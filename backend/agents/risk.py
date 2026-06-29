"""
Risk Agent — evaluates business rules and assigns severity.
Two-layer approach:
  1. Rule-based (keywords, deadlines, rejection count, health score) — fast, deterministic
  2. LLM assessment — contextual reasoning that catches nuance rules miss
Final severity = max(rule-based, LLM-based).
"""
import re
import json
from datetime import datetime
from agents.state import AgentState


def risk_agent(state: AgentState) -> dict:
    adapter = state["adapter"]
    rules = adapter.get("rules", {})
    text = state["interaction_text"].lower()
    keywords_found = [k.lower() for k in state.get("keywords_found", [])]
    entity_name = state.get("entity_name", "Entity")
    domain_name = adapter.get("schema", {}).get("domain_name", "B2B")

    log_entry = {
        "agent": "Risk",
        "timestamp": datetime.utcnow().isoformat(),
        "steps": [],
    }

    severity_map = rules.get("severity_keywords", {
        "critical": ["urgent", "cancel", "rejected", "churn"],
        "high": ["concern", "dropping", "declining", "issue"],
        "medium": ["question", "wondering", "thinking"],
        "low": ["update", "fyi", "info"],
    })

    risk_signals = []
    triggered_rules = []
    detected_severity = "low"
    severity_order = ["low", "medium", "high", "critical"]

    # ── 1. Keyword-based severity ─────────────────────────────────────────
    for severity_level in ["critical", "high", "medium", "low"]:
        level_keywords = [k.lower() for k in severity_map.get(severity_level, [])]
        matched = [k for k in level_keywords if k in text]
        if matched:
            risk_signals.append(f"Severity keywords detected: {matched}")
            triggered_rules.append(f"Rule: '{matched[0]}' keyword → {severity_level} severity")
            if severity_order.index(severity_level) > severity_order.index(detected_severity):
                detected_severity = severity_level
            log_entry["steps"].append(f"Keyword trigger: {matched} → {severity_level}")
            break

    # ── 2. Deadline detection ─────────────────────────────────────────────
    deadline_patterns = [
        r"(\d+)\s*(hour|hr)s?\s*(left|remaining|deadline|away)",
        r"by\s+(tomorrow|tonight|friday|monday|tuesday|wednesday|thursday|saturday|sunday)",
        r"in\s+(\d+)\s*(hour|hr|day)s?",
        r"(\d+)\s*(day)s?\s*(to|until)\s+(renewal|deadline|due)",
    ]
    for pattern in deadline_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            risk_signals.append("Deadline detected in interaction text")
            triggered_rules.append("Rule: deadline detected → escalate to high severity")
            if severity_order.index("high") > severity_order.index(detected_severity):
                detected_severity = "high"
            log_entry["steps"].append("⚠️ Deadline pattern detected in text")
            break

    # ── 3. Rejection count threshold ──────────────────────────────────────
    rejection_threshold = rules.get("rejection_count_critical", 3)
    rejection_match = re.search(r"(\d+)(rd|st|nd|th)?\s*rejection|rejected\s+(\d+)", text, re.IGNORECASE)
    if rejection_match:
        risk_signals.append("Rejection count detected in text")
        triggered_rules.append(f"Rule: rejection threshold ({rejection_threshold}) → critical")
        if severity_order.index("critical") > severity_order.index(detected_severity):
            detected_severity = "critical"
        log_entry["steps"].append("🔴 Rejection pattern matched → critical")

    # ── 4. Health score threshold ─────────────────────────────────────────
    health_threshold = rules.get("health_score_critical", 60)
    health_match = re.search(r"health\s+score[:\s]+(\d+)", text, re.IGNORECASE)
    if health_match:
        score = int(health_match.group(1))
        if score < health_threshold:
            risk_signals.append(f"Health score {score} below threshold {health_threshold}")
            triggered_rules.append(f"Rule: health score {score} < {health_threshold} → critical")
            if severity_order.index("critical") > severity_order.index(detected_severity):
                detected_severity = "critical"
            log_entry["steps"].append(f"🔴 Health score {score} critical")

    if not risk_signals:
        risk_signals = ["No specific risk triggers detected — using default severity"]
        log_entry["steps"].append("No explicit risk signals found")

    # ── 5. LLM-powered contextual risk assessment ─────────────────────────
    risk_reasoning = ""
    try:
        from llm_provider import llm
        # Build compact context for LLM
        crm_ctx = state.get("crm_context", "")[:200]
        signals_summary = "; ".join(risk_signals[:3])

        risk_prompt = (
            f"You are a {domain_name} business risk analyst. Assess the urgency of this situation.\n\n"
            f"Entity: {entity_name}\n"
            f"Interaction: {state['interaction_text'][:400]}\n"
            f"Rule-based signals: {signals_summary}\n"
            f"CRM context: {crm_ctx}\n\n"
            f"Classify severity: critical / high / medium / low\n"
            f"Consider: urgency, financial impact, relationship risk, time sensitivity.\n\n"
            f'Respond ONLY as JSON: {{"severity": "high", "reasoning": "one concise sentence", "additional_signals": ["signal1"]}}'
        )

        raw = llm.generate(risk_prompt, "You are a business risk analyst. Respond only with valid JSON.")
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            parsed = json.loads(match.group())
            llm_severity = parsed.get("severity", detected_severity).lower()
            risk_reasoning = parsed.get("reasoning", "")
            additional = parsed.get("additional_signals", [])

            # Take the higher of rule-based vs LLM severity
            if llm_severity in severity_order and severity_order.index(llm_severity) > severity_order.index(detected_severity):
                detected_severity = llm_severity
                triggered_rules.append(f"Rule: LLM assessment → {llm_severity} severity")

            risk_signals.extend(additional)
            log_entry["steps"].append(f"🤖 LLM risk assessment: {risk_reasoning}")
    except Exception as e:
        risk_reasoning = ""
        log_entry["steps"].append(f"LLM risk: using rule-based fallback ({type(e).__name__})")

    log_entry["steps"].append(f"✓ Final severity: {detected_severity.upper()}")

    return {
        "severity": detected_severity,
        "risk_signals": risk_signals,
        "triggered_rules": triggered_rules,
        "risk_reasoning": risk_reasoning,
        "agent_log": [log_entry],
    }
