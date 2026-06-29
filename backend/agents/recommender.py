"""
Recommender Agent — matches actions, scores confidence, builds evidence.
Confidence formula: base_confidence × severity_multiplier × memory_boost × semantic_boost
NEW: LLM generates a 2-sentence natural-language reasoning summary for the top action.
"""
import re
from datetime import datetime
from agents.state import AgentState


SEVERITY_MULTIPLIER = {
    "low": 0.85,
    "medium": 1.0,
    "high": 1.08,
    "critical": 1.15,
}


def recommender_agent(state: AgentState) -> dict:
    adapter = state["adapter"]
    actions_config = adapter.get("actions", {})
    action_templates = actions_config.get("actions", [])
    fallback = actions_config.get("fallback", {})

    intent = state.get("matched_intent", "general")
    text = state["interaction_text"].lower()
    keywords = [k.lower() for k in state.get("keywords_found", [])]
    severity = state.get("severity", "medium")
    memory_patterns = state.get("memory_patterns", [])
    semantic_memories = state.get("semantic_memories", [])
    playbook_matches = state.get("playbook_matches", [])
    risk_signals = state.get("risk_signals", [])
    blast_radius = state.get("blast_radius", "")
    crm_context = state.get("crm_context", "")
    graph_context = state.get("graph_context", [])
    entity_name = state.get("entity_name", "Entity")
    domain_name = adapter.get("schema", {}).get("domain_name", "B2B")

    log_entry = {
        "agent": "Recommender",
        "timestamp": datetime.utcnow().isoformat(),
        "steps": [],
    }
    log_entry["steps"].append(f"Matching actions for intent: '{intent}', severity: {severity}")

    sev_mult = SEVERITY_MULTIPLIER.get(severity, 1.0)

    # ── SQL memory boost ───────────────────────────────────────────────────
    memory_boost = 0.0
    best_sql_pattern = None
    for mp in memory_patterns:
        if mp.get("success_rate", 0) > 0.5 and mp.get("success_count", 0) > 0:
            boost = min(0.20, mp["success_count"] * 0.03)
            if boost > memory_boost:
                memory_boost = boost
                best_sql_pattern = mp
    if memory_boost > 0:
        log_entry["steps"].append(
            f"SQL memory boost: +{memory_boost:.0%} from {best_sql_pattern['success_count']} approvals"
        )

    # ── Semantic memory boost ─────────────────────────────────────────────
    semantic_boost = 0.0
    best_semantic = None
    for sm in semantic_memories:
        boost = sm.get("similarity", 0) * 0.15  # up to +15% for perfect match
        if boost > semantic_boost:
            semantic_boost = boost
            best_semantic = sm
    if semantic_boost > 0:
        log_entry["steps"].append(
            f"Semantic memory boost: +{semantic_boost:.0%} (similarity: {best_semantic['similarity']})"
        )

    total_memory_boost = min(0.25, memory_boost + semantic_boost)

    # ── Graph boost ────────────────────────────────────────────────────────
    graph_boost = 0.0
    for ctx in graph_context:
        if ctx.get("type") == "entity_history" and ctx.get("approval_rate", 0) > 0.7:
            graph_boost = min(0.05, ctx["approval_rate"] * 0.05)
            log_entry["steps"].append(f"Graph boost: +{graph_boost:.0%} from entity approval history")
            break

    # ── Score actions ─────────────────────────────────────────────────────
    scored_actions = []

    for template in action_templates:
        template_intents = template.get("intents", [])
        template_keywords = [k.lower() for k in template.get("keywords", [])]

        intent_match = intent in template_intents or not template_intents
        keyword_overlap = [k for k in template_keywords if k in text or k in keywords]

        if not intent_match and not keyword_overlap:
            continue

        base = template.get("base_confidence", 0.65)
        confidence = min(0.99, base * sev_mult + total_memory_boost + graph_boost)
        confidence = round(confidence, 3)

        # ── Build evidence chain ──────────────────────────────────────────
        evidence = []

        # Interaction
        evidence.append({
            "type": "interaction",
            "source": "Current Interaction",
            "content": state["interaction_text"][:200],
        })

        # Semantic memory (highest priority evidence)
        if best_semantic:
            evidence.append({
                "type": "semantic_memory",
                "source": f"Semantic Match ({int(best_semantic['similarity']*100)}% similar)",
                "content": f"Past case: {best_semantic.get('document', '')[:200]}",
            })

        # Playbook
        if playbook_matches:
            pb = playbook_matches[0]
            evidence.append({
                "type": "playbook",
                "source": pb["title"],
                "content": pb["excerpt"],
            })

        # SQL Memory
        for mp in memory_patterns[:1]:
            evidence.append({
                "type": "similar_case",
                "source": f"Past case — {mp['issue_type']}",
                "content": f"Resolution: {mp['resolution']} | Success rate: {int(mp.get('success_rate',0)*100)}% ({mp.get('success_count',0)} times)",
            })

        # CRM
        if crm_context:
            evidence.append({
                "type": "crm",
                "source": "CRM Record",
                "content": crm_context[:200],
            })

        # Graph
        for ctx in graph_context[:1]:
            if ctx.get("message"):
                evidence.append({
                    "type": "graph_path",
                    "source": "Entity Knowledge Graph",
                    "content": ctx["message"],
                })

        # Risk
        for sig in risk_signals[:1]:
            evidence.append({
                "type": "risk_signal",
                "source": "Risk Analysis",
                "content": sig,
            })

        scored_actions.append({
            "action": template["action"],
            "owner": template.get("owner", "Team"),
            "priority": template.get("priority", severity),
            "action_type": template.get("action_type", "task"),
            "base_confidence": base,
            "confidence": confidence,
            "estimated_hours": template.get("estimated_hours", 1.0),
            "confidence_breakdown": {
                "base": round(base, 3),
                "severity_multiplier": sev_mult,
                "memory_boost": round(total_memory_boost, 3),
                "graph_boost": round(graph_boost, 3),
            },
            "evidence": evidence,
        })
        log_entry["steps"].append(f"Action '{template['action'][:50]}' → {confidence:.0%}")

    # Sort by confidence
    scored_actions.sort(key=lambda x: x["confidence"], reverse=True)

    # Fallback if nothing matched
    if not scored_actions and fallback:
        scored_actions.append({
            "action": fallback.get("action", "Review and schedule check-in"),
            "owner": fallback.get("owner", "Team"),
            "priority": fallback.get("priority", "medium"),
            "action_type": "task",
            "base_confidence": fallback.get("base_confidence", 0.60),
            "confidence": fallback.get("base_confidence", 0.60),
            "estimated_hours": 1.0,
            "confidence_breakdown": {"base": 0.60, "severity_multiplier": 1.0, "memory_boost": 0, "graph_boost": 0},
            "evidence": [{"type": "interaction", "source": "Current Interaction", "content": state["interaction_text"][:200]}],
        })
        log_entry["steps"].append("No actions matched — using fallback action")

    # Add rank
    for i, action in enumerate(scored_actions):
        action["rank"] = i + 1

    # ── LLM Reasoning Summary ─────────────────────────────────────────────
    if scored_actions:
        top = scored_actions[0]
        evidence_texts = [e["content"][:100] for e in top.get("evidence", [])[:3]]
        risk_reasoning = state.get("risk_reasoning", "")

        try:
            from llm_provider import llm
            reasoning_prompt = (
                f"You are a senior {domain_name} advisor making a time-sensitive recommendation.\n\n"
                f"Situation:\n"
                f"- Entity: {entity_name}\n"
                f"- Interaction: {state['interaction_text'][:300]}\n"
                f"- Risk level: {severity.upper()}\n"
                f"- Risk rationale: {risk_reasoning}\n"
                f"- Top recommended action: {top['action']}\n"
                f"- Key evidence: {'; '.join(evidence_texts)}\n\n"
                f"Write exactly 2 sentences:\n"
                f"1. WHY this specific action is right for {entity_name}'s situation (reference evidence)\n"
                f"2. What business outcome it protects and how urgently\n\n"
                f"Be specific. Do NOT use generic phrases. Reference actual details from the evidence."
            )
            reasoning = llm.generate(
                reasoning_prompt,
                "You are a senior business advisor. Be concise, specific, and evidence-based."
            )
            scored_actions[0]["reasoning_summary"] = reasoning
            log_entry["steps"].append(f"🤖 Generated reasoning: {reasoning[:100]}...")
        except Exception as e:
            scored_actions[0]["reasoning_summary"] = ""
            log_entry["steps"].append(f"LLM reasoning: skipped ({type(e).__name__})")

    log_entry["steps"].append(f"✓ Generated {len(scored_actions)} ranked actions")

    return {
        "ranked_actions": scored_actions,
        "agent_log": [log_entry],
    }
