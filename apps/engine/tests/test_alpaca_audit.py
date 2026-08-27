from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from audit.alpaca_audit import AlpacaAuditReconciler, run_alpaca_audit


@pytest.fixture
def mock_supabase_data():
    now = datetime.now(UTC)
    date_6d_ago = (now - timedelta(days=6)).strftime("%Y-%m-%d")
    date_5d_ago = (now - timedelta(days=5)).strftime("%Y-%m-%d")
    date_today = now.strftime("%Y-%m-%d")

    portfolio = {
        "id": "port-123",
        "owner_id": "claude-haiku-4-5",
        "cash_balance": 5000.0,
        "total_equity": 10500.0,
    }
    positions = [
        {"portfolio_id": "port-123", "ticker": "AAPL", "quantity": 25, "average_cost_basis": 180.0},
        {"portfolio_id": "port-123", "ticker": "NVDA", "quantity": 10, "average_cost_basis": 100.0},
    ]
    trades = [
        {
            "id": "trade-1",
            "portfolio_id": "port-123",
            "ticker": "AAPL",
            "signal": "BUY",
            "quantity": 25,
            "price": 180.0,
            "total_cost": 4500.0,
            "executed_at": f"{date_6d_ago}T10:00:00Z",
            "alpaca_order_id": "alpaca-ord-1",
            "alpaca_status": "FILLED",
            "alpaca_filled_at": f"{date_6d_ago}T10:00:05Z",
        },
        {
            "id": "trade-2",
            "portfolio_id": "port-123",
            "ticker": "NVDA",
            "signal": "BUY",
            "quantity": 10,
            "price": 100.0,
            "total_cost": 1000.0,
            "executed_at": f"{date_5d_ago}T10:00:00Z",
            "alpaca_order_id": "alpaca-ord-2",
            "alpaca_status": "FILLED",
            "alpaca_filled_at": f"{date_5d_ago}T10:00:05Z",
        },
        {
            "id": "trade-3",
            "portfolio_id": "port-123",
            "ticker": "NVDA",
            "signal": "SELL",
            "quantity": 2,
            "price": 110.0,
            "total_cost": 220.0,
            "executed_at": f"{date_today}T10:00:00Z",
            "alpaca_order_id": "alpaca-ord-3",
            "alpaca_status": "SKIPPED_NO_POSITION",
            "alpaca_filled_at": None,
        },
    ]
    performance = [
        {"date": date_6d_ago, "total_equity": 10000.0, "cash_balance": 10000.0},
        {"date": date_5d_ago, "total_equity": 10050.0, "cash_balance": 5500.0},
        {"date": date_today, "total_equity": 10500.0, "cash_balance": 5000.0},
    ]
    return {
        "portfolio": portfolio,
        "positions": positions,
        "trades": trades,
        "performance": performance,
    }


def create_mock_alpaca_order(order_id, client_order_id, symbol, qty, filled_avg_price, status="filled"):
    order = MagicMock()
    order.id = order_id
    order.client_order_id = client_order_id
    order.symbol = symbol
    order.qty = str(qty)
    order.filled_qty = str(qty) if status == "filled" else "0"
    order.filled_avg_price = str(filled_avg_price) if filled_avg_price else None
    order.status = MagicMock()
    order.status.value = status
    order.filled_at = "2026-08-20T10:00:05Z" if status == "filled" else None
    return order


@pytest.mark.asyncio
async def test_alpaca_audit_reconciler_reconstructs_and_matches(mock_supabase_data):
    mock_sb = MagicMock()

    def mock_table(name):
        query_mock = MagicMock()
        if name == "portfolios":
            query_mock.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
                data=mock_supabase_data["portfolio"]
            )
        elif name == "portfolio_positions":
            query_mock.select.return_value.eq.return_value.execute.return_value = MagicMock(
                data=mock_supabase_data["positions"]
            )
        elif name == "trades":
            trades_chain = MagicMock()
            trades_chain.execute.return_value = MagicMock(data=mock_supabase_data["trades"])
            trades_chain.gte.return_value = trades_chain
            trades_chain.order.return_value = trades_chain
            query_mock.select.return_value.eq.return_value = trades_chain
        elif name == "portfolio_performance":
            perf_chain = MagicMock()
            perf_chain.execute.return_value = MagicMock(data=mock_supabase_data["performance"])
            perf_chain.order.return_value = perf_chain
            query_mock.select.return_value.eq.return_value = perf_chain
        return query_mock

    mock_sb.table.side_effect = mock_table

    alpaca_orders = [
        create_mock_alpaca_order(
            "alpaca-ord-1",
            "claude-haiku-4-5__AAPL__BUY__trade-1",
            "AAPL",
            25,
            180.10,  # 10 cents slippage per share
            "filled",
        ),
        create_mock_alpaca_order(
            "alpaca-ord-2",
            "claude-haiku-4-5__NVDA__BUY__trade-2",
            "NVDA",
            10,
            100.00,  # exact fill
            "filled",
        ),
    ]

    mock_alpaca_client = MagicMock()
    mock_alpaca_client.get_orders.return_value = alpaca_orders

    mock_mdm = MagicMock()
    mock_mdm.get_quote = AsyncMock(side_effect=lambda ticker: MagicMock(price=200.0 if ticker == "AAPL" else 150.0))

    reconciler = AlpacaAuditReconciler(
        supabase_client=mock_sb,
        alpaca_client=mock_alpaca_client,
        market_data_manager=mock_mdm,
    )

    result = await reconciler.audit_model_portfolio("claude-haiku-4-5", days=7)

    assert result["model_name"] == "claude-haiku-4-5"
    assert result["chart_performance"]["start_equity"] == 10000.0
    assert result["chart_performance"]["end_equity"] == 10500.0
    assert pytest.approx(result["chart_performance"]["pct_change"], 0.01) == 5.0

    # Trade matching assertions
    matched_trades = result["trades"]
    assert len(matched_trades) == 3
    assert matched_trades[0]["slippage_usd"] == pytest.approx(2.50, 0.01)
    assert matched_trades[0]["status"] == "FILLED"
    assert matched_trades[2]["status"] == "SKIPPED_NO_POSITION"

    # Anomalies should report the skipped trade
    assert len(result["anomalies"]) >= 1
    assert any("SKIPPED_NO_POSITION" in a["message"] for a in result["anomalies"])

    # Test report formatting
    report = reconciler.render_terminal_report(result)
    assert "ALPACA PORTFOLIO AUDIT REPORT: claude-haiku-4-5" in report
    assert "EXECUTIVE SUMMARY" in report
    assert "POSITIONS RECONCILIATION" in report
    assert "RECENT TRADES & EXECUTION SLIPPAGE" in report


