from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import get_db, Domain, Interaction, NBA, NBAAction
from core.adapter import get_adapter
from agents.pipeline import run_pipeline

router = APIRouter(prefix="/api/interactions", tags=["interactions"])


class InteractionRequest(BaseModel):
    domain_id: int
    entity_name: str
    text: str


@router.post("")
def submit_interaction(req: InteractionRequest, db: Session = Depends(get_db)):
    # Validate domain
    domain = db.query(Domain).filter(Domain.id == req.domain_id).first()
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")

    # Load adapter
    try:
        adapter = get_adapter(domain.slug)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Adapter not found for domain: {domain.slug}")

    # Save interaction
    interaction = Interaction(
        domain_id=req.domain_id,
        entity_name=req.entity_name,
        text=req.text,
    )
    db.add(interaction)
    db.commit()
    db.refresh(interaction)

    # Run pipeline
    try:
        result = run_pipeline(
            domain_id=req.domain_id,
            interaction_id=interaction.id,
            interaction_text=req.text,
            entity_name=req.entity_name,
            adapter=adapter,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")

    # Save NBA
    nba = NBA(
        interaction_id=interaction.id,
        domain_id=req.domain_id,
        hitl_status="pending",
        agent_log=result.get("agent_log", []),
        matched_intent=result.get("matched_intent", ""),
        severity=result.get("severity", "medium"),
        blast_radius=result.get("blast_radius", ""),
    )
    db.add(nba)
    db.commit()
    db.refresh(nba)

    # Save actions
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
        )
        db.add(action)
    db.commit()

    return {
        "interaction_id": interaction.id,
        "nba_id": nba.id,
        "matched_intent": result.get("matched_intent"),
        "severity": result.get("severity"),
        "action_count": len(result.get("ranked_actions", [])),
    }


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
