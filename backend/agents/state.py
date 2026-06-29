"""
LangGraph 5+1 agent pipeline state definition.
Planner → Context → Dependency → Risk → Recommender → Critic
"""
from typing import TypedDict, List, Optional, Annotated
from langgraph.graph import StateGraph, END
import operator


class AgentState(TypedDict):
    # ── Input ─────────────────────────────────────────────────────────────
    domain_id: int
    domain_slug: str          # used for vector store + entity graph isolation
    interaction_id: int
    interaction_text: str
    entity_name: str
    adapter: dict

    # ── Planner output ─────────────────────────────────────────────────────
    matched_intent: str
    keywords_found: List[str]

    # ── Context output ─────────────────────────────────────────────────────
    memory_patterns: List[dict]        # SQL fallback patterns
    semantic_memories: List[dict]      # ChromaDB vector results
    playbook_matches: List[dict]
    crm_context: str
    history: List[dict]

    # ── Dependency output ──────────────────────────────────────────────────
    affected_entities: List[str]
    blast_radius: str
    graph_context: List[dict]          # GraphRAG entity graph context

    # ── Risk output ───────────────────────────────────────────────────────
    severity: str
    risk_signals: List[str]
    triggered_rules: List[str]
    risk_reasoning: str                # LLM-generated risk rationale

    # ── Recommender output ────────────────────────────────────────────────
    ranked_actions: List[dict]

    # ── Critic output ─────────────────────────────────────────────────────
    critique: str
    critique_flag: str                 # OK | LOW_CONFIDENCE | ESCALATE

    # ── Accumulated across all agents ─────────────────────────────────────
    agent_log: Annotated[List[dict], operator.add]

    error: Optional[str]
