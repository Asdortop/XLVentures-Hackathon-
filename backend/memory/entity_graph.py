"""
NetworkX entity knowledge graph per domain.
Nodes: entity names, intent types, action names.
Edges: weighted by approval/rejection history from past NBAs.

Persisted to disk as graphs/{domain_slug}_graph.pkl.
Loaded lazily, cached in-process.

Purpose: gives the Dependency agent dynamic, learned relationship context
         beyond the static YAML schema. When a new entity appears,
         the graph can suggest similar past entities and their outcomes.
"""
import pickle
from pathlib import Path
import networkx as nx

GRAPH_DIR = Path(__file__).parent.parent / "graphs"
GRAPH_DIR.mkdir(exist_ok=True)

_graphs: dict[str, nx.DiGraph] = {}


def _graph_path(domain_slug: str) -> Path:
    return GRAPH_DIR / f"{domain_slug}_graph.pkl"


def get_graph(domain_slug: str) -> nx.DiGraph:
    if domain_slug not in _graphs:
        path = _graph_path(domain_slug)
        if path.exists():
            try:
                with open(path, "rb") as f:
                    _graphs[domain_slug] = pickle.load(f)
            except Exception:
                _graphs[domain_slug] = nx.DiGraph()
        else:
            _graphs[domain_slug] = nx.DiGraph()
    return _graphs[domain_slug]


def _save_graph(domain_slug: str):
    graph = _graphs.get(domain_slug)
    if graph is not None:
        try:
            with open(_graph_path(domain_slug), "wb") as f:
                pickle.dump(graph, f)
        except Exception as e:
            print(f"[EntityGraph] save failed for {domain_slug}: {e}")


def add_decision(
    domain_slug: str,
    entity_name: str,
    intent: str,
    action: str,
    approved: bool,
):
    """Record an approved/rejected decision into the entity graph."""
    graph = get_graph(domain_slug)

    # ── Entity node ────────────────────────────────────────────────────────
    if not graph.has_node(entity_name):
        graph.add_node(entity_name, node_type="entity", decisions=0, approved=0, rejected=0, intents=set())
    n = graph.nodes[entity_name]
    n["decisions"] = n.get("decisions", 0) + 1
    if approved:
        n["approved"] = n.get("approved", 0) + 1
    else:
        n["rejected"] = n.get("rejected", 0) + 1
    # Accumulate intents seen for this entity
    intents_set = n.get("intents", set())
    if isinstance(intents_set, list):
        intents_set = set(intents_set)
    intents_set.add(intent)
    n["intents"] = intents_set

    # ── Entity → Intent edge ───────────────────────────────────────────────
    if graph.has_edge(entity_name, intent):
        e = graph[entity_name][intent]
        e["count"] = e.get("count", 0) + 1
        if approved:
            e["approvals"] = e.get("approvals", 0) + 1
        # Track the action associated with this intent for this entity
        if approved and action:
            e["best_action"] = action
    else:
        graph.add_edge(
            entity_name, intent,
            node_type="entity_intent",
            count=1,
            approvals=1 if approved else 0,
            best_action=action if approved else "",
        )

    # ── Intent → Action edge ───────────────────────────────────────────────
    if graph.has_edge(intent, action):
        e = graph[intent][action]
        e["count"] = e.get("count", 0) + 1
        if approved:
            e["approvals"] = e.get("approvals", 0) + 1
    else:
        graph.add_edge(
            intent, action,
            node_type="intent_action",
            count=1,
            approvals=1 if approved else 0,
        )

    _save_graph(domain_slug)


def get_entity_context(domain_slug: str, entity_name: str, intent: str) -> list[dict]:
    """
    Return graph-derived context for this entity + intent combination.
    Used as additional evidence in the Dependency and Recommender agents.
    """
    graph = get_graph(domain_slug)
    context = []

    # ── This entity's history ──────────────────────────────────────────────
    if graph.has_node(entity_name):
        n = graph.nodes[entity_name]
        decisions = n.get("decisions", 0)
        if decisions > 0:
            approved_count = n.get("approved", n.get("approvals", 0))  # backward compat
            approval_rate = round(approved_count / decisions, 2)
            context.append({
                "type": "entity_history",
                "entity": entity_name,
                "decisions": decisions,
                "approval_rate": approval_rate,
                "message": f"{entity_name} has {decisions} past decision(s), {int(approval_rate*100)}% approved",
            })

        # Past intents for this entity
        for _, target, data in graph.out_edges(entity_name, data=True):
            if data.get("count", 0) > 0:
                context.append({
                    "type": "past_intent",
                    "entity": entity_name,
                    "intent": target,
                    "count": data.get("count", 0),
                    "best_action": data.get("best_action", ""),
                    "approval_rate": round(
                        data.get("approvals", 0) / max(data.get("count", 1), 1), 2
                    ),
                })

    # ── Similar entities that had the same intent ──────────────────────────
    similar = []
    for node in graph.nodes():
        if node == entity_name:
            continue
        if graph.has_edge(node, intent):
            edge = graph[node][intent]
            if edge.get("approvals", 0) > 0:
                similar.append({
                    "type": "similar_entity",
                    "entity": node,
                    "intent": intent,
                    "best_action": edge.get("best_action", ""),
                    "approvals": edge.get("approvals", 0),
                    "message": f"Similar entity '{node}' had '{intent}' → '{edge.get('best_action', 'action')}' (approved {edge.get('approvals', 0)}×)",
                })

    # Sort by most approvals, take top 2
    similar.sort(key=lambda x: x["approvals"], reverse=True)
    context.extend(similar[:2])

    return context


def get_graph_stats(domain_slug: str) -> dict:
    graph = get_graph(domain_slug)
    return {
        "nodes": graph.number_of_nodes(),
        "edges": graph.number_of_edges(),
        "entities": [n for n, d in graph.nodes(data=True) if d.get("node_type") == "entity"],
    }
