import pytest
from unittest.mock import AsyncMock, MagicMock, patch


VALID_5_WHYS_RESULT = """
## 5 Whys Analysis

1. **Why** is this theme market-moving? Global uranium supply shortage is creating supply-demand imbalance.

2. **Why** will these specific assets benefit? These assets control uranium mining capacity needed for SMR fuel.

3. **Why** are these not already priced in? Market underestimates the duration of supply constraints.

4. **Why** is this the most efficient way to profit? Direct uranium miners provide leveraged exposure to spot price.

5. **Why** is your recommendation the best beneficiary of this theme? These companies have proven reserves and operational capacity.

## Recommended Assets

| Ticker | Company Name | Relevance Score | Mechanism of Profit |
|--------|--------------|-----------------|---------------------|
| $UUUU | Energy Fuels | 90 | Uranium mining |
| $CCJ | Cameco | 95 | Uranium production |
"""


@pytest.mark.asyncio
async def test_discovery_quality_flow():
    """Verify that the DiscoveryService correctly delegates to the DiscoveryAgent."""

    mock_agent_response = (
        "Stock Screening Results:\n"
        "- $UUUU (Energy Fuels): Price: $6.50, Market Cap: $1.10B, Sector: Energy\n"
        "- $CCJ (Cameco): Price: $48.20, Market Cap: $20.00B, Sector: Energy\n"
        "- $DNN (Denison Mines): Price: $2.30, Market Cap: $900M, Sector: Energy\n"
    )

    with patch("analysis.discovery_service.DiscoveryAgent") as MockAgent:
        mock_instance = MagicMock()
        mock_instance.discover_assets = AsyncMock(return_value=mock_agent_response)
        mock_instance.close = AsyncMock()
        MockAgent.return_value = mock_instance

        from analysis.discovery_service import DiscoveryService
        service = DiscoveryService()

        event = "Global Uranium supply shortage and surge in SMR demand"
        results = await service.discover_assets(event, event_summary="Uranium squeeze")

    assert len(results) > 0
    assert results[0]["ticker"] == "AGENT_DISCOVERY"
    assert "UUUU" in results[0]["reason"]
    assert "CCJ" in results[0]["reason"]

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
async def test_discovery_service_handles_retry_with_5_whys():
    """Verify that the service handles DiscoveryAgent retry behavior and returns valid 5 Whys results."""

    with patch("analysis.discovery_service.DiscoveryAgent") as MockAgent:
        mock_instance = MagicMock()
        mock_instance.discover_assets = AsyncMock(return_value=VALID_5_WHYS_RESULT)
        mock_instance.close = AsyncMock()
        MockAgent.return_value = mock_instance

        from analysis.discovery_service import DiscoveryService
        service = DiscoveryService()

        event = "Global Uranium supply shortage"
        results = await service.discover_assets(event)

    assert len(results) > 0
    assert results[0]["ticker"] == "AGENT_DISCOVERY"
    assert "UUUU" in results[0]["reason"]
    assert "Cameco" in results[0]["reason"]
    assert "Why" in results[0]["reason"] or "5 Whys" in results[0]["reason"]

    mock_instance.discover_assets.assert_called_once()


@pytest.mark.asyncio
async def test_discovery_service_graceful_fallback():
    """Verify that the service handles incomplete 5 Whys results gracefully."""

    incomplete_response = "Some stocks were found but analysis is incomplete."

    with patch("analysis.discovery_service.DiscoveryAgent") as MockAgent:
        mock_instance = MagicMock()
        mock_instance.discover_assets = AsyncMock(return_value=incomplete_response)
        mock_instance.close = AsyncMock()
        MockAgent.return_value = mock_instance

        from analysis.discovery_service import DiscoveryService
        service = DiscoveryService()

        results = await service.discover_assets("Some theme")

    assert len(results) > 0
    assert results[0]["ticker"] == "AGENT_DISCOVERY"
