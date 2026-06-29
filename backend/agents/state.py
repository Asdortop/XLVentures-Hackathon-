"""
LangGraph 5-agent pipeline:
Planner → Context → Dependency → Risk → Recommender
"""
from typing import TypedDict, List, Optional, Annotated
from langgraph.graph import StateGraph, END
import operator


class AgentState(TypedDict):
    # Input
    domain_id: int
    interaction_id: int
    interaction_text: str
    entity_name: str
    adapter: dict

    # Planner output
    matched_intent: str
    keywords_found: List[str]

    # Context output
    memory_patterns: List[dict]
    playbook_matches: List[dict]
    crm_context: str
    history: List[dict]

    # Dependency output
    affected_entities: List[str]
    blast_radius: str

    # Risk output
    severity: str
    risk_signals: List[str]
    triggered_rules: List[str]

    # Recommender output
    ranked_actions: List[dict]

    # Logs — accumulated across all agents
    agent_log: Annotated[List[dict], operator.add]

    error: Optional[str]
