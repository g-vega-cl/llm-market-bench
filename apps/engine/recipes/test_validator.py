"""Unit tests for Recipe Studio DAG validator."""

from recipes.validator import validate_recipe_graph


def test_validate_valid_recipe_graph():
    valid_graph = {
        "version": "1.0",
        "name": "Semiconductor VWAP Strategy",
        "cadence": "5m",
        "nodes": [
            {
                "id": "src_1",
                "type": "news_source",
                "title": "Semi News",
                "config": {"bucket": "semiconductors", "tickers": ["NVDA", "AMD"]},
            },
            {
                "id": "gate_1",
                "type": "technical_gate",
                "title": "RSI Gate",
                "config": {"conditions": [{"metric": "rsi_14", "operator": "<", "target": 35.0}]},
            },
            {
                "id": "out_1",
                "type": "risk_output",
                "title": "Output Order",
                "config": {"action": "BUY", "stop_loss_pct": 1.5, "target_profit_pct": 3.0},
            },
        ],
        "edges": [
            {"from": "src_1", "to": "gate_1"},
            {"from": "gate_1", "to": "out_1"},
        ],
    }

    is_valid, errors = validate_recipe_graph(valid_graph)
    assert is_valid is True
    assert len(errors) == 0


def test_validate_missing_source():
    graph = {
        "nodes": [
            {
                "id": "out_1",
                "type": "risk_output",
                "config": {"action": "BUY"},
            }
        ],
        "edges": [],
    }
    is_valid, errors = validate_recipe_graph(graph)
    assert is_valid is False
    assert any("at least one source" in e for e in errors)


def test_validate_missing_sink():
    graph = {
        "nodes": [
            {
                "id": "src_1",
                "type": "news_source",
                "config": {"bucket": "semiconductors"},
            }
        ],
        "edges": [],
    }
    is_valid, errors = validate_recipe_graph(graph)
    assert is_valid is False
    assert any("terminal 'risk_output'" in e for e in errors)


def test_validate_cycle_detection():
    graph = {
        "nodes": [
            {"id": "src_1", "type": "news_source", "config": {}},
            {"id": "gate_1", "type": "technical_gate", "config": {}},
            {"id": "gate_2", "type": "technical_gate", "config": {}},
            {"id": "out_1", "type": "risk_output", "config": {"action": "BUY"}},
        ],
        "edges": [
            {"from": "src_1", "to": "gate_1"},
            {"from": "gate_1", "to": "gate_2"},
            {"from": "gate_2", "to": "gate_1"},  # Cycle!
            {"from": "gate_2", "to": "out_1"},
        ],
    }
    is_valid, errors = validate_recipe_graph(graph)
    assert is_valid is False
    assert any("Cycle detected" in e for e in errors)


def test_validate_bad_edge_reference():
    graph = {
        "nodes": [
            {"id": "src_1", "type": "news_source", "config": {}},
            {"id": "out_1", "type": "risk_output", "config": {"action": "BUY"}},
        ],
        "edges": [
            {"from": "src_1", "to": "non_existent_node"},
        ],
    }
    is_valid, errors = validate_recipe_graph(graph)
    assert is_valid is False
    assert any("non-existent target node" in e for e in errors)
