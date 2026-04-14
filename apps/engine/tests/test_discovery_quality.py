import pytest
from unittest.mock import AsyncMock, MagicMock, patch


MOCK_ASSETS_RESULT = [
    {"ticker": "UUUU", "name": "Energy Fuels", "reason": "Uranium mining with exposure to SMR fuel demand"},
    {"ticker": "CCJ", "name": "Cameco", "reason": "Largest western uranium producer with long-term contracts"},
    {"ticker": "DNN", "name": "Denison Mines", "reason": "Exploration and development of uranium assets in the Athabasca Basin"}
]


@pytest.mark.asyncio
async def test_discovery_quality_flow():
    """Verify that the DiscoveryService correctly delegates to the DiscoveryAgent and returns real tickers."""

    with patch("analysis.discovery_service.DiscoveryAgent") as MockAgent:
        mock_instance = MagicMock()
        mock_instance.discover_assets = AsyncMock(return_value=MOCK_ASSETS_RESULT)
        mock_instance.close = AsyncMock()
        MockAgent.return_value = mock_instance

        from analysis.discovery_service import DiscoveryService
        service = DiscoveryService()

        event = "Global Uranium supply shortage and surge in SMR demand"
        results = await service.discover_assets(event, event_summary="Uranium squeeze")

        assert len(results) == 3
        assert results[0]["ticker"] == "UUUU"
        assert results[0]["name"] == "Energy Fuels"
        assert "uranium" in results[0]["reason"].lower()

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


@pytest.mark.asyncio
async def test_discovery_service_returns_real_tickers():
    """Verify that the service returns real tickers from the agent, not AGENT_DISCOVERY wrapper."""

    mock_assets = [
        {"ticker": "AAPL", "name": "Apple", "reason": "AI integration in devices"},
        {"ticker": "MSFT", "name": "Microsoft", "reason": "Azure AI services"}
    ]

    with patch("analysis.discovery_service.DiscoveryAgent") as MockAgent:
        mock_instance = MagicMock()
        mock_instance.discover_assets = AsyncMock(return_value=mock_assets)
        mock_instance.close = AsyncMock()
        MockAgent.return_value = mock_instance

        from analysis.discovery_service import DiscoveryService
        service = DiscoveryService()

        results = await service.discover_assets("Consumer AI adoption")

        assert len(results) == 2
        assert results[0]["ticker"] == "AAPL"
        assert results[1]["ticker"] == "MSFT"
        assert all(r["ticker"] != "AGENT_DISCOVERY" for r in results)


@pytest.mark.asyncio
async def test_discovery_service_passes_context():
    """Verify that the service passes event_summary as context to the agent."""

    with patch("analysis.discovery_service.DiscoveryAgent") as MockAgent:
        mock_instance = MagicMock()
        mock_instance.discover_assets = AsyncMock(return_value=[])
        mock_instance.close = AsyncMock()
        MockAgent.return_value = mock_instance

        from analysis.discovery_service import DiscoveryService
        service = DiscoveryService()

        event = "Test event theme"
        context = "Additional context from summary"
        await service.discover_assets(event, event_summary=context)

        mock_instance.discover_assets.assert_called_once_with(
            theme=event,
            context=context
        )
