from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import SessionLocal, get_db, Domain, Interaction, NBA, NBAAction
from core.adapter import get_adapter
from agents.pipeline import run_pipeline, run_pipeline_steps
import json

router = APIRouter(prefix="/api/interactions", tags=["interactions"])


class InteractionRequest(BaseModel):
    domain_id: int
    entity_name: str
    text: str


def _save_nba(db: Session, interaction_id: int, domain_id: int, result: dict) -> NBA:
    """Save pipeline result as NBA + NBAActions. Returns the NBA object."""
    nba = NBA(
        interaction_id=interaction_id,
        domain_id=domain_id,
        hitl_status="pending",
        agent_log=result.get("agent_log", []),
        matched_intent=result.get("matched_intent", ""),
        severity=result.get("severity", "medium"),
        blast_radius=result.get("blast_radius", ""),
    )
    db.add(nba)
    db.commit()
    db.refresh(nba)

    for action_data in result.get("ranked_actions", []):
        action = NBAAction(
            nba_id=nba.id,
            rank=action_data.get("rank", 1),
            action=action_data.get("action", ""),
            owner=action_data.get("owner", ""),
            priority=action_data.get("priority", "medium"),
            action_type=action_data.get("action_type", "task"),
            confidence=action_data.get("confidence", 0.5),
            estimated_hours=action_data.get("estimated_hours", 1.0),
            evidence=action_data.get("evidence", []),
            reasoning_summary=action_data.get("reasoning_summary", ""),
        )
        db.add(action)
    db.commit()
    return nba


@router.post("")
def submit_interaction(req: InteractionRequest, db: Session = Depends(get_db)):
    """Standard (non-streaming) submission. Used as fallback."""
    domain = db.query(Domain).filter(Domain.id == req.domain_id).first()
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")

    try:
        adapter = get_adapter(domain.slug)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Adapter not found: {domain.slug}")

    interaction = Interaction(domain_id=req.domain_id, entity_name=req.entity_name, text=req.text)
    db.add(interaction)
    db.commit()
    db.refresh(interaction)

    try:
        result = run_pipeline(
            domain_id=req.domain_id,
            domain_slug=domain.slug,
            interaction_id=interaction.id,
            interaction_text=req.text,
            entity_name=req.entity_name,
            adapter=adapter,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")

    nba = _save_nba(db, interaction.id, req.domain_id, result)

    return {
        "interaction_id": interaction.id,
        "nba_id": nba.id,
        "matched_intent": result.get("matched_intent"),
        "severity": result.get("severity"),
        "action_count": len(result.get("ranked_actions", [])),
    }


@router.post("/stream")
async def submit_interaction_stream(req: InteractionRequest):
    """
    SSE streaming submission. Emits live agent progress events then saves NBA.
    Frontend reads via fetch + ReadableStream (POST SSE pattern).
    """
    # Validate and load synchronously before streaming starts
    db = SessionLocal()
    try:
        domain = db.query(Domain).filter(Domain.id == req.domain_id).first()
        if not domain:
            raise HTTPException(status_code=404, detail="Domain not found")
        try:
            adapter = get_adapter(domain.slug)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail=f"Adapter not found: {domain.slug}")

        interaction = Interaction(domain_id=req.domain_id, entity_name=req.entity_name, text=req.text)
        db.add(interaction)
        db.commit()
        db.refresh(interaction)
        interaction_id = interaction.id
        domain_slug = domain.slug
    finally:
        db.close()

    def _sse(event_type: str, data: dict) -> str:
        return f"data: {json.dumps({'type': event_type, **data})}\n\n"

    def generate():
        final_state = None
        try:
            for agent_name, icon, result, state in run_pipeline_steps(
                domain_id=req.domain_id,
                domain_slug=domain_slug,
                interaction_id=interaction_id,
                interaction_text=req.text,
                entity_name=req.entity_name,
                adapter=adapter,
            ):
                final_state = state

                # Extract human-readable summary per agent
                log_steps = result.get("agent_log", [{}])[0].get("steps", [])
                summary = log_steps[-1] if log_steps else f"{agent_name} completed"

                yield _sse("agent_done", {
                    "agent": agent_name,
                    "icon": icon,
                    "summary": summary,
                    "steps": log_steps,
                    "severity": state.get("severity", ""),
                    "matched_intent": state.get("matched_intent", ""),
                })

            # Save NBA after all agents complete
            if final_state:
                db2 = SessionLocal()
                try:
                    nba = _save_nba(db2, interaction_id, req.domain_id, final_state)
                    top_confidence = max(
                        (a.get("confidence", 0) for a in final_state.get("ranked_actions", [])),
                        default=0
                    )
                    yield _sse("pipeline_complete", {
                        "nba_id": nba.id,
                        "severity": final_state.get("severity", "medium"),
                        "action_count": len(final_state.get("ranked_actions", [])),
                        "matched_intent": final_state.get("matched_intent", ""),
                        "top_confidence": round(top_confidence, 3),
                        "critique_flag": final_state.get("critique_flag", "OK"),
                    })
                finally:
                    db2.close()

        except Exception as e:
            yield _sse("pipeline_error", {"error": str(e)})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.get("/{domain_id}")
def list_interactions(domain_id: int, db: Session = Depends(get_db)):
    interactions = (
        db.query(Interaction)
        .filter(Interaction.domain_id == domain_id)
        .order_by(Interaction.created_at.desc())
        .limit(20)
        .all()
    )
    return [
        {
            "id": i.id,
            "entity_name": i.entity_name,
            "text": i.text[:100] + "..." if len(i.text) > 100 else i.text,
            "created_at": i.created_at.isoformat(),
            "nba_id": i.nba.id if i.nba else None,
        }
        for i in interactions
    ]
