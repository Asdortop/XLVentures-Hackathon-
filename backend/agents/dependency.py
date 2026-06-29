"""
Dependency Agent — maps entity relationships and blast radius.
Two layers:
1. Static YAML schema relationships (existing)
2. GraphRAG entity graph — dynamic, learned from past NBA decisions (NEW)
"""
from datetime import datetime
from agents.state import AgentState


def dependency_agent(state: AgentState) -> dict:
    adapter = state["adapter"]
    schema = adapter.get("schema", {})
    entity_name = state.get("entity_name", "Unknown")
    domain_slug = state.get("domain_slug", "")
    intent = state.get("matched_intent", "general")

    log_entry = {
        "agent": "Dependency",
        "timestamp": datetime.utcnow().isoformat(),
        "steps": [],
    }

    entities = schema.get("entities", [])
    relationships = schema.get("relationships", [])
    primary_entity = schema.get("primary_entity", "Entity")

    log_entry["steps"].append(f"Mapping relationships for entity: {entity_name}")
    log_entry["steps"].append(
        f"Schema: {len(entities)} entities, {len(relationships)} relationships"
    )

    # ── 1. Static YAML blast radius ────────────────────────────────────────
    affected = []
    blast_parts = []

    for rel in relationships:
        from_e = rel.get("from", "")
        to_e = rel.get("to", "")
        rel_type = rel.get("type", "related_to")

        from_label = next((e["label"] for e in entities if e["id"] == from_e), from_e)
        to_label = next((e["label"] for e in entities if e["id"] == to_e), to_e)

        affected.append(to_label)
        blast_parts.append(f"{entity_name} ({primary_entity}) → {to_label} ({rel_type})")
        log_entry["steps"].append(f"Relationship: {from_label} --[{rel_type}]--> {to_label}")

    if not affected:
        affected = [primary_entity]
        blast_parts = [f"{entity_name} ({primary_entity}) — no downstream dependencies found"]
        log_entry["steps"].append("No relationships in schema — isolated entity")

    blast_radius = " | ".join(blast_parts)
    log_entry["steps"].append(f"✓ Static blast radius: {len(affected)} affected entities")

    # ── 2. GraphRAG entity graph context ──────────────────────────────────
    graph_context = []
    if domain_slug:
        try:
            from memory.entity_graph import get_entity_context
            graph_context = get_entity_context(domain_slug, entity_name, intent)

            if graph_context:
                for ctx in graph_context:
                    if ctx["type"] == "entity_history":
                        log_entry["steps"].append(
                            f"📊 Graph: {ctx['message']}"
                        )
                    elif ctx["type"] == "similar_entity":
                        log_entry["steps"].append(
                            f"🔗 Graph: {ctx['message']}"
                        )
            else:
                log_entry["steps"].append("Graph: no prior decisions for this entity/intent")
        except Exception as e:
            log_entry["steps"].append(f"Graph: error — {e}")
    else:
        log_entry["steps"].append("Graph: skipped (no domain_slug)")

    return {
        "affected_entities": affected,
        "blast_radius": blast_radius,
        "graph_context": graph_context,
        "agent_log": [log_entry],
    }