@pytest.mark.asyncio
async def test_alpaca_audit_reconciler_missing_portfolio():
    mock_sb = MagicMock()
    mock_sb.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
        data=None
    )

    reconciler = AlpacaAuditReconciler(supabase_client=mock_sb)
    with pytest.raises(ValueError, match="not found in Supabase"):
        await reconciler.audit_model_portfolio("non-existent-model")


@pytest.mark.asyncio
async def test_alpaca_audit_reconciler_empty_trades():
    mock_sb = MagicMock()

    def mock_table(name):
        query_mock = MagicMock()
        if name == "portfolios":
            query_mock.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
                data={"id": "port-empty", "owner_id": "test-empty", "total_equity": 10000.0, "cash_balance": 10000.0}
            )
        elif name == "portfolio_positions":
            query_mock.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        elif name == "trades":
            trades_chain = MagicMock()
            trades_chain.execute.return_value = MagicMock(data=[])
            trades_chain.order.return_value = trades_chain
            query_mock.select.return_value.eq.return_value = trades_chain
        elif name == "portfolio_performance":
            perf_chain = MagicMock()
            perf_chain.execute.return_value = MagicMock(data=[])
            perf_chain.order.return_value = perf_chain
            query_mock.select.return_value.eq.return_value = perf_chain
        return query_mock

    mock_sb.table.side_effect = mock_table
    reconciler = AlpacaAuditReconciler(supabase_client=mock_sb)

    result = await reconciler.audit_model_portfolio("test-empty")
    assert result["total_trades"] == 0
    assert result["filled_trades"] == 0
    assert result["equity_delta"] == 0.0

    report = reconciler.render_terminal_report(result)
    assert "No active positions" in report
    assert "No recent trades found" in report


@pytest.mark.asyncio
async def test_run_alpaca_audit_cli_wrapper():
    with patch("audit.alpaca_audit.AlpacaAuditReconciler") as MockReconcilerClass:
        instance = MagicMock()
        instance.audit_model_portfolio = AsyncMock(
            return_value={
                "model_name": "MiniMax-M3",
                "portfolio_id": "p-1",
                "supabase_equity": 10000.0,
                "supabase_cash": 5000.0,
                "alpaca_reconstructed_equity": 9995.0,
                "alpaca_reconstructed_cash": 4995.0,
                "equity_delta": -5.0,
                "equity_delta_pct": -0.05,
                "total_trades": 2,
                "filled_trades": 2,
                "skipped_or_failed_trades": 0,
                "avg_slippage_usd": 2.50,
                "chart_performance": {
                    "start_equity": 9500.0,
                    "end_equity": 10000.0,
                    "pct_change": 5.26,
                    "days": 7,
                },
                "positions": [
                    {
                        "ticker": "AAPL",
                        "supabase_qty": 10,
                        "alpaca_qty": 10,
                        "delta_qty": 0,
                        "current_price": 200.0,
                        "supabase_val": 2000.0,
                        "alpaca_val": 2000.0,
                    }
                ],
                "trades": [],
                "anomalies": [],
            }
        )
        instance.render_terminal_report = MagicMock(return_value="AUDIT REPORT MOCK")
        MockReconcilerClass.return_value = instance

        res = await run_alpaca_audit(model_name="MiniMax-M3", days=7, json_output=False)
        assert res["model_name"] == "MiniMax-M3"
        instance.render_terminal_report.assert_called_once()
