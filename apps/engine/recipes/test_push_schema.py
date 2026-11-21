"""Push v2 schema contract: one stage, no per-stage title, always a name."""

import pytest
from pydantic import ValidationError

from recipes.push_schema import DEFAULT_STRATEGY_NAME, PushStrategy


def _legacy_graph() -> dict:
    """A graph stored before the stage `title` field was removed."""
    return {
        "version": "2.0-push",
        "name": "  Legacy Graph  ",
        "cadence": "3h",
        "stages": [
            {
                "id": "stage-1",
                "title": "Catalyst & Technical Analysis",
                "blocks": [
                    {"id": "b1", "type": "prompt", "text": "Analyze NVDA."},
                    {"id": "b2", "type": "output_format"},
                ],
                "selected_tools": ["get_technical_indicators"],
            }
        ],
    }


def test_legacy_stage_title_is_ignored_and_dropped():
    strategy = PushStrategy.model_validate(_legacy_graph())

    assert strategy.name == "Legacy Graph"
    assert "title" not in strategy.model_dump()["stages"][0]


def test_null_name_is_normalized_instead_of_rejected():
    graph = _legacy_graph()
    graph["name"] = None

    assert PushStrategy.model_validate(graph).name == DEFAULT_STRATEGY_NAME


def test_blank_name_falls_back_to_the_default():
    graph = _legacy_graph()
    graph["name"] = "   "

    assert PushStrategy.model_validate(graph).name == DEFAULT_STRATEGY_NAME


def test_graph_without_output_format_is_rejected():
    """No terminal block means prose output the signal parser silently drops."""
    graph = _legacy_graph()
    graph["stages"][0]["blocks"] = [{"id": "b1", "type": "prompt", "text": "Analyze NVDA."}]

    with pytest.raises(ValidationError, match="output_format"):
        PushStrategy.model_validate(graph)


def test_duplicate_block_ids_are_rejected():
    graph = _legacy_graph()
    graph["stages"][0]["blocks"] = [
        {"id": "b1", "type": "prompt", "text": "Analyze NVDA."},
        {"id": "b1", "type": "output_format"},
    ]

    with pytest.raises(ValidationError, match="unique"):
        PushStrategy.model_validate(graph)


def test_terminal_block_is_normalised_last_instead_of_rejected():
    graph = _legacy_graph()
    graph["stages"][0]["blocks"] = [
        {"id": "b1", "type": "output_format"},
        {"id": "b2", "type": "prompt", "text": "Analyze NVDA."},
    ]

    strategy = PushStrategy.model_validate(graph)

    assert [block.type for block in strategy.stages[0].blocks] == ["prompt", "output_format"]


def test_two_terminal_blocks_are_rejected():
    """Two output_format blocks is a graph the hydrator would render twice."""
    graph = _legacy_graph()
    graph["stages"][0]["blocks"] = [
        {"id": "b1", "type": "output_format"},
        {"id": "b2", "type": "output_format"},
    ]

    with pytest.raises(ValidationError, match="exactly one output_format"):
        PushStrategy.model_validate(graph)


def test_zero_block_graph_stays_valid_on_purpose():
    """Legacy placeholder rows must not be invalidated by a deploy."""
    graph = _legacy_graph()
    graph["stages"][0]["blocks"] = []

    assert PushStrategy.model_validate(graph).stages[0].blocks == []
