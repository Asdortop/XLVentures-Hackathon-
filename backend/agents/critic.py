"""
Critic Agent — reflection layer that evaluates the top recommendation.
Runs after Recommender. Uses LLM to spot gaps or flag escalations.
Sets critique_flag: OK | LOW_CONFIDENCE | ESCALATE
"""
from datetime import datetime
from agents.state import AgentState


def critic_agent(state: AgentState) -> dict:
    ranked_actions = state.get("ranked_actions", [])
    entity_name = state.get("entity_name", "Entity")
    severity = state.get("severity", "medium")
    domain_name = state["adapter"].get("schema", {}).get("domain_name", "B2B")

    log_entry = {
        "agent": "Critic",
        "timestamp": datetime.utcnow().isoformat(),
        "steps": [],
    }

    if not ranked_actions:
        return {
            "critique": "No actions to evaluate.",
            "critique_flag": "OK",
            "agent_log": [log_entry],
        }

    top = ranked_actions[0]
    confidence = top.get("confidence", 0)

    # ── Rule-based flag ────────────────────────────────────────────────────
    if confidence < 0.65:
        base_flag = "LOW_CONFIDENCE"
        log_entry["steps"].append(f"⚠️ Low confidence ({confidence:.0%}) — flagging for review")
    elif severity == "critical" and confidence < 0.80:
        base_flag = "ESCALATE"
        log_entry["steps"].append(f"🔴 Critical severity with moderate confidence — recommend escalation")
    else:
        base_flag = "OK"
        log_entry["steps"].append(f"✓ Confidence {confidence:.0%} acceptable for severity '{severity}'")

    # ── LLM critique ──────────────────────────────────────────────────────
    critique = ""
    try:
        from llm_provider import llm
        evidence_types = [e.get("type", "") for e in top.get("evidence", [])]
        has_memory = any(t in ("semantic_memory", "similar_case") for t in evidence_types)

        critique_prompt = (
            f"You are a quality control reviewer for {domain_name} business recommendations.\n\n"
            f"Entity: {entity_name}\n"
            f"Situation: {state['interaction_text'][:250]}\n"
            f"Recommended action: {top['action']}\n"
            f"Confidence: {int(confidence*100)}%\n"
            f"Severity: {severity}\n"
            f"Has memory evidence: {has_memory}\n\n"
            f"In exactly 1 sentence: Is this recommendation appropriate? "
            f"Flag any missing steps, risks, or concerns. "
            f"If everything looks right, say so briefly."
        )
        critique = llm.generate(
            critique_prompt,
            "You are a business QA reviewer. Be concise and constructive."
        )
        log_entry["steps"].append(f"🤖 Critique: {critique[:100]}...")
    except Exception as e:
        critique = f"Recommendation is {'well-supported' if base_flag == 'OK' else 'flagged for review — confidence below threshold'}."
        log_entry["steps"].append(f"LLM critique: using fallback ({type(e).__name__})")

    # Upgrade flag if critique suggests escalation
    critique_lower = critique.lower()
    if base_flag == "OK" and any(w in critique_lower for w in ["escalate", "urgent", "immediately", "senior"]):
        base_flag = "ESCALATE"
        log_entry["steps"].append("Critic upgraded flag to ESCALATE based on LLM critique")

    log_entry["steps"].append(f"✓ Final critique flag: {base_flag}")

    return {
        "critique": critique,
        "critique_flag": base_flag,
        "agent_log": [log_entry],
    }
