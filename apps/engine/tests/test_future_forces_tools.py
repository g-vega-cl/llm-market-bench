"""Unit tests for get_future_forces and research_future_force tools."""

from unittest.mock import AsyncMock, patch

import pytest

from core.llm.tools import (
    CANONICAL_TOOLS_REGISTRY,
    execute_get_future_forces_tool,
    execute_research_future_force_tool,
    execute_tool,
)


def test_tools_registered_in_canonical_registry():
    """Verify that get_future_forces and research_future_force are present in CANONICAL_TOOLS_REGISTRY."""
    assert "get_future_forces" in CANONICAL_TOOLS_REGISTRY
    assert "research_future_force" in CANONICAL_TOOLS_REGISTRY

    gff = CANONICAL_TOOLS_REGISTRY["get_future_forces"]
    assert gff["function"]["name"] == "get_future_forces"

    rff = CANONICAL_TOOLS_REGISTRY["research_future_force"]
    assert rff["function"]["name"] == "research_future_force"


@pytest.mark.asyncio
async def test_execute_get_future_forces_tool_fallback():
    """Verify execute_get_future_forces_tool formats default forces when database is empty."""
    res = await execute_get_future_forces_tool(limit=3)
    assert "ACTIVE MULTI-HORIZON FORCES & CATALYSTS" in res
    assert "Expression Tickers:" in res
    assert "Causal Thesis:" in res
    assert "Milestone Catalyst:" in res
    assert "Invalidation Criteria:" in res


@pytest.mark.asyncio
async def test_execute_get_future_forces_tool_filtered():
    """Verify archetype filtering in execute_get_future_forces_tool."""
    res = await execute_get_future_forces_tool(archetype="mega_event", limit=5)
    assert "MEGA_EVENT" in res
    assert "FIFA World Cup" in res


@pytest.mark.asyncio
async def test_execute_research_future_force_tool():
    """Verify execute_research_future_force_tool returns structured audit."""
    from analytics.future_forces import ForceEvaluationResult

    mock_result = ForceEvaluationResult(
        passes_rubric=True,
        conviction_score=5,
        priced_in_assessment="Priced for failure; asymmetric 35% upside.",
        critique="Ensure supplier contracts are locked.",
        recommended_horizon_months=6,
        falsification_clarity_score=5,
    )

    with patch("analytics.future_forces.evaluate_future_force", new_callable=AsyncMock, return_value=mock_result):
        res = await execute_research_future_force_tool(
            force_title="AI Threat Surface",
            archetype="secular_tollroad",
            thesis="Autonomous agents expand threat surface 10x.",
            catalyst_event="Q4 ARR prints",
            invalidation_triggers="Budget growth stalls below 5%.",
            transmission_mechanism="25% FCF margin expansion.",
            tickers=["CRWD", "PANW"],
            horizon_months=6,
        )

    assert "ADVERSARIAL FORCE AUDIT: AI Threat Surface (PASSED RUBRIC)" in res
    assert "Audited Conviction: 5/5" in res
    assert "Recommended Horizon: 6 months" in res
    assert "Priced for failure" in res


@pytest.mark.asyncio
async def test_execute_tool_dispatch_future_forces():
    """Verify dispatch through execute_tool helper."""
    with patch(
        "core.llm.tools.execute_get_future_forces_tool",
        new_callable=AsyncMock,
        return_value="DISPATCHED_GET_FORCES",
    ) as mock_get:
        out = await execute_tool("get_future_forces", {"archetype": "sleeping_giant"})
        assert out == "DISPATCHED_GET_FORCES"
        mock_get.assert_awaited_once_with(archetype="sleeping_giant", max_horizon_months=24, limit=5)

    with patch(
        "core.llm.tools.execute_research_future_force_tool",
        new_callable=AsyncMock,
        return_value="DISPATCHED_RESEARCH_FORCE",
    ) as mock_res:
        out = await execute_tool(
            "research_future_force",
            {
                "force_title": "Test",
                "archetype": "sleeping_giant",
                "thesis": "Thesis",
                "catalyst_event": "Event",
                "invalidation_triggers": "Triggers",
                "transmission_mechanism": "Mechanism",
            },
        )
        assert out == "DISPATCHED_RESEARCH_FORCE"
        mock_res.assert_awaited_once()
