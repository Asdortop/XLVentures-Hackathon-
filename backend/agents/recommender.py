"""
Recommender Agent — matches actions, scores confidence, builds evidence
Confidence formula: base_confidence × severity_multiplier × memory_boost
"""
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
    playbook_matches = state.get("playbook_matches", [])
    risk_signals = state.get("risk_signals", [])
    blast_radius = state.get("blast_radius", "")
    crm_context = state.get("crm_context", "")

    log_entry = {
        "agent": "Recommender",
        "timestamp": datetime.utcnow().isoformat(),
        "steps": [],
    }

    log_entry["steps"].append(f"Matching actions for intent: '{intent}', severity: {severity}")

    sev_mult = SEVERITY_MULTIPLIER.get(severity, 1.0)

    # Memory boost: scales dynamically with how many times this intent was approved
    # Each approval = +3% boost, capped at +20% max
    memory_boost = 0.0
    best_pattern = None
    for mp in memory_patterns:
        if mp.get("success_rate", 0) > 0.5 and mp.get("success_count", 0) > 0:
            boost = min(0.20, mp["success_count"] * 0.03)
            if boost > memory_boost:
                memory_boost = boost
                best_pattern = mp
    if memory_boost > 0:
        log_entry["steps"].append(
            f"Memory boost applied: +{memory_boost:.0%} from {best_pattern['success_count']} past approvals for '{intent}'"
        )


    scored_actions = []

    for template in action_templates:
        # Check if this action applies to current intent
        template_intents = template.get("intents", [])
        template_keywords = [k.lower() for k in template.get("keywords", [])]

        intent_match = intent in template_intents or not template_intents
        keyword_overlap = [k for k in template_keywords if k in text or k in keywords]

        if not intent_match and not keyword_overlap:
            continue

        # Score
        base = template.get("base_confidence", 0.65)
        confidence = min(0.99, base * sev_mult + memory_boost)
        confidence = round(confidence, 3)

        # Build evidence
        evidence = []

        # Interaction evidence
        evidence.append({
            "type": "interaction",
            "source": "Current Interaction",
            "content": state["interaction_text"][:200],
        })

        # Playbook evidence
        if playbook_matches:
            pb = playbook_matches[0]
            evidence.append({
                "type": "playbook",
                "source": pb["title"],
                "content": pb["excerpt"],
            })

        # Memory evidence
        for mp in memory_patterns[:1]:
            evidence.append({
                "type": "similar_case",
                "source": f"Past case — {mp['issue_type']}",
                "content": f"Resolution: {mp['resolution']} | Success rate: {int(mp['success_rate']*100)}% ({mp['success_count']} times)",
            })

        # CRM evidence
        if crm_context:
            evidence.append({
                "type": "crm",
                "source": "CRM Record",
                "content": crm_context[:200],
            })

        # Graph path evidence
        if blast_radius:
            evidence.append({
                "type": "graph_path",
                "source": "Dependency Map",
                "content": blast_radius,
            })

        # Risk signal evidence
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
                "memory_boost": memory_boost,
            },
            "evidence": evidence,
        })

        log_entry["steps"].append(
            f"Action '{template['action'][:50]}...' scored {confidence:.0%}"
        )

    # Sort by confidence descending
    scored_actions.sort(key=lambda x: x["confidence"], reverse=True)

    # Add fallback if nothing matched
    if not scored_actions and fallback:
        scored_actions.append({
            "action": fallback.get("action", "Review and schedule check-in"),
            "owner": fallback.get("owner", "Team"),
            "priority": fallback.get("priority", "medium"),
            "action_type": "task",
            "base_confidence": fallback.get("base_confidence", 0.60),
            "confidence": fallback.get("base_confidence", 0.60),
            "estimated_hours": 1.0,
            "confidence_breakdown": {"base": 0.60, "severity_multiplier": 1.0, "memory_boost": 0},
            "evidence": [{"type": "interaction", "source": "Current Interaction", "content": state["interaction_text"][:200]}],
        })
        log_entry["steps"].append("No actions matched — using fallback action")

    # Add rank
    for i, action in enumerate(scored_actions):
        action["rank"] = i + 1

    log_entry["steps"].append(f"✓ Generated {len(scored_actions)} ranked actions")

    return {
        "ranked_actions": scored_actions,
        "agent_log": [log_entry],
    }
