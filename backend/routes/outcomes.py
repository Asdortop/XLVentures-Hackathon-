from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db, NBA, NBAAction, MemoryPattern, Event, Domain
from core.adapter import get_adapter

router = APIRouter(prefix="/api/outcomes", tags=["outcomes"])


def _avg_time_to_decision_minutes(db: Session, domain_id: int) -> float:
    """Compute avg minutes between NBA creation and first approve/reject event."""
    try:
        events = (
            db.query(Event)
            .filter(
                Event.domain_id == domain_id,
                Event.event_type.in_(["nba_approved", "nba_rejected"]),
            )
            .all()
        )
        if not events:
            return 0.0
        deltas = []
        for ev in events:
            nba = db.query(NBA).filter(NBA.id == ev.nba_id).first()
            if nba:
                delta = (ev.created_at - nba.created_at).total_seconds() / 60
                if delta >= 0:
                    deltas.append(delta)
        return round(sum(deltas) / len(deltas), 1) if deltas else 0.0
    except Exception:
        return 0.0


def _confidence_trend(db: Session, domain_id: int) -> dict:
    """Compare avg confidence of first 5 vs last 5 approved NBAs."""
    try:
        approved_nbas = (
            db.query(NBA)
            .filter(NBA.domain_id == domain_id, NBA.hitl_status == "approved")
            .order_by(NBA.created_at.asc())
            .all()
        )
        if len(approved_nbas) < 2:
            return {"first_avg": 0, "last_avg": 0, "delta": 0, "improving": False}

        def avg_conf(nbas):
            confs = []
            for n in nbas:
                for a in n.actions:
                    confs.append(a.confidence)
            return round(sum(confs) / len(confs), 3) if confs else 0

        first_avg = avg_conf(approved_nbas[:5])
        last_avg = avg_conf(approved_nbas[-5:])
        delta = round(last_avg - first_avg, 3)
        return {
            "first_avg": round(first_avg * 100, 1),
            "last_avg": round(last_avg * 100, 1),
            "delta": round(delta * 100, 1),
            "improving": delta > 0,
        }
    except Exception:
        return {"first_avg": 0, "last_avg": 0, "delta": 0, "improving": False}


@router.get("/{domain_id}")
def get_outcomes(domain_id: int, db: Session = Depends(get_db)):
    domain = db.query(Domain).filter(Domain.id == domain_id).first()
    if not domain:
        return {}

    # Total NBAs
    total_nbas = db.query(NBA).filter(NBA.domain_id == domain_id).count()
    approved = db.query(NBA).filter(NBA.domain_id == domain_id, NBA.hitl_status == "approved").count()
    rejected = db.query(NBA).filter(NBA.domain_id == domain_id, NBA.hitl_status == "rejected").count()
    pending = db.query(NBA).filter(NBA.domain_id == domain_id, NBA.hitl_status == "pending").count()

    approval_rate = round(approved / max(approved + rejected, 1), 2)

    # Hours saved: sum estimated_hours of all approved actions
    approved_nba_ids = [
        n.id for n in db.query(NBA).filter(
            NBA.domain_id == domain_id, NBA.hitl_status == "approved"
        ).all()
    ]
    hours_saved = 0.0
    avg_confidence = 0.0
    if approved_nba_ids:
        approved_actions = db.query(NBAAction).filter(NBAAction.nba_id.in_(approved_nba_ids)).all()
        hours_saved = round(sum(a.estimated_hours for a in approved_actions), 1)
        if approved_actions:
            avg_confidence = round(sum(a.confidence for a in approved_actions) / len(approved_actions), 2)

    # Avg actions per NBA
    avg_actions = round(db.query(NBAAction).join(NBA).filter(NBA.domain_id == domain_id).count() / max(total_nbas, 1), 1)

    # Memory patterns
    patterns = db.query(MemoryPattern).filter(MemoryPattern.domain_id == domain_id).all()
    pattern_count = len(patterns)
    top_patterns = sorted(patterns, key=lambda p: p.success_count, reverse=True)[:3]

    # Top performing actions by approval rate
    # Get all actions from approved NBAs
    approved_nba_ids = [
        n.id for n in db.query(NBA).filter(
            NBA.domain_id == domain_id, NBA.hitl_status == "approved"
        ).all()
    ]
    action_stats = {}
    if approved_nba_ids:
        approved_actions = db.query(NBAAction).filter(
            NBAAction.nba_id.in_(approved_nba_ids)
        ).all()
        for a in approved_actions:
            key = a.action[:60]
            if key not in action_stats:
                action_stats[key] = {"action": a.action, "approved": 0, "total": 0}
            action_stats[key]["approved"] += 1
            action_stats[key]["total"] += 1

    # All actions (for total count)
    all_actions = db.query(NBAAction).join(NBA).filter(NBA.domain_id == domain_id).all()
    for a in all_actions:
        key = a.action[:60]
        if key in action_stats:
            action_stats[key]["total"] = max(action_stats[key]["total"], 1)

    top_actions = sorted(
        [{"action": v["action"], "approval_rate": round(v["approved"] / max(v["total"], 1), 2)}
         for v in action_stats.values()],
        key=lambda x: x["approval_rate"],
        reverse=True,
    )[:5]

    # Value metric from adapter
    value_metric = {}
    per_nba_value = 0
    value_label = "Decisions Supported"
    try:
        adapter = get_adapter(domain.slug)
        ui = adapter.get("ui", {})
        vm = ui.get("value_metric", {})
        per_nba_value = vm.get("per_approved_nba", 0)
        value_label = vm.get("label", "Decisions Supported")
    except Exception:
        pass

    estimated_value = approved * per_nba_value

    # ── New business metrics ──────────────────────────────────────────────
    avg_ttd = _avg_time_to_decision_minutes(db, domain_id)
    value_awaiting = pending * per_nba_value
    conf_trend = _confidence_trend(db, domain_id)

    # Semantic memory count
    semantic_count = 0
    try:
        from memory.vector_store import collection_count
        semantic_count = collection_count(domain.slug)
    except Exception:
        pass

    return {
        "domain_id": domain_id,
        "total_nbas": total_nbas,
        "approved": approved,
        "rejected": rejected,
        "pending": pending,
        "approval_rate": approval_rate,
        "pattern_count": pattern_count,
        "semantic_memory_count": semantic_count,
        "avg_time_to_decision_minutes": avg_ttd,
        "value_awaiting": value_awaiting,
        "confidence_trend": conf_trend,
        "top_patterns": [
            {
                "issue_type": p.issue_type,
                "resolution": p.resolution[:80],
                "success_count": p.success_count,
                "success_rate": round(p.success_count / max(p.success_count + p.failure_count, 1), 2),
            }
            for p in top_patterns
        ],
        "top_actions": top_actions,
        "value_metric": {
            "label": value_label,
            "per_approved_nba": per_nba_value,
            "total": estimated_value,
        },
    }
