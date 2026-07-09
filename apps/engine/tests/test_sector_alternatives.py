from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.llm.tools import execute_sector_alternatives_tool


@pytest.mark.asyncio
async def test_execute_sector_alternatives_tool_hybrid():
    """Test that execute_sector_alternatives_tool retrieves candidates from FMP, correlations, and vector search."""
    mock_profile = [{"sector": "Technology", "industry": "Consumer Electronics", "companyName": "Apple Inc."}]
    mock_screen = [
        {"symbol": "MSFT", "companyName": "Microsoft Corp", "price": 420.0, "marketCap": 3.1e12},
        {"symbol": "HPQ", "companyName": "HP Inc", "price": 35.0, "marketCap": 3.4e10},
    ]

    # Mock correlation database responses
    mock_runs = [{"id": "run-123", "run_date": "2026-07-05"}]
    mock_corr_data = [
        {"ticker_a": "AAPL", "ticker_b": "GOOGL", "pearson_corr": 0.75, "returns_a_90d": 12.0, "returns_b_90d": 10.0},
        {"ticker_a": "AAPL", "ticker_b": "MSFT", "pearson_corr": 0.68, "returns_a_90d": 12.0, "returns_b_90d": 8.0},
        {
            "ticker_a": "AMZN",
            "ticker_b": "AAPL",
            "pearson_corr": 0.35,
            "returns_a_90d": 5.0,
            "returns_b_90d": 12.0,
        },  # Below 0.40 threshold
    ]

    # Mock vector search (match_decisions)
    mock_decisions = [
        {"ticker": "META"},
        {"ticker": "NFLX"},
    ]

    with (
        patch("core.llm.tools.MarketDataManager") as mock_mgr_class,
        patch("core.llm.tools.get_supabase_client") as mock_sb_client,
        patch("core.llm.tools.get_embedding") as mock_emb,
    ):
        # Mock MarketDataManager
        mock_mgr = mock_mgr_class.return_value
        mock_mgr.get_company_profile = AsyncMock(return_value=mock_profile)
        mock_mgr.screen_stocks = AsyncMock(return_value=mock_screen)
        mock_mgr.get_history = AsyncMock(return_value=[])

        # Mock Supabase
        sb_instance = mock_sb_client.return_value

        mock_table = MagicMock()
        mock_select = MagicMock()
        mock_order = MagicMock()
        mock_limit = MagicMock()
        MagicMock()

        sb_instance.table.return_value = mock_table
        mock_table.select.return_value = mock_select
        mock_select.order.return_value = mock_order
        mock_order.limit.return_value = mock_limit

        # Match different table routes
        def table_side_effect(table_name):
            t = MagicMock()
            if table_name == "correlation_runs":
                t.select.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
                    data=mock_runs
                )
            elif table_name == "correlation_data":
                # Make eq chainable: returning a mock that has eq returning itself, and execute returning data
                eq_mock = MagicMock()
                eq_mock.eq.return_value = eq_mock
                eq_mock.execute.return_value = MagicMock(data=mock_corr_data)
                t.select.return_value.eq.return_value = eq_mock
            return t

        sb_instance.table.side_effect = table_side_effect

        # Mock RPC match_decisions
        mock_rpc = MagicMock()
        sb_instance.rpc.return_value = mock_rpc
        mock_rpc.execute.return_value = MagicMock(data=mock_decisions)

        mock_emb.return_value = [0.1] * 1536

        result = await execute_sector_alternatives_tool("AAPL")

        # Verify calls
        mock_mgr.get_company_profile.assert_called_once_with("AAPL")
        mock_mgr.screen_stocks.assert_called_once_with(sector="Technology", industry="Consumer Electronics", limit=5)

        # Check that output contains sectors, correlations, and decisions
        assert "Industry Competitors" in result
        assert "MSFT" in result
        assert "HPQ" in result
        assert "Highly Correlated Assets" in result
        assert "GOOGL" in result
        assert "Historical Related Plays" in result
        assert "META" in result
        assert "NFLX" in result
        assert "AMZN" not in result  # should be excluded as correlation < 0.40
