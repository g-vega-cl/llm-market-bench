"""DAG validation and static lookahead linter for Strategy Recipes."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from recipes.schema import (
    ClassificationConfig,
    DAGEdge,
    DAGNode,
    GenerativeAnalystConfig,
    NewsSourceConfig,
    RecipeGraph,
    RiskOutputConfig,
    TechnicalGateConfig,
)


def _detect_cycle(node_ids: set[str], adjacency: dict[str, list[str]]) -> bool:
    """Return True if the directed graph contains a cycle."""
    visited: dict[str, int] = {nid: 0 for nid in node_ids}

    def dfs(node: str) -> bool:
        visited[node] = 1
        for neighbor in adjacency.get(node, []):
            if neighbor not in visited:
                continue
            if visited[neighbor] == 1:
                return True
            if visited[neighbor] == 0 and dfs(neighbor):
                return True
        visited[node] = 2
        return False

    return any(visited[nid] == 0 and dfs(nid) for nid in node_ids)


def _validate_node_config(node: DAGNode) -> str | None:
    """Validate a single node's configuration dictionary against its schema."""
    try:
        if node.type == "news_source":
            NewsSourceConfig(**node.config)
        elif node.type == "technical_gate":
            TechnicalGateConfig(**node.config)
        elif node.type == "classification":
            ClassificationConfig(**node.config)
        elif node.type == "generative_analyst":
            GenerativeAnalystConfig(**node.config)
        elif node.type == "risk_output":
            RiskOutputConfig(**node.config)
        return None
    except ValidationError as e:
        return f"Node '{node.id}' ({node.type}) config invalid: {e.errors()[0]['msg']}"


def _validate_nodes(
    nodes: list[DAGNode],
) -> tuple[set[str], dict[str, str], dict[str, list[str]], list[str]]:
    """Validate node unique IDs and config schemas."""
    node_ids: set[str] = set()
    node_types: dict[str, str] = {}
    adjacency: dict[str, list[str]] = {}
    errors: list[str] = []

    for node in nodes:
        if node.id in node_ids:
            errors.append(f"Duplicate node ID: '{node.id}'")
        node_ids.add(node.id)
        node_types[node.id] = node.type
        adjacency[node.id] = []

        cfg_err = _validate_node_config(node)
        if cfg_err:
            errors.append(cfg_err)

    return node_ids, node_types, adjacency, errors


def _validate_edges(
    edges: list[DAGEdge],
    node_ids: set[str],
    adjacency: dict[str, list[str]],
) -> list[str]:
    """Validate edge references and populate graph adjacency."""
    errors: list[str] = []
    for edge in edges:
        if edge.from_node not in node_ids:
            errors.append(f"Edge references non-existent source node: '{edge.from_node}'")
        if edge.to_node not in node_ids:
            errors.append(f"Edge references non-existent target node: '{edge.to_node}'")
        if edge.from_node in node_ids and edge.to_node in node_ids:
            adjacency[edge.from_node].append(edge.to_node)
    return errors


def validate_recipe_graph(graph_data: RecipeGraph | dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate a strategy recipe graph against schema and DAG invariants."""
    if isinstance(graph_data, dict):
        try:
            graph = RecipeGraph(**graph_data)
        except ValidationError as e:
            return False, [f"Schema validation error: {err['loc']} - {err['msg']}" for err in e.errors()]
        except Exception as e:
            return False, [f"Invalid recipe JSON structure: {e}"]
    else:
        graph = graph_data

    if not graph.nodes:
        return False, ["Recipe graph has no nodes."]

    node_ids, node_types, adjacency, errors = _validate_nodes(graph.nodes)
    errors.extend(_validate_edges(graph.edges, node_ids, adjacency))

    has_source = any(t in {"news_source", "price_tape"} for t in node_types.values())
    if not has_source:
        errors.append("Recipe graph requires at least one source node ('news_source' or 'price_tape').")

    has_sink = any(t == "risk_output" for t in node_types.values())
    if not has_sink:
        errors.append("Recipe graph requires a terminal 'risk_output' node.")

    if _detect_cycle(node_ids, adjacency):
        errors.append("Cycle detected in recipe graph. Strategy recipes must be Directed Acyclic Graphs (DAGs).")

    return len(errors) == 0, errors
