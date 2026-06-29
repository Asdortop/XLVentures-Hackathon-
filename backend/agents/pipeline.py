"""
LangGraph pipeline — wires all 5 agents into a directed graph
"""
from langgraph.graph import StateGraph, END
from agents.state import AgentState
from agents.planner import planner_agent
from agents.context import context_agent
from agents.dependency import dependency_agent
from agents.risk import risk_agent
from agents.recommender import recommender_agent


def build_pipeline():
    graph = StateGraph(AgentState)

    graph.add_node("planner", planner_agent)
    graph.add_node("context", context_agent)
    graph.add_node("dependency", dependency_agent)
    graph.add_node("risk", risk_agent)
    graph.add_node("recommender", recommender_agent)

    graph.set_entry_point("planner")
    graph.add_edge("planner", "context")
    graph.add_edge("context", "dependency")
    graph.add_edge("dependency", "risk")
    graph.add_edge("risk", "recommender")
    graph.add_edge("recommender", END)

    return graph.compile()


pipeline = build_pipeline()


def run_pipeline(
    domain_id: int,
    interaction_id: int,
    interaction_text: str,
    entity_name: str,
    adapter: dict,
) -> dict:
    initial_state = AgentState(
        domain_id=domain_id,
        interaction_id=interaction_id,
        interaction_text=interaction_text,
        entity_name=entity_name,
        adapter=adapter,
        matched_intent="",
        keywords_found=[],
        memory_patterns=[],
        playbook_matches=[],
        crm_context="",
        history=[],
        affected_entities=[],
        blast_radius="",
        severity="medium",
        risk_signals=[],
        triggered_rules=[],
        ranked_actions=[],
        agent_log=[],
        error=None,
    )

    result = pipeline.invoke(initial_state)
    return result
