"""
Memory & Graph Explorer API
GET /api/memory/{domain_id}
Returns: vector memories, entity graph nodes/edges, SQL patterns
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db, Domain, MemoryPattern, NBA, NBAAction, Interaction
import json

router = APIRouter(prefix="/api/memory", tags=["memory"])


@router.get("/{domain_id}")
def get_memory_data(domain_id: int, db: Session = Depends(get_db)):
    domain = db.query(Domain).filter(Domain.id == domain_id).first()
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")

    # ── 1. SQL Memory Patterns ─────────────────────────────────────────────
    patterns = db.query(MemoryPattern).filter(MemoryPattern.domain_id == domain_id).all()
    sql_patterns = [
        {
            "id": p.id,
            "issue_type": p.issue_type,
            "issue_text": p.issue_text[:120] if p.issue_text else "",
            "resolution": p.resolution[:120] if p.resolution else "",
            "success_count": p.success_count,
            "failure_count": p.failure_count,
            "success_rate": round(
                p.success_count / max(p.success_count + p.failure_count, 1), 2
            ),
            "last_used": p.last_used.isoformat() if p.last_used else None,
        }
        for p in patterns
    ]

    # ── 2. Semantic Vector Memories ────────────────────────────────────────
    semantic_memories = []
    semantic_count = 0
    try:
        from memory.vector_store import _get_conn, _ensure_table, collection_count
        import re, sqlite3

        semantic_count = collection_count(domain.slug)
        conn = _get_conn()
        safe = re.sub(r'[^a-z0-9_]', '_', domain.slug.lower())
        table = f"embeddings_{safe}"
        rows = conn.execute(
            f"SELECT id, document, metadata FROM {table} ORDER BY rowid DESC LIMIT 20"
        ).fetchall()
        conn.close()

        for row_id, doc, meta_json in rows:
            meta = json.loads(meta_json) if meta_json else {}
            semantic_memories.append({
                "id": row_id,
                "document": doc[:150],
                "issue_type": meta.get("issue_type", ""),
                "resolution": meta.get("resolution", "")[:100],
                "entity_name": meta.get("entity_name", ""),
                "severity": meta.get("severity", ""),
                "approved": meta.get("approved", None),
                "success_count": meta.get("success_count", 1),
                "is_correction": meta.get("is_correction", False),
            })
    except Exception as e:
        print(f"[MemoryAPI] vector store read: {e}")

    # ── 3. Entity Graph ────────────────────────────────────────────────────
    graph_nodes = []
    graph_edges = []
    try:
        from memory.entity_graph import get_graph
        G = get_graph(domain.slug)

        for node, data in G.nodes(data=True):
            graph_nodes.append({
                "id": node,
                "label": node,
                "decisions": data.get("decisions", 0),
                "approved": data.get("approved", 0),
                "rejected": data.get("rejected", 0),
                "intents": list(data.get("intents", set())),
                "success_rate": round(
                    data.get("approved", 0) / max(data.get("decisions", 1), 1), 2
                ),
            })

        for u, v, data in G.edges(data=True):
            graph_edges.append({
                "source": u,
                "target": v,
                "weight": data.get("weight", 1),
                "relationship": data.get("relationship", "related_to"),
            })
    except Exception as e:
        print(f"[MemoryAPI] entity graph read: {e}")

    # ── 4. Recent approved/rejected decisions timeline ─────────────────────
    recent_nbas = (
        db.query(NBA)
        .filter(NBA.domain_id == domain_id, NBA.hitl_status.in_(["approved", "rejected"]))
        .order_by(NBA.created_at.desc())
        .limit(10)
        .all()
    )
    decision_timeline = [
        {
            "nba_id": n.id,
            "entity_name": n.interaction.entity_name if n.interaction else "",
            "intent": n.matched_intent,
            "severity": n.severity,
            "status": n.hitl_status,
            "top_action": n.actions[0].action[:80] if n.actions else "",
            "confidence": round(n.actions[0].confidence, 2) if n.actions else 0,
            "created_at": n.created_at.isoformat(),
            "rejection_reason": n.rejection_reason,
        }
        for n in recent_nbas
    ]

    return {
        "domain_id": domain_id,
        "domain_slug": domain.slug,
        "sql_patterns": sql_patterns,
        "semantic_memories": semantic_memories,
        "semantic_count": semantic_count,
        "graph_nodes": graph_nodes,
        "graph_edges": graph_edges,
        "decision_timeline": decision_timeline,
        "summary": {
            "sql_pattern_count": len(sql_patterns),
            "semantic_memory_count": semantic_count,
            "entity_count": len(graph_nodes),
            "edge_count": len(graph_edges),
            "total_decisions": len(decision_timeline),
        },
    }
