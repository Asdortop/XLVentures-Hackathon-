"""
Risk Agent — evaluates business rules and assigns severity
"""
import re
from datetime import datetime
from agents.state import AgentState


def risk_agent(state: AgentState) -> dict:
    adapter = state["adapter"]
    rules = adapter.get("rules", {})
    text = state["interaction_text"].lower()
    keywords_found = [k.lower() for k in state.get("keywords_found", [])]

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

    # ── 1. Keyword-based severity ────────────────────────────────────────────
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

    # ── 2. Deadline detection ────────────────────────────────────────────────
    deadline_hours = rules.get("deadline_warning_hours", 48)
    deadline_patterns = [
        r"(\d+)\s*(hour|hr)s?\s*(left|remaining|deadline|away)",
        r"by\s+(tomorrow|tonight|friday|monday|tuesday|wednesday|thursday|saturday|sunday)",
        r"in\s+(\d+)\s*(hour|hr|day)s?",
        r"(\d+)\s*(day)s?\s*(to|until)\s+(renewal|deadline|deadline|due)",
    ]
    for pattern in deadline_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            risk_signals.append(f"Deadline detected in interaction text")
            triggered_rules.append(f"Rule: deadline detected → escalate to high severity")
            if severity_order.index("high") > severity_order.index(detected_severity):
                detected_severity = "high"
            log_entry["steps"].append("⚠️ Deadline pattern detected in text")
            break

    # ── 3. Rejection count threshold ─────────────────────────────────────────
    rejection_threshold = rules.get("rejection_count_critical", 3)
    rejection_match = re.search(r"(\d+)(rd|st|nd|th)?\s*rejection|rejected\s+(\d+)", text, re.IGNORECASE)
    if rejection_match:
        risk_signals.append(f"Rejection count detected in text")
        triggered_rules.append(f"Rule: rejection threshold ({rejection_threshold}) → critical")
        if severity_order.index("critical") > severity_order.index(detected_severity):
            detected_severity = "critical"
        log_entry["steps"].append(f"🔴 Rejection pattern matched → critical")

    # ── 4. Health score threshold ─────────────────────────────────────────────
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

    log_entry["steps"].append(f"✓ Final severity: {detected_severity.upper()}")

    return {
        "severity": detected_severity,
        "risk_signals": risk_signals,
        "triggered_rules": triggered_rules,
        "agent_log": [log_entry],
    }
