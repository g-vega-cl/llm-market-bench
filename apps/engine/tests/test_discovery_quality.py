import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_discovery_quality_flow():
    """Verify that the DiscoveryService correctly delegates to the DiscoveryAgent."""

    mock_agent_response = (
        "Stock Screening Results:\n"
        "- $UUUU (Energy Fuels): Price: $6.50, Market Cap: $1.10B, Sector: Energy\n"
        "- $CCJ (Cameco): Price: $48.20, Market Cap: $20.00B, Sector: Energy\n"
        "- $DNN (Denison Mines): Price: $2.30, Market Cap: $900M, Sector: Energy\n"
    )

    # Patch the DiscoveryAgent inside the service so no real LLM clients are created
    with patch("analysis.discovery_service.DiscoveryAgent") as MockAgent:
        mock_instance = MagicMock()
        mock_instance.discover_assets = AsyncMock(return_value=mock_agent_response)
        mock_instance.close = AsyncMock()
        MockAgent.return_value = mock_instance

        from analysis.discovery_service import DiscoveryService
        service = DiscoveryService()

        event = "Global Uranium supply shortage and surge in SMR demand"
        results = await service.discover_assets(event, event_summary="Uranium squeeze")

    # Assertions: the service should return the agent's findings wrapped in a dict
    assert len(results) > 0
    assert results[0]["ticker"] == "AGENT_DISCOVERY"
    assert "UUUU" in results[0]["reason"]
    assert "CCJ" in results[0]["reason"]

    # Verify the agent was invoked with the correct theme
    mock_instance.discover_assets.assert_called_once_with(
        theme=event,
        context="Uranium squeeze"
    )


@pytest.mark.asyncio
async def test_discovery_empty_result():
    """Verify that a failed agent call returns an empty list gracefully."""

    with patch("analysis.discovery_service.DiscoveryAgent") as MockAgent:
        mock_instance = MagicMock()
        mock_instance.discover_assets = AsyncMock(side_effect=Exception("LLM timeout"))
        mock_instance.close = AsyncMock()
        MockAgent.return_value = mock_instance

        from analysis.discovery_service import DiscoveryService
        service = DiscoveryService()

        results = await service.discover_assets("Some theme")

    assert results == []
