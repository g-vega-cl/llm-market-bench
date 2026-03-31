import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from analysis.discovery_service import DiscoveryService
from core.models import DiscoveryThemes, DiscoveryRankingResponse, RankedAsset

@pytest.mark.asyncio
async def test_discovery_quality_flow():
    """Verify that discovery correctly identifies niche plays and re-ranks them."""
    service = DiscoveryService()
    
    # 1. Mock Gemini Themes Response
    mock_themes = DiscoveryThemes(
        sectors=["Energy"],
        industries=["Uranium", "Oil & Gas E&P"],
        keywords=["Uranium mining", "SMR nuclear"],
        market_cap_min=100000000,
        reasoning="Testing uranium squeeze theme"
    )
    
    service.gemini_client.chat.completions.create = MagicMock(return_value=mock_themes)
    
    # 2. Mock FMP Provider
    service.fmp.screen_stocks = AsyncMock(side_effect=[
        # Energy sector screen
        [{"symbol": "XOM", "companyName": "Exxon", "marketCap": 400000000000}],
        # Uranium industry screen
        [{"symbol": "CCJ", "companyName": "Cameco", "marketCap": 20000000000},
         {"symbol": "UUUU", "companyName": "Energy Fuels", "marketCap": 1100000000}],
        # Oil & Gas screen
        [{"symbol": "CVX", "companyName": "Chevron", "marketCap": 300000000000}]
    ])
    service.fmp.search_tickers = AsyncMock(return_value=[
        {"symbol": "DNN", "name": "Denison Mines"}
    ])
    
    # 3. Mock Deepseek Ranking Response
    mock_ranking = DiscoveryRankingResponse(
        ranked_assets=[
            RankedAsset(ticker="UUUU", name="Energy Fuels", relevance_score=95, reason="Direct US-based uranium play"),
            RankedAsset(ticker="DNN", name="Denison Mines", relevance_score=90, reason="High leverage to uranium price"),
            RankedAsset(ticker="CCJ", name="Cameco", relevance_score=85, reason="Largest pure-play uranium producer"),
            RankedAsset(ticker="XOM", name="Exxon", relevance_score=10, reason="Only tangentially related via general energy")
        ]
    )
    service.deepseek_client.chat.completions.create = MagicMock(return_value=mock_ranking)
    
    # Execution
    event = "Global Uranium supply shortage and surge in SMR demand"
    results = await service.discover_assets(event)
    
    # Assertions
    assert len(results) > 0
    # UUUU should be in the results (high score)
    tickers = [r["ticker"] for r in results]
    assert "UUUU" in tickers
    assert "DNN" in tickers
    # XOM should be filtered out by relevance score (< 40)
    assert "XOM" not in tickers
    
    # Verify the formatting
    assert "[Score 95]" in results[0]["reason"]
    
    # Verify mock calls
    assert service.fmp.screen_stocks.called
    assert service.deepseek_client.chat.completions.create.called
