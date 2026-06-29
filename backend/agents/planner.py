"""
Planner Agent — classifies the interaction intent using adapter's intents.yaml
"""
from datetime import datetime
from agents.state import AgentState


def planner_agent(state: AgentState) -> dict:
    text = state["interaction_text"].lower()
    adapter = state["adapter"]
    intents = adapter.get("intents", {}).get("intents", [])

    log_entry = {
        "agent": "Planner",
        "timestamp": datetime.utcnow().isoformat(),
        "steps": [],
    }

    best_intent = None
    best_score = 0
    all_keywords_found = []

    log_entry["steps"].append(f"Analyzing text: '{state['interaction_text'][:100]}...'")
    log_entry["steps"].append(f"Scanning {len(intents)} intents from adapter")

    for intent in intents:
        keywords = [k.lower() for k in intent.get("keywords", [])]
        matched = [k for k in keywords if k in text]
        score = len(matched)

        if matched:
            log_entry["steps"].append(
                f"Intent '{intent['id']}' matched {len(matched)} keywords: {matched}"
            )

        if score > best_score:
            best_score = score
            best_intent = intent["id"]
            all_keywords_found = matched

    if not best_intent and intents:
        best_intent = intents[0]["id"]
        log_entry["steps"].append(f"No keyword match — defaulting to first intent: {best_intent}")
    elif best_intent:
        log_entry["steps"].append(f"✓ Matched intent: '{best_intent}' (score: {best_score})")

    return {
        "matched_intent": best_intent or "general",
        "keywords_found": all_keywords_found,
        "agent_log": [log_entry],
    }
