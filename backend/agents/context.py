"""
Context Agent — gathers relevant context from 5 sources:
1. Semantic memory (sentence-transformers cosine similarity) — NEW
2. SQL memory patterns (fallback if vector store empty)
3. Playbooks/knowledge (adapter YAML keyword match)
4. CRM seed data (adapter schema)
5. Customer history (DB)
"""
from datetime import datetime
from agents.state import AgentState
from database import SessionLocal, MemoryPattern, Interaction


def context_agent(state: AgentState) -> dict:
    adapter = state["adapter"]
    domain_id = state["domain_id"]
    domain_slug = state.get("domain_slug", "")
    intent = state["matched_intent"]
    text = state["interaction_text"]
    text_lower = text.lower()
    keywords = [k.lower() for k in state.get("keywords_found", [])]

    log_entry = {
        "agent": "Context",
        "timestamp": datetime.utcnow().isoformat(),
        "steps": [],
    }

    # ── 1. Semantic Vector Memory ─────────────────────────────────────────
    semantic_memories = []
    if domain_slug:
        try:
            from memory.vector_store import retrieve_similar
            hits = retrieve_similar(domain_slug, text, n=5, min_similarity=0.35)
            for hit in hits:
                meta = hit.get("metadata", {})
                semantic_memories.append({
                    "issue_type": meta.get("issue_type", intent),
                    "resolution": meta.get("resolution", ""),
                    "success_count": meta.get("success_count", 1),
                    "similarity": hit["similarity"],
                    "source": "semantic_memory",
                })
            log_entry["steps"].append(
                f"Semantic memory: found {len(semantic_memories)} similar past decisions "
                f"(top similarity: {semantic_memories[0]['similarity'] if semantic_memories else 'n/a'})"
            )
        except Exception as e:
            log_entry["steps"].append(f"Semantic memory: error — {e}")
    else:
        log_entry["steps"].append("Semantic memory: skipped (no domain_slug)")

    # ── 2. SQL Memory Patterns (fallback / supplement) ───────────────────
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
        log_entry["steps"].append(
            f"SQL memory: {len(memory_patterns)} pattern(s) for intent '{intent}'"
        )
        db.close()
    except Exception as e:
        log_entry["steps"].append(f"SQL memory: error — {e}")

    # ── 3. Playbook Matches ───────────────────────────────────────────────
    playbook_matches = []
    playbooks = adapter.get("knowledge", {}).get("playbooks", [])
    for pb in playbooks:
        pb_keywords = [k.lower() for k in pb.get("keywords", [])]
        match_score = sum(1 for k in pb_keywords if k in text_lower or k in keywords)
        if match_score > 0:
            playbook_matches.append({
                "id": pb.get("id"),
                "title": pb.get("title"),
                "excerpt": pb.get("excerpt", "")[:300],
                "match_score": match_score,
            })
    playbook_matches.sort(key=lambda x: x["match_score"], reverse=True)
    log_entry["steps"].append(f"Knowledge: matched {len(playbook_matches)} playbooks")

    # ── 4. CRM Context ────────────────────────────────────────────────────
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
    log_entry["steps"].append(
        f"CRM: {'found record' if seed_records else 'no seed data'} for '{entity_name}'"
    )

    # ── 5. Interaction History ─────────────────────────────────────────────
    history = []
    try:
        db = SessionLocal()
        past = (
            db.query(Interaction)
            .filter(Interaction.domain_id == domain_id)
            .order_by(Interaction.created_at.desc())
            .limit(5)
            .all()
        )
        for p in past:
            if p.id != state.get("interaction_id") and entity_name.lower() in p.text.lower():
                history.append({"text": p.text[:200], "created_at": p.created_at.isoformat()})
        log_entry["steps"].append(f"History: {len(history)} past interaction(s) for this entity")
        db.close()
    except Exception as e:
        log_entry["steps"].append(f"History: error — {e}")

    return {
        "semantic_memories": semantic_memories,
        "memory_patterns": memory_patterns,
        "playbook_matches": playbook_matches,
        "crm_context": crm_context,
        "history": history,
        "agent_log": [log_entry],
    }
