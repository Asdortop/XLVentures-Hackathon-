"""
LangGraph pipeline — 6-agent directed graph.
Planner → Context → Dependency → Risk → Recommender → Critic → END
"""
from langgraph.graph import StateGraph, END
from agents.state import AgentState
from agents.planner import planner_agent
from agents.context import context_agent
from agents.dependency import dependency_agent
from agents.risk import risk_agent
from agents.recommender import recommender_agent
from agents.critic import critic_agent


def build_pipeline():
    graph = StateGraph(AgentState)

    graph.add_node("planner", planner_agent)
    graph.add_node("context", context_agent)
    graph.add_node("dependency", dependency_agent)
    graph.add_node("risk", risk_agent)
    graph.add_node("recommender", recommender_agent)
    graph.add_node("critic", critic_agent)

    graph.set_entry_point("planner")
    graph.add_edge("planner", "context")
    graph.add_edge("context", "dependency")
    graph.add_edge("dependency", "risk")
    graph.add_edge("risk", "recommender")
    graph.add_edge("recommender", "critic")
    graph.add_edge("critic", END)

    return graph.compile()


pipeline = build_pipeline()


def run_pipeline(
    domain_id: int,
    domain_slug: str,
    interaction_id: int,
    interaction_text: str,
    entity_name: str,
    adapter: dict,
) -> dict:
    initial_state = AgentState(
        domain_id=domain_id,
        domain_slug=domain_slug,
        interaction_id=interaction_id,
        interaction_text=interaction_text,
        entity_name=entity_name,
        adapter=adapter,
        matched_intent="",
        keywords_found=[],
        memory_patterns=[],
        semantic_memories=[],
        playbook_matches=[],
        crm_context="",
        history=[],
        affected_entities=[],
        blast_radius="",
        graph_context=[],
        severity="medium",
        risk_signals=[],
        triggered_rules=[],
        risk_reasoning="",
        ranked_actions=[],
        critique="",
        critique_flag="OK",
        agent_log=[],
        error=None,
    )

    result = pipeline.invoke(initial_state)
    return result


# ── Sequential runner for SSE streaming ──────────────────────────────────────
AGENT_SEQUENCE = [
    ("planner",     "✦", planner_agent),
    ("context",     "◈", context_agent),
    ("dependency",  "⬡", dependency_agent),
    ("risk",        "◎", risk_agent),
    ("recommender", "★", recommender_agent),
    ("critic",      "⚑", critic_agent),
]


def run_pipeline_steps(
    domain_id: int,
    domain_slug: str,
    interaction_id: int,
    interaction_text: str,
    entity_name: str,
    adapter: dict,
):
    """
    Generator that yields (agent_name, icon, partial_result) tuples after each agent.
    Used by the SSE streaming endpoint to emit live progress.
    """
    state = dict(AgentState(
        domain_id=domain_id,
        domain_slug=domain_slug,
        interaction_id=interaction_id,
        interaction_text=interaction_text,
        entity_name=entity_name,
        adapter=adapter,
        matched_intent="",
        keywords_found=[],
        memory_patterns=[],
        semantic_memories=[],
        playbook_matches=[],
        crm_context="",
        history=[],
        affected_entities=[],
        blast_radius="",
        graph_context=[],
        severity="medium",
        risk_signals=[],
        triggered_rules=[],
        risk_reasoning="",
        ranked_actions=[],
        critique="",
        critique_flag="OK",
        agent_log=[],
        error=None,
    ))

    for agent_name, icon, agent_fn in AGENT_SEQUENCE:
        result = agent_fn(state)
        # Merge result into state (accumulate agent_log)
        for key, value in result.items():
            if key == "agent_log":
                state["agent_log"] = state.get("agent_log", []) + value
            else:
                state[key] = value
        yield agent_name, icon, result, state
