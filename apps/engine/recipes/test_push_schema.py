"""Push v2 schema contract: one stage, no per-stage title, always a name."""

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
                "blocks": [{"id": "b1", "type": "prompt", "text": "Analyze NVDA."}],
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
