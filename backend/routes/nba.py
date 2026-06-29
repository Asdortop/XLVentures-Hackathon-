from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from database import get_db, NBA, NBAAction, MemoryPattern, Interaction, Event

router = APIRouter(prefix="/api/nba", tags=["nba"])


class HITLRequest(BaseModel):
    reason: Optional[str] = None


def _format_nba(nba: NBA) -> dict:
    top_confidence = max((a.confidence for a in nba.actions), default=0)
    return {
        "id": nba.id,
        "interaction_id": nba.interaction_id,
        "domain_id": nba.domain_id,
        "hitl_status": nba.hitl_status,
        "matched_intent": nba.matched_intent,
        "severity": nba.severity,
        "blast_radius": nba.blast_radius,
        "action_count": len(nba.actions),
        "top_confidence": round(top_confidence, 3),
        "entity_name": nba.interaction.entity_name if nba.interaction else "",
        "interaction_text": nba.interaction.text[:100] if nba.interaction else "",
        "created_at": nba.created_at.isoformat(),
    }


@router.get("/{domain_id}")
def list_nbas(domain_id: int, status: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(NBA).filter(NBA.domain_id == domain_id)
    if status:
        query = query.filter(NBA.hitl_status == status)
    nbas = query.order_by(NBA.created_at.desc()).all()
    return [_format_nba(n) for n in nbas]


@router.get("/detail/{nba_id}")
def get_nba_detail(nba_id: int, db: Session = Depends(get_db)):
    nba = db.query(NBA).filter(NBA.id == nba_id).first()
    if not nba:
        raise HTTPException(status_code=404, detail="NBA not found")

    actions = [
        {
            "id": a.id,
            "rank": a.rank,
            "action": a.action,
            "owner": a.owner,
            "priority": a.priority,
            "action_type": a.action_type,
            "confidence": round(a.confidence, 3),
            "estimated_hours": a.estimated_hours,
            "evidence": a.evidence or [],
        }
        for a in nba.actions
    ]

    return {
        **_format_nba(nba),
        "actions": actions,
        "agent_log": nba.agent_log or [],
        "rejection_reason": nba.rejection_reason,
    }


@router.post("/detail/{nba_id}/approve")
def approve_nba(nba_id: int, db: Session = Depends(get_db)):
    nba = db.query(NBA).filter(NBA.id == nba_id).first()
    if not nba:
        raise HTTPException(status_code=404, detail="NBA not found")
    if nba.hitl_status != "pending":
        raise HTTPException(status_code=400, detail="NBA is not pending")

    nba.hitl_status = "approved"
    db.commit()

    # ── Memory learning: create or update pattern ──────────────────────────
    _update_memory(db, nba, approved=True)

    # Log event
    db.add(Event(
        domain_id=nba.domain_id,
        nba_id=nba.id,
        event_type="nba_approved",
        payload={"matched_intent": nba.matched_intent},
    ))
    db.commit()

    return {"status": "approved", "nba_id": nba_id}


@router.post("/detail/{nba_id}/reject")
def reject_nba(nba_id: int, req: HITLRequest, db: Session = Depends(get_db)):
    nba = db.query(NBA).filter(NBA.id == nba_id).first()
    if not nba:
        raise HTTPException(status_code=404, detail="NBA not found")
    if nba.hitl_status != "pending":
        raise HTTPException(status_code=400, detail="NBA is not pending")

    nba.hitl_status = "rejected"
    nba.rejection_reason = req.reason
    db.commit()

    # ── Memory learning ─────────────────────────────────────────────────────
    _update_memory(db, nba, approved=False)

    db.add(Event(
        domain_id=nba.domain_id,
        nba_id=nba.id,
        event_type="nba_rejected",
        payload={"matched_intent": nba.matched_intent, "reason": req.reason},
    ))
    db.commit()

    return {"status": "rejected", "nba_id": nba_id}


def _update_memory(db: Session, nba: NBA, approved: bool):
    """Create a new memory pattern or update an existing one."""
    intent = nba.matched_intent or "general"
    top_action = nba.actions[0].action if nba.actions else "Unknown action"
    interaction_text = nba.interaction.text[:300] if nba.interaction else ""

    existing = (
        db.query(MemoryPattern)
        .filter(
            MemoryPattern.domain_id == nba.domain_id,
            MemoryPattern.issue_type == intent,
        )
        .first()
    )

    if existing:
        if approved:
            existing.success_count += 1
        else:
            existing.failure_count += 1
        from datetime import datetime
        existing.last_used = datetime.utcnow()
    else:
        # Create new pattern — this is how memory GROWS
        new_pattern = MemoryPattern(
            domain_id=nba.domain_id,
            issue_type=intent,
            issue_text=interaction_text,
            resolution=top_action,
            success_count=1 if approved else 0,
            failure_count=0 if approved else 1,
        )
        db.add(new_pattern)

    db.commit()
