from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from database import get_db, NBA, NBAAction, MemoryPattern, Interaction, Event, Domain

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

    # Extract agent_log extras
    agent_log = nba.agent_log or []
    critique = ""
    critique_flag = "OK"
    risk_reasoning = ""
    for entry in agent_log:
        if entry.get("agent") == "Critic":
            # Critique is stored in agent_log steps
            pass
    # Pull from ranked_actions[0] if present
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
            "reasoning_summary": a.reasoning_summary or "",
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

    # ── SQL Memory learning ────────────────────────────────────────────────
    _update_sql_memory(db, nba, approved=True)

    # ── Semantic vector memory ─────────────────────────────────────────────
    _update_vector_memory(nba, approved=True)

    # ── Entity graph ───────────────────────────────────────────────────────
    _update_entity_graph(db, nba, approved=True)

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

    # ── Memory learning ────────────────────────────────────────────────────
    _update_sql_memory(db, nba, approved=False)
    _update_vector_memory(nba, approved=False)
    _update_entity_graph(db, nba, approved=False)

    # ── Rejection → learning loop ──────────────────────────────────────────
    if req.reason:
        _process_rejection_feedback(db, nba, req.reason)

    db.add(Event(
        domain_id=nba.domain_id,
        nba_id=nba.id,
        event_type="nba_rejected",
        payload={"matched_intent": nba.matched_intent, "reason": req.reason},
    ))
    db.commit()

    return {"status": "rejected", "nba_id": nba_id}


# ── Internal helpers ──────────────────────────────────────────────────────────

def _get_domain_slug(db: Session, domain_id: int) -> str:
    domain = db.query(Domain).filter(Domain.id == domain_id).first()
    return domain.slug if domain else ""


def _update_sql_memory(db: Session, nba: NBA, approved: bool):
    """Aggregate SQL memory pattern: success/failure count."""
    intent = nba.matched_intent or "general"
    top_action = nba.actions[0].action if nba.actions else "Unknown action"
    interaction_text = nba.interaction.text[:300] if nba.interaction else ""

    existing = (
        db.query(MemoryPattern)
        .filter(MemoryPattern.domain_id == nba.domain_id, MemoryPattern.issue_type == intent)
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
        db.add(MemoryPattern(
            domain_id=nba.domain_id,
            issue_type=intent,
            issue_text=interaction_text,
            resolution=top_action,
            success_count=1 if approved else 0,
            failure_count=0 if approved else 1,
        ))
    db.commit()


def _update_vector_memory(nba: NBA, approved: bool):
    """Embed and store/update the interaction → resolution in the vector store."""
    try:
        from database import SessionLocal, Domain
        db_tmp = SessionLocal()
        domain = db_tmp.query(Domain).filter(Domain.id == nba.domain_id).first()
        domain_slug = domain.slug if domain else ""
        db_tmp.close()
        if not domain_slug:
            return

        from memory.vector_store import store_memory
        intent = nba.matched_intent or "general"
        top_action = nba.actions[0].action if nba.actions else ""
        interaction_text = nba.interaction.text if nba.interaction else ""
        entity_name = nba.interaction.entity_name if nba.interaction else ""

        # Document: "interaction text → resolved as: action"
        document = f"{interaction_text} → resolved as: {top_action}"
        doc_id = f"nba_{nba.id}_{'approved' if approved else 'rejected'}"

        store_memory(
            domain_slug=domain_slug,
            doc_id=doc_id,
            text=document,
            metadata={
                "nba_id": nba.id,
                "issue_type": intent,
                "resolution": top_action,
                "entity_name": entity_name,
                "severity": nba.severity,
                "approved": approved,
                "success_count": 1,
            },
        )
    except Exception as e:
        print(f"[VectorMemory] update failed for nba {nba.id}: {e}")


def _update_entity_graph(db: Session, nba: NBA, approved: bool):
    """Add this decision to the entity knowledge graph."""
    try:
        domain_slug = _get_domain_slug(db, nba.domain_id)
        if not domain_slug:
            return
        entity_name = nba.interaction.entity_name if nba.interaction else "Unknown"
        intent = nba.matched_intent or "general"
        top_action = nba.actions[0].action if nba.actions else ""

        from memory.entity_graph import add_decision
        add_decision(domain_slug, entity_name, intent, top_action, approved)
    except Exception as e:
        print(f"[EntityGraph] update failed for nba {nba.id}: {e}")


def _process_rejection_feedback(db: Session, nba: NBA, reason: str):
    """
    LLM-powered rejection learning:
    Parse rejection reason to store a corrective memory that improves future recommendations.
    """
    try:
        domain_slug = _get_domain_slug(db, nba.domain_id)
        if not domain_slug:
            return
        top_action = nba.actions[0].action if nba.actions else ""
        interaction_text = nba.interaction.text if nba.interaction else ""
        entity_name = nba.interaction.entity_name if nba.interaction else ""

        from llm_provider import llm
        prompt = (
            f"An NBA recommendation was rejected.\n\n"
            f"Entity: {entity_name}\n"
            f"Situation: {interaction_text[:300]}\n"
            f"Rejected action: {top_action}\n"
            f"Rejection reason: {reason}\n\n"
            f"What would have been a better action? Reply in 1 sentence starting with an action verb."
        )
        better_action = llm.generate(prompt, "You are a business process expert. Be concise.")

        # Store the corrective memory with the better action
        from memory.vector_store import store_memory
        store_memory(
            domain_slug=domain_slug,
            doc_id=f"correction_nba_{nba.id}",
            text=f"{interaction_text} → better action: {better_action}",
            metadata={
                "nba_id": nba.id,
                "issue_type": nba.matched_intent,
                "resolution": better_action,
                "entity_name": entity_name,
                "severity": nba.severity,
                "approved": True,  # treat correction as a positive signal
                "success_count": 2,  # higher weight for human-corrected memories
                "is_correction": True,
            },
        )
        print(f"[RejectionFeedback] Stored corrective memory for nba {nba.id}: {better_action[:60]}")
    except Exception as e:
        print(f"[RejectionFeedback] Failed for nba {nba.id}: {e}")
