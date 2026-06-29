"""
Context Agent — gathers relevant context from 4 sources:
1. Memory patterns (DB)
2. Playbooks/knowledge (adapter YAML)
3. CRM seed data (adapter schema)
4. Customer history (DB)
"""
from datetime import datetime
from agents.state import AgentState
from database import SessionLocal, MemoryPattern, Interaction


def context_agent(state: AgentState) -> dict:
    adapter = state["adapter"]
    domain_id = state["domain_id"]
    intent = state["matched_intent"]
    text = state["interaction_text"].lower()
    keywords = [k.lower() for k in state.get("keywords_found", [])]

    log_entry = {
        "agent": "Context",
        "timestamp": datetime.utcnow().isoformat(),
        "steps": [],
    }

    # ── 1. Memory Patterns ──────────────────────────────────────────────────
    memory_patterns = []
    try:
        db = SessionLocal()
        patterns = (
            db.query(MemoryPattern)
            .filter(MemoryPattern.domain_id == domain_id)
            .all()
        )
        for p in patterns:
            if p.issue_type == intent or any(k in (p.issue_text or "").lower() for k in keywords):
                memory_patterns.append({
                    "issue_type": p.issue_type,
                    "resolution": p.resolution,
                    "success_count": p.success_count,
                    "failure_count": p.failure_count,
                    "success_rate": round(
                        p.success_count / max(p.success_count + p.failure_count, 1), 2
                    ),
                })
        log_entry["steps"].append(f"Memory: found {len(memory_patterns)} relevant patterns for intent '{intent}'")
        db.close()
    except Exception as e:
        log_entry["steps"].append(f"Memory: error — {e}")

    # ── 2. Playbook Matches ──────────────────────────────────────────────────
    playbook_matches = []
    playbooks = adapter.get("knowledge", {}).get("playbooks", [])
    for pb in playbooks:
        pb_keywords = [k.lower() for k in pb.get("keywords", [])]
        match_score = sum(1 for k in pb_keywords if k in text or k in keywords)
        if match_score > 0:
            playbook_matches.append({
                "id": pb.get("id"),
                "title": pb.get("title"),
                "excerpt": pb.get("excerpt", "")[:300],
                "match_score": match_score,
            })
    playbook_matches.sort(key=lambda x: x["match_score"], reverse=True)
    log_entry["steps"].append(f"Knowledge: matched {len(playbook_matches)} playbooks")

    # ── 3. CRM Context (from schema seed data) ──────────────────────────────
    crm_context = ""
    entity_name = state.get("entity_name", "")
    schema = adapter.get("schema", {})
    seed_records = schema.get("seed_data", [])
    for record in seed_records:
        if entity_name.lower() in str(record).lower():
            crm_context = str(record)
            break
    if not crm_context and entity_name:
        crm_context = f"Entity: {entity_name} — No CRM record found, using submitted interaction as context."
    log_entry["steps"].append(f"CRM: {'found record' if seed_records else 'no seed data'} for '{entity_name}'")

    # ── 4. Interaction History ──────────────────────────────────────────────
    history = []
    try:
        db = SessionLocal()
        past = (
            db.query(Interaction)
            .filter(Interaction.domain_id == domain_id)
            .order_by(Interaction.created_at.desc())
            .limit(3)
            .all()
        )
        for p in past:
            if p.id != state.get("interaction_id") and entity_name.lower() in p.text.lower():
                history.append({"text": p.text[:200], "created_at": p.created_at.isoformat()})
        log_entry["steps"].append(f"History: {len(history)} past interactions for this entity")
        db.close()
    except Exception as e:
        log_entry["steps"].append(f"History: error — {e}")

    return {
        "memory_patterns": memory_patterns,
        "playbook_matches": playbook_matches,
        "crm_context": crm_context,
        "history": history,
        "agent_log": [log_entry],
    }
