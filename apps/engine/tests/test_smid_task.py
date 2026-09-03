"""Unit tests for the SMID compounder scheduled task.

Pure unit tests with zero external network calls.
Mocks Supabase, FMP, and Polygon providers to verify:
1. Health check mode liquidates only deteriorating holdings and does not buy.
2. Rebalance mode retains winners, liquidates deteriorating holdings, and buys new candidates.
3. Dry run mode computes the execution plan without executing database orders.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tasks.smid_compounder_task import run_smid_compounder_task


@pytest.fixture
def mock_portfolio():
    """Mocks Portfolio instance."""
    portfolio = MagicMock()
    portfolio.id = "test-portfolio-id"
    portfolio.owner_id = "sys-smid-quality-compounder"
    portfolio.cash_balance = 10000.0
    portfolio.initialize = AsyncMock()
    portfolio.execute_trade = AsyncMock()
    portfolio.calculate_reg_t_metrics = MagicMock()
    portfolio.save_metrics = AsyncMock()

    # Create mock positions: DECK (winner, $25B cap) and ZOM (zombie, unprofitable)
    pos_deck = MagicMock()
    pos_deck.ticker = "DECK"
    pos_deck.quantity = 20
    pos_deck.average_cost_basis = 100.0

    pos_zom = MagicMock()
    pos_zom.ticker = "ZOM"
    pos_zom.quantity = 50
    pos_zom.average_cost_basis = 30.0

    portfolio.positions = {"DECK": pos_deck, "ZOM": pos_zom}
    return portfolio


@pytest.mark.asyncio
async def test_task_health_check_liquidates_zombie_and_retains_winner(mock_portfolio):
    """In health_check mode, ZOM is liquidated while DECK is retained. No new buys are made."""
    with (
        patch("tasks.smid_compounder_task.Portfolio", return_value=mock_portfolio),
        patch("tasks.smid_compounder_task.get_supabase_client"),
        patch("tasks.smid_compounder_task.fetch_current_price_and_market_cap") as mock_price_cap,
        patch("tasks.smid_compounder_task.fetch_holding_statements") as mock_stmts,
    ):
        # DECK: $25B cap, $150 price. ZOM: $500M cap, $10 price
        mock_price_cap.side_effect = lambda client, ticker, key: (
            (150.0, 25000000000.0) if ticker == "DECK" else (10.0, 500000000.0)
        )

        # Statements: DECK profitable, ZOM negative net income
        def get_mock_stmts(client, ticker, key):
            if ticker == "DECK":
                inc = [{"netIncome": 50000000.0, "operatingIncome": 60000000.0} for _ in range(4)]
                cf = [{"freeCashFlow": 40000000.0} for _ in range(4)]
                bs = [{"totalStockholdersEquity": 100000000.0, "totalDebt": 20000000.0, "cashAndCashEquivalents": 10000000.0}]
            else:
                inc = [{"netIncome": -30000000.0, "operatingIncome": -20000000.0} for _ in range(4)]
                cf = [{"freeCashFlow": -10000000.0} for _ in range(4)]
                bs = [{"totalStockholdersEquity": 50000000.0, "totalDebt": 80000000.0, "cashAndCashEquivalents": 5000000.0}]
            return inc, cf, bs

        mock_stmts.side_effect = get_mock_stmts

        result = await run_smid_compounder_task(mode="health_check", target_holdings=25, dry_run=False)

        assert result["mode"] == "health_check"
        assert len(result["sales"]) == 1
        assert result["sales"][0]["ticker"] == "ZOM"
        assert len(result["retained"]) == 1
        assert result["retained"][0]["ticker"] == "DECK"
        assert len(result["buys"]) == 0  # No buys in health check mode

        # Verify execute_trade called only for ZOM sell
        mock_portfolio.execute_trade.assert_called_once()
        call_kwargs = mock_portfolio.execute_trade.call_args.kwargs
        assert call_kwargs["ticker"] == "ZOM"
        assert call_kwargs["signal"] == "SELL"
        assert call_kwargs["quantity"] == 50


@pytest.mark.asyncio
async def test_task_rebalance_mode_deploys_buys(mock_portfolio):
    """In rebalance mode, ZOM is liquidated, DECK is retained, and new candidates are bought."""
    with (
        patch("tasks.smid_compounder_task.Portfolio", return_value=mock_portfolio),
        patch("tasks.smid_compounder_task.get_supabase_client"),
        patch("tasks.smid_compounder_task.fetch_current_price_and_market_cap") as mock_price_cap,
        patch("tasks.smid_compounder_task.fetch_holding_statements") as mock_stmts,
        patch("tasks.smid_compounder_task.fetch_screened_candidates") as mock_screen,
    ):
        mock_price_cap.side_effect = lambda client, ticker, key: (
            (150.0, 25000000000.0) if ticker == "DECK" else (10.0, 500000000.0)
        )

        def get_mock_stmts(client, ticker, key):
            if ticker == "DECK":
                inc = [{"netIncome": 50000000.0, "operatingIncome": 60000000.0} for _ in range(4)]
                cf = [{"freeCashFlow": 40000000.0} for _ in range(4)]
                bs = [{"totalStockholdersEquity": 100000000.0, "totalDebt": 20000000.0, "cashAndCashEquivalents": 10000000.0}]
            else:
                inc = [{"netIncome": -30000000.0, "operatingIncome": -20000000.0} for _ in range(4)]
                cf = [{"freeCashFlow": -10000000.0} for _ in range(4)]
                bs = [{"totalStockholdersEquity": 50000000.0, "totalDebt": 80000000.0, "cashAndCashEquivalents": 5000000.0}]
            return inc, cf, bs

        mock_stmts.side_effect = get_mock_stmts

        # Mock 2 quality candidates returned from screening
        mock_screen.return_value = [
            {
                "symbol": "SOLS",
                "price": 60.0,
                "market_cap": 9000000000.0,
                "quality": {"is_quality_pass": True, "roic": 0.15, "ttm_fcf": 150000000.0},
                "momentum_12m": 25.0,
            },
            {
                "symbol": "AYI",
                "price": 300.0,
                "market_cap": 9500000000.0,
                "quality": {"is_quality_pass": True, "roic": 0.16, "ttm_fcf": 400000000.0},
                "momentum_12m": 10.0,
            },
        ]

        result = await run_smid_compounder_task(mode="rebalance", target_holdings=3, dry_run=False)

        assert result["mode"] == "rebalance"
        assert len(result["sales"]) == 1
        assert result["sales"][0]["ticker"] == "ZOM"
        assert len(result["retained"]) == 1
        assert result["retained"][0]["ticker"] == "DECK"
        # 2 open slots (target 3 minus 1 retained) -> 2 buys
        assert len(result["buys"]) == 2
        buy_tickers = [b["ticker"] for b in result["buys"]]
        assert "SOLS" in buy_tickers
        assert "AYI" in buy_tickers

        # Verify calls: 1 sell + 2 buys = 3 execute_trade calls
        assert mock_portfolio.execute_trade.call_count == 3


@pytest.mark.asyncio
async def test_task_dry_run_executes_no_orders(mock_portfolio):
    """In dry_run mode, orders are computed but execute_trade is never called."""
    with (
        patch("tasks.smid_compounder_task.Portfolio", return_value=mock_portfolio),
        patch("tasks.smid_compounder_task.get_supabase_client"),
        patch("tasks.smid_compounder_task.fetch_current_price_and_market_cap") as mock_price_cap,
        patch("tasks.smid_compounder_task.fetch_holding_statements") as mock_stmts,
        patch("tasks.smid_compounder_task.fetch_screened_candidates", return_value=[]),
    ):
        mock_price_cap.return_value = (100.0, 5000000000.0)
        mock_stmts.return_value = (
            [{"netIncome": 10000000.0} for _ in range(4)],
            [{"freeCashFlow": 10000000.0} for _ in range(4)],
            [{"totalStockholdersEquity": 50000000.0}],
        )

        result = await run_smid_compounder_task(mode="health_check", dry_run=True)

        assert result["dry_run"] is True
        mock_portfolio.execute_trade.assert_not_called()
