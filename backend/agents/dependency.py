"""
Dependency Agent — maps entity relationships and calculates blast radius
"""
from datetime import datetime
from agents.state import AgentState


def dependency_agent(state: AgentState) -> dict:
    adapter = state["adapter"]
    schema = adapter.get("schema", {})
    entity_name = state.get("entity_name", "Unknown")

    log_entry = {
        "agent": "Dependency",
        "timestamp": datetime.utcnow().isoformat(),
        "steps": [],
    }

    entities = schema.get("entities", [])
    relationships = schema.get("relationships", [])
    primary_entity = schema.get("primary_entity", "Entity")

    log_entry["steps"].append(f"Mapping relationships for entity: {entity_name}")
    log_entry["steps"].append(f"Schema has {len(entities)} entities and {len(relationships)} relationships")

    # Find all entities connected to the primary entity
    affected = []
    blast_parts = []

    for rel in relationships:
        from_e = rel.get("from", "")
        to_e = rel.get("to", "")
        rel_type = rel.get("type", "related_to")

        # Find labels for these entity ids
        from_label = next((e["label"] for e in entities if e["id"] == from_e), from_e)
        to_label = next((e["label"] for e in entities if e["id"] == to_e), to_e)

        affected.append(to_label)
        blast_parts.append(f"{entity_name} ({primary_entity}) → {to_label} ({rel_type})")
        log_entry["steps"].append(f"Relationship: {from_label} --[{rel_type}]--> {to_label}")

    if not affected:
        affected = [primary_entity]
        blast_parts = [f"{entity_name} ({primary_entity}) — no downstream dependencies found"]
        log_entry["steps"].append("No relationships defined in schema — isolated entity")

    blast_radius = " | ".join(blast_parts)
    log_entry["steps"].append(f"✓ Blast radius: {len(affected)} affected entities")

    return {
        "affected_entities": affected,
        "blast_radius": blast_radius,
        "agent_log": [log_entry],
    }
