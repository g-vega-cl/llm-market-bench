"""Hermetic tests for portfolio health auditor and auto-healer.

Verifies:
1. Detection of missing daily SPY trades when daily predictions exist.
2. Auto-healing of missing trades with alpaca_status="BACKFILLED".
3. Detection of unliquidated weekly sector positions.
4. Clean status when all portfolios traded as expected.
5. Markdown table report generation for CI summary.
"""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest


@pytest.fixture
def mock_supabase():
    """Mock Supabase client with chainable query builder methods."""
    client = MagicMock()
    table_mock = MagicMock()
    client.table.return_value = table_mock

    table_mock.select.return_value = table_mock
    table_mock.insert.return_value = table_mock
    table_mock.upsert.return_value = table_mock
    table_mock.update.return_value = table_mock
    table_mock.delete.return_value = table_mock
    table_mock.eq.return_value = table_mock
    table_mock.gte.return_value = table_mock
    table_mock.lte.return_value = table_mock
    table_mock.lt.return_value = table_mock
    table_mock.like.return_value = table_mock
    table_mock.order.return_value = table_mock
    table_mock.limit.return_value = table_mock
    table_mock.execute.return_value = MagicMock(data=[])

    return client


@pytest.mark.asyncio
async def test_audit_clean_portfolio(mock_supabase):
    """When all system portfolios have traded as expected, status is clean."""
    from audit.portfolio_auditor import audit_system_portfolios

    # Mock predictions for target date
    target_date = "2026-09-29"
    pred = {
        "id": "pred-1",
        "model_name": "MiniMax-M3",
        "predicted_direction": "UP",
        "expected_return_pct": 0.15,
        "target_date": target_date,
        "open_price": 766.83,
        "high_price": 766.98,
        "low_price": 762.37,
        "close_price": 764.08,
    }

    # Setup table return values based on table name
    def table_router(table_name):
        mock_t = MagicMock()
        mock_t.select.return_value = mock_t
        mock_t.eq.return_value = mock_t
        mock_t.gte.return_value = mock_t
        mock_t.lte.return_value = mock_t
        mock_t.like.return_value = mock_t

        if table_name == "daily_predictions":
            mock_t.execute.return_value = MagicMock(data=[pred])
        elif table_name == "portfolios":
            mock_t.execute.return_value = MagicMock(
                data=[
                    {
                        "id": "p-1",
                        "owner_id": "sys-daily-spy-close-MiniMax-M3",
                        "cash_balance": 10000.0,
                        "total_equity": 10000.0,
                    },
                    {
                        "id": "p-2",
                        "owner_id": "sys-daily-spy-MiniMax-M3",
                        "cash_balance": 10000.0,
                        "total_equity": 10000.0,
                    },
                ]
            )
        elif table_name == "trades":
            # Both portfolios have 2 trades on target_date
            mock_t.execute.return_value = MagicMock(
                data=[
                    {
                        "id": "t-1",
                        "signal": "BUY",
                        "quantity": 13,
                        "price": 766.98,
                        "executed_at": f"{target_date}T13:30:00Z",
                    },
                    {
                        "id": "t-2",
                        "signal": "SELL",
                        "quantity": 13,
                        "price": 763.92,
                        "executed_at": f"{target_date}T20:00:00Z",
                    },
                ]
            )
        elif table_name == "portfolio_positions":
            mock_t.execute.return_value = MagicMock(data=[])
        else:
            mock_t.execute.return_value = MagicMock(data=[])
        return mock_t

    mock_supabase.table.side_effect = table_router

    report = await audit_system_portfolios(
        target_date=target_date,
        lookback_days=1,
        auto_heal=False,
        supabase_client=mock_supabase,
    )

    assert report["status"] == "clean"
    assert len(report["anomalies"]) == 0
    assert len(report["healed"]) == 0


@pytest.mark.asyncio
async def test_audit_detects_missing_daily_spy_trade(mock_supabase):
    """When daily prediction exists but portfolio has 0 trades, anomaly is detected."""
    from audit.portfolio_auditor import audit_system_portfolios

    target_date = "2026-09-29"
    pred = {
        "id": "pred-1",
        "model_name": "MiniMax-M3",
        "predicted_direction": "UP",
        "expected_return_pct": 0.15,
        "target_date": target_date,
        "open_price": 766.83,
        "high_price": 766.98,
        "low_price": 762.37,
        "close_price": 764.08,
    }

    def table_router(table_name):
        mock_t = MagicMock()
        mock_t.select.return_value = mock_t
        mock_t.eq.return_value = mock_t
        mock_t.gte.return_value = mock_t
        mock_t.lte.return_value = mock_t
        mock_t.like.return_value = mock_t

        if table_name == "daily_predictions":
            mock_t.execute.return_value = MagicMock(data=[pred])
        elif table_name == "portfolios":
            mock_t.execute.return_value = MagicMock(
                data=[
                    {
                        "id": "p-1",
                        "owner_id": "sys-daily-spy-close-MiniMax-M3",
                        "cash_balance": 10000.0,
                        "total_equity": 10000.0,
                    },
                ]
            )
        elif table_name == "trades":
            # 0 trades found!
            mock_t.execute.return_value = MagicMock(data=[])
        elif table_name == "portfolio_positions":
            mock_t.execute.return_value = MagicMock(data=[])
        else:
            mock_t.execute.return_value = MagicMock(data=[])
        return mock_t

    mock_supabase.table.side_effect = table_router

    report = await audit_system_portfolios(
        target_date=target_date,
        lookback_days=1,
        auto_heal=False,
        supabase_client=mock_supabase,
    )

    assert report["status"] == "anomalies_detected"
    assert len(report["anomalies"]) >= 1
    anomaly = report["anomalies"][0]
    assert anomaly["type"] == "MISSING_DAILY_SPY_TRADE"
    assert anomaly["owner_id"] == "sys-daily-spy-close-MiniMax-M3"
    assert anomaly["date"] == target_date


@pytest.mark.asyncio
async def test_audit_auto_heals_missing_daily_spy_trade(mock_supabase):
    """When auto_heal=True, reconstructs missing trades with alpaca_status='BACKFILLED'."""
    from audit.portfolio_auditor import audit_system_portfolios

    target_date = "2026-09-29"
    pred = {
        "id": "pred-1",
        "model_name": "MiniMax-M3",
        "predicted_direction": "UP",
        "expected_return_pct": 0.15,
        "target_date": target_date,
        "open_price": 766.83,
        "high_price": 766.98,
        "low_price": 762.37,
        "close_price": 764.08,
    }

    trades_db = []

    def table_router(table_name):
        mock_t = MagicMock()
        mock_t.select.return_value = mock_t
        mock_t.insert.side_effect = lambda payload: trades_db.append(payload) or mock_t
        mock_t.upsert.return_value = mock_t
        mock_t.update.return_value = mock_t
        mock_t.delete.return_value = mock_t
        mock_t.eq.return_value = mock_t
        mock_t.gte.return_value = mock_t
        mock_t.lte.return_value = mock_t
        mock_t.lt.return_value = mock_t
        mock_t.like.return_value = mock_t
        mock_t.order.return_value = mock_t
        mock_t.limit.return_value = mock_t

        if table_name == "daily_predictions":
            mock_t.execute.return_value = MagicMock(data=[pred])
        elif table_name == "portfolios":
            mock_t.execute.return_value = MagicMock(
                data=[
                    {
                        "id": str(uuid4()),
                        "owner_id": "sys-daily-spy-close-MiniMax-M3",
                        "cash_balance": 10000.0,
                        "total_equity": 10000.0,
                    },
                ]
            )
        elif table_name == "trades":
            mock_t.execute.return_value = MagicMock(data=trades_db)
        elif table_name == "portfolio_positions":
            mock_t.execute.return_value = MagicMock(data=[])
        else:
            mock_t.execute.return_value = MagicMock(data=[])
        return mock_t

    mock_supabase.table.side_effect = table_router

    with patch("execution.daily_trading.get_supabase_client", return_value=mock_supabase):
        report = await audit_system_portfolios(
            target_date=target_date,
            lookback_days=1,
            auto_heal=True,
            supabase_client=mock_supabase,
        )

    assert report["status"] == "healed"
    assert len(report["healed"]) >= 1
    healed = report["healed"][0]
    assert healed["owner_id"] == "sys-daily-spy-close-MiniMax-M3"
    assert healed["date"] == target_date
    assert "BACKFILLED" in str(report["summary_table_markdown"])


@pytest.mark.asyncio
async def test_audit_detects_unliquidated_weekly_sector_position(mock_supabase):
    """Detects when a weekly sector portfolio holds open positions past Friday close."""
    from audit.portfolio_auditor import audit_system_portfolios

    def table_router(table_name):
        mock_t = MagicMock()
        mock_t.select.return_value = mock_t
        mock_t.eq.return_value = mock_t
        mock_t.gte.return_value = mock_t
        mock_t.lte.return_value = mock_t
        mock_t.like.return_value = mock_t

        if table_name == "daily_predictions":
            mock_t.execute.return_value = MagicMock(data=[])
        elif table_name == "portfolios":
            mock_t.execute.return_value = MagicMock(
                data=[
                    {
                        "id": "p-sec-1",
                        "owner_id": "sys-sector-ls-consensus",
                        "cash_balance": 5000.0,
                        "total_equity": 10000.0,
                    },
                ]
            )
        elif table_name == "trades":
            mock_t.execute.return_value = MagicMock(data=[])
        elif table_name == "portfolio_positions":
            # Unliquidated weekly position holding XLE
            mock_t.execute.return_value = MagicMock(
                data=[{"portfolio_id": "p-sec-1", "ticker": "XLE", "quantity": 50, "average_cost_basis": 90.0}]
            )
        else:
            mock_t.execute.return_value = MagicMock(data=[])
        return mock_t

    mock_supabase.table.side_effect = table_router

    # Auditing a Saturday or Monday before rebalance
    report = await audit_system_portfolios(
        target_date="2026-09-26",  # Saturday
        lookback_days=1,
        auto_heal=False,
        supabase_client=mock_supabase,
    )

    assert report["status"] == "anomalies_detected"
    assert any(a["type"] == "UNLIQUIDATED_WEEKLY_SECTOR_POSITION" for a in report["anomalies"])


@pytest.mark.asyncio
async def test_audit_detects_invalid_entry_price_daily_spy(mock_supabase):
    """Detects when SPY daily entry price took previous day close instead of session open."""
    from audit.portfolio_auditor import audit_system_portfolios

    target_date = "2026-10-02"
    pred = {
        "id": "pred-10-02",
        "model_name": "deepseek-v4-flash",
        "predicted_direction": "UP",
        "expected_return_pct": 0.20,
        "target_date": target_date,
        "open_price": 770.58,
        "high_price": 772.65,
        "low_price": 767.15,
        "close_price": 769.50,
    }

    def table_router(table_name):
        mock_t = MagicMock()
        mock_t.select.return_value = mock_t
        mock_t.eq.return_value = mock_t
        mock_t.gte.return_value = mock_t
        mock_t.lte.return_value = mock_t
        mock_t.like.return_value = mock_t

        if table_name == "daily_predictions":
            mock_t.execute.return_value = MagicMock(data=[pred])
        elif table_name == "portfolios":
            mock_t.execute.return_value = MagicMock(
                data=[
                    {
                        "id": "p-1",
                        "owner_id": "sys-daily-spy-close-deepseek-v4-flash",
                        "cash_balance": 10000.0,
                        "total_equity": 10000.0,
                    },
                ]
            )
        elif table_name == "trades":
            # Entry trade price was 763.99 (previous close) instead of 770.58!
            mock_t.execute.return_value = MagicMock(
                data=[
                    {
                        "id": "t-entry",
                        "signal": "BUY",
                        "price": 763.99,
                        "quantity": 13,
                        "executed_at": f"{target_date}T13:30:00Z",
                    },
                    {
                        "id": "t-exit",
                        "signal": "SELL",
                        "price": 769.50,
                        "quantity": 13,
                        "executed_at": f"{target_date}T20:00:00Z",
                    },
                ]
            )
        elif table_name == "portfolio_positions":
            mock_t.execute.return_value = MagicMock(data=[])
        else:
            mock_t.execute.return_value = MagicMock(data=[])
        return mock_t

    mock_supabase.table.side_effect = table_router

    report = await audit_system_portfolios(
        target_date=target_date,
        lookback_days=1,
        auto_heal=False,
        supabase_client=mock_supabase,
    )

    assert report["status"] == "anomalies_detected"
    assert len(report["anomalies"]) == 1
    anomaly = report["anomalies"][0]
    assert anomaly["type"] == "INVALID_ENTRY_PRICE_DAILY_SPY"
    assert anomaly["owner_id"] == "sys-daily-spy-close-deepseek-v4-flash"
    assert "763.99" in anomaly["details"]
    assert "770.58" in anomaly["details"]


@pytest.mark.asyncio
async def test_audit_auto_heals_invalid_entry_price_daily_spy(mock_supabase):
    """Auto-heals trades with invalid entry prices by recalculating with session open."""
    from audit.portfolio_auditor import audit_system_portfolios

    target_date = "2026-10-02"
    pred = {
        "id": "pred-10-02",
        "model_name": "deepseek-v4-flash",
        "predicted_direction": "UP",
        "expected_return_pct": 0.20,
        "target_date": target_date,
        "open_price": 770.58,
        "high_price": 772.65,
        "low_price": 767.15,
        "close_price": 769.50,
    }

    inserted_trades = []

    def table_router(table_name):
        mock_t = MagicMock()
        mock_t.select.return_value = mock_t
        mock_t.insert.side_effect = lambda p: inserted_trades.append(p) or mock_t
        mock_t.upsert.return_value = mock_t
        mock_t.update.return_value = mock_t
        mock_t.delete.return_value = mock_t
        mock_t.eq.return_value = mock_t
        mock_t.gte.return_value = mock_t
        mock_t.lte.return_value = mock_t
        mock_t.lt.return_value = mock_t
        mock_t.like.return_value = mock_t
        mock_t.order.return_value = mock_t
        mock_t.limit.return_value = mock_t

        if table_name == "daily_predictions":
            mock_t.execute.return_value = MagicMock(data=[pred])
        elif table_name == "portfolios":
            mock_t.execute.return_value = MagicMock(
                data=[
                    {
                        "id": str(uuid4()),
                        "owner_id": "sys-daily-spy-close-deepseek-v4-flash",
                        "cash_balance": 10000.0,
                        "total_equity": 10000.0,
                    },
                ]
            )
        elif table_name == "trades":
            # Initial select returns invalid entry price
            if not inserted_trades:
                mock_t.execute.return_value = MagicMock(
                    data=[
                        {
                            "id": "t-old-1",
                            "signal": "BUY",
                            "price": 763.99,
                            "quantity": 13,
                            "realized_pnl": None,
                            "executed_at": f"{target_date}T13:30:00Z",
                        },
                        {
                            "id": "t-old-2",
                            "signal": "SELL",
                            "price": 769.50,
                            "quantity": 13,
                            "realized_pnl": 71.63,
                            "executed_at": f"{target_date}T20:00:00Z",
                        },
                    ]
                )
            else:
                mock_t.execute.return_value = MagicMock(data=inserted_trades)
        elif table_name == "portfolio_performance":
            # Prior day performance
            mock_t.execute.return_value = MagicMock(data=[{"total_equity": 10000.0}])
        elif table_name == "portfolio_positions":
            mock_t.execute.return_value = MagicMock(data=[])
        else:
            mock_t.execute.return_value = MagicMock(data=[])
        return mock_t

    mock_supabase.table.side_effect = table_router

    with patch("execution.daily_trading.get_supabase_client", return_value=mock_supabase):
        report = await audit_system_portfolios(
            target_date=target_date,
            lookback_days=1,
            auto_heal=True,
            supabase_client=mock_supabase,
        )

    assert report["status"] == "healed"
    assert len(report["healed"]) == 1
    healed = report["healed"][0]
    assert healed["action"] == "AUTO_HEALED_DAILY_SPY"
    # Entry trade should now be based on open_price ~770.58
    assert len(inserted_trades) >= 2
    entry_trade = inserted_trades[0]
    assert abs(entry_trade["price"] - 770.58) < 1.0


@pytest.mark.asyncio
async def test_portfolio_auditor_detects_and_heals_unclosed_short_trade(mock_supabase):
    """Verify portfolio auditor detects unclosed entry SHORT trade and heals its realized_pnl from matching COVER."""
    from audit.portfolio_auditor import audit_system_portfolios

    target_date = "2026-09-28"
    portfolio_id = "p-jev"
    pred = {
        "model_name": "~typesafe/jev-latest",
        "predicted_direction": "DOWN",
        "expected_return_pct": 0.0,
        "target_date": target_date,
        "open_price": 768.20,
        "high_price": 769.00,
        "low_price": 765.00,
        "close_price": 765.66,
    }

    mock_portfolios = [
        {
            "id": portfolio_id,
            "owner_id": "sys-daily-spy-close-~typesafe/jev-latest",
            "cash_balance": 10000.0,
            "total_equity": 10000.0,
        }
    ]

    mock_trades = [
        {
            "id": "t-short-1",
            "portfolio_id": portfolio_id,
            "signal": "SHORT",
            "price": 768.20,
            "quantity": 12,
            "realized_pnl": None,
            "executed_at": f"{target_date}T13:30:00Z",
        },
        {
            "id": "t-cover-1",
            "portfolio_id": portfolio_id,
            "signal": "COVER",
            "price": 765.66,
            "quantity": 12,
            "realized_pnl": 30.40,
            "realized_pnl_pct": 0.33,
            "executed_at": f"{target_date}T20:00:00Z",
        },
    ]

    updated_records = []

    def table_router(table_name):
        mock_t = MagicMock()
        mock_t.select.return_value = mock_t
        mock_t.eq.return_value = mock_t
        mock_t.gte.return_value = mock_t
        mock_t.lte.return_value = mock_t
        mock_t.like.return_value = mock_t

        def record_update(payload):
            updated_records.append(payload)
            ub = MagicMock()
            ub.eq.return_value = ub
            ub.execute.return_value = MagicMock(data=[payload])
            return ub

        mock_t.update.side_effect = record_update

        if table_name == "daily_predictions":
            mock_t.execute.return_value = MagicMock(data=[pred])
        elif table_name == "portfolios":
            mock_t.execute.return_value = MagicMock(data=mock_portfolios)
        elif table_name == "trades":
            mock_t.execute.return_value = MagicMock(data=mock_trades)
        elif table_name == "portfolio_positions":
            mock_t.execute.return_value = MagicMock(data=[])
        elif table_name == "portfolio_performance":
            mock_t.execute.return_value = MagicMock(data=[{"total_equity": 10000.0}])
        else:
            mock_t.execute.return_value = MagicMock(data=[])
        return mock_t

    mock_supabase.table.side_effect = table_router

    # 1. Without auto-heal: detects anomaly
    report = await audit_system_portfolios(
        target_date=target_date,
        lookback_days=1,
        auto_heal=False,
        supabase_client=mock_supabase,
    )

    assert report["status"] == "anomalies_detected"
    assert len(report["anomalies"]) == 1
    anomaly = report["anomalies"][0]
    assert anomaly["type"] == "UNCLOSED_SHORT_DAILY_SPY"
    assert anomaly["owner_id"] == "sys-daily-spy-close-~typesafe/jev-latest"

    # 2. With auto-heal: heals entry trade
    report_heal = await audit_system_portfolios(
        target_date=target_date,
        lookback_days=1,
        auto_heal=True,
        supabase_client=mock_supabase,
    )

    assert report_heal["status"] == "healed"
    assert len(report_heal["healed"]) == 1
    healed = report_heal["healed"][0]
    assert healed["type"] == "UNCLOSED_SHORT_DAILY_SPY"
    entry_pnl_update = next((u for u in updated_records if u.get("realized_pnl") == 30.40), None)
    assert entry_pnl_update is not None


@pytest.mark.asyncio
async def test_portfolio_auditor_detects_and_heals_unliquidated_max_pain_position(mock_supabase):
    """After market close, any unliquidated sys-max-pain position is flagged and backfilled at target (if RTH high touched) or RTH close."""
    from audit.portfolio_auditor import audit_system_portfolios

    target_date = "2026-10-22"
    portfolio_id = "p-max-pain"
    mock_portfolios = [
        {
            "id": portfolio_id,
            "owner_id": "sys-max-pain",
            "cash_balance": 2370.0,
            "total_equity": 10000.0,
        }
    ]
    mock_positions = [
        {
            "id": "pos-1",
            "portfolio_id": portfolio_id,
            "ticker": "SPY",
            "quantity": 10,
            "average_cost_basis": 763.0,
            "last_updated_at": f"{target_date}T14:30:00Z",
        }
    ]
    inserted_trades = []
    deleted_positions = []

    def table_router(table_name):
        mock_t = MagicMock()
        mock_t.select.return_value = mock_t
        mock_t.eq.return_value = mock_t
        mock_t.gte.return_value = mock_t
        mock_t.lte.return_value = mock_t
        mock_t.lt.return_value = mock_t
        mock_t.like.return_value = mock_t
        mock_t.order.return_value = mock_t
        mock_t.limit.return_value = mock_t
        mock_t.update.return_value = mock_t
        mock_t.upsert.return_value = mock_t
        mock_t.insert.side_effect = lambda payload: inserted_trades.append(payload) or mock_t
        mock_t.delete.side_effect = lambda: deleted_positions.append(table_name) or mock_t

        if table_name == "portfolios":
            mock_t.execute.return_value = MagicMock(data=mock_portfolios)
        elif table_name == "portfolio_positions":
            mock_t.execute.return_value = MagicMock(data=mock_positions)
        else:
            mock_t.execute.return_value = MagicMock(data=[])
        return mock_t

    mock_supabase.table.side_effect = table_router

    # RTH high (769.20) touched Max Pain strike ($769.00), while RTH close was 764.50
    with (
        patch(
            "tasks.evaluate_daily_predictions.fetch_intraday_prices",
            return_value=(763.0, 769.20, 762.0, 764.50),
        ),
        patch(
            "execution.providers.alpaca_max_pain.get_verified_max_pain",
            return_value={"max_pain": 769.0, "expiration": target_date},
        ),
    ):
        report = await audit_system_portfolios(
            target_date=target_date,
            lookback_days=1,
            auto_heal=True,
            supabase_client=mock_supabase,
        )

    assert report["status"] == "healed"
    assert any(a["type"] == "UNLIQUIDATED_MAX_PAIN_POSITION" for a in report["anomalies"])
    assert any(h["owner_id"] == "sys-max-pain" for h in report["healed"])
    assert len(inserted_trades) == 1
    exit_trade = inserted_trades[0]
    assert exit_trade["signal"] == "SELL"
    assert exit_trade["alpaca_status"] == "BACKFILLED"
    # Should exit at target strike ($769.00 * (1 - 1bps)) since RTH high touched $769.00
    assert round(exit_trade["price"], 4) == round(769.0 * (1.0 - 0.0001), 4)
    assert "portfolio_positions" in deleted_positions


@pytest.mark.asyncio
async def test_audit_auto_heal_anchors_to_initial_capital_when_no_prior_history(mock_supabase):
    """Verify auto-healing an initial session anchors to INITIAL_PORTFOLIO_CASH ($10,000), not dirty portfolio cash."""
    from audit.portfolio_auditor import audit_system_portfolios

    target_date = "2026-10-27"
    pred = {
        "id": "pred-jev-1",
        "model_name": "jev-four-regime-champion",
        "predicted_direction": "UP",
        "expected_return_pct": 0.0,
        "target_date": target_date,
        "open_price": 767.39,
        "high_price": 769.80,
        "low_price": 767.00,
        "close_price": 769.66,
    }

    portfolio_updates = []
    performance_upserts = []

    def table_router(table_name):
        mock_t = MagicMock()
        mock_t.select.return_value = mock_t
        mock_t.insert.return_value = mock_t
        mock_t.upsert.side_effect = lambda payload, **kwargs: performance_upserts.append(payload) or mock_t
        mock_t.update.side_effect = lambda payload: portfolio_updates.append(payload) or mock_t
        mock_t.delete.return_value = mock_t
        mock_t.eq.return_value = mock_t
        mock_t.gte.return_value = mock_t
        mock_t.lte.return_value = mock_t
        mock_t.lt.return_value = mock_t
        mock_t.like.return_value = mock_t
        mock_t.order.return_value = mock_t
        mock_t.limit.return_value = mock_t

        if table_name == "daily_predictions":
            mock_t.execute.return_value = MagicMock(data=[pred])
        elif table_name == "portfolios":
            # Dirty cash balance representing Day 2 state ($10,025.21)
            mock_t.execute.return_value = MagicMock(
                data=[
                    {
                        "id": str(uuid4()),
                        "owner_id": "sys-daily-spy-close-jev-four-regime-champion",
                        "cash_balance": 10025.21,
                        "total_equity": 10025.21,
                    },
                ]
            )
        elif table_name == "portfolio_performance":
            # No prior performance record before 2026-10-27
            mock_t.execute.return_value = MagicMock(data=[])
        elif table_name == "trades":
            # Missing trades for 2026-10-27
            mock_t.execute.return_value = MagicMock(data=[])
        elif table_name == "portfolio_positions":
            mock_t.execute.return_value = MagicMock(data=[])
        else:
            mock_t.execute.return_value = MagicMock(data=[])
        return mock_t

    mock_supabase.table.side_effect = table_router

    with patch("execution.daily_trading.get_supabase_client", return_value=mock_supabase):
        report = await audit_system_portfolios(
            target_date=target_date,
            lookback_days=1,
            auto_heal=True,
            supabase_client=mock_supabase,
        )

    assert report["status"] == "healed"
    healed = [h for h in report["healed"] if h["owner_id"] == "sys-daily-spy-close-jev-four-regime-champion"][0]

    # Starting from $10,000, 13 shares bought at 767.54, sold at 769.51 -> +$25.51 profit.
    # Total equity MUST be ~10,025.51, NOT 10,050.72 (which was 10,025.21 + 25.51).
    assert healed["new_equity"] is not None
    assert round(healed["new_equity"], 2) == 10025.51
    assert healed["new_equity"] < 10040.0


@pytest.mark.asyncio
async def test_audit_detects_and_heals_desynced_performance_equity(mock_supabase):
    """Verify that when performance equity drifts from prior equity + trade realized PnL, it is detected and healed."""
    from audit.portfolio_auditor import audit_system_portfolios

    target_date = "2026-10-28"
    pred = {
        "id": "pred-jev-2",
        "model_name": "jev-four-regime-champion",
        "predicted_direction": "UP",
        "expected_return_pct": 0.0,
        "target_date": target_date,
        "open_price": 771.45,
        "high_price": 773.00,
        "low_price": 770.00,
        "close_price": 771.17,
    }

    trades = [
        {
            "id": "t-buy",
            "signal": "BUY",
            "quantity": 13,
            "price": 771.45,
            "realized_pnl": None,
            "executed_at": f"{target_date}T13:30:00Z",
        },
        {
            "id": "t-sell",
            "signal": "SELL",
            "quantity": 13,
            "price": 771.17,
            "realized_pnl": -3.64,
            "executed_at": f"{target_date}T19:30:00Z",
        },
    ]

    performance_updates = []

    def table_router(table_name):
        mock_t = MagicMock()
        mock_t.select.return_value = mock_t
        mock_t.update.side_effect = lambda payload: performance_updates.append(payload) or mock_t
        mock_t.eq.return_value = mock_t
        mock_t.gte.return_value = mock_t
        mock_t.lte.return_value = mock_t
        mock_t.lt.return_value = mock_t
        mock_t.like.return_value = mock_t
        mock_t.order.return_value = mock_t
        mock_t.limit.return_value = mock_t

        if table_name == "daily_predictions":
            mock_t.execute.return_value = MagicMock(data=[pred])
        elif table_name == "portfolios":
            mock_t.execute.return_value = MagicMock(
                data=[
                    {
                        "id": "p-jev",
                        "owner_id": "sys-daily-spy-close-jev-four-regime-champion",
                        "cash_balance": 10050.72,
                        "total_equity": 10050.72,
                    },
                ]
            )
        elif table_name == "trades":
            mock_t.execute.return_value = MagicMock(data=trades)
        elif table_name == "portfolio_performance":
            # If lt("date", target_date): returns Day 1 equity: 10025.51
            # If eq("date", target_date): returns desynced Day 2 equity: 10025.21 (expected is 10025.51 - 3.64 = 10021.87)
            # We can mock this dynamically by inspecting call args or returning based on call
            class PerfMock:
                def __init__(self):
                    self.is_lt = False

                def select(self, *a, **kw):
                    return self

                def eq(self, col, val):
                    return self

                def lt(self, col, val):
                    self.is_lt = True
                    return self

                def order(self, *a, **kw):
                    return self

                def limit(self, *a, **kw):
                    return self

                def update(self, payload):
                    performance_updates.append(payload)
                    return self

                def execute(self):
                    if self.is_lt:
                        return MagicMock(data=[{"total_equity": 10025.51}])
                    else:
                        return MagicMock(data=[{"total_equity": 10025.21}])

            return PerfMock()
        elif table_name == "portfolio_positions":
            mock_t.execute.return_value = MagicMock(data=[])
        else:
            mock_t.execute.return_value = MagicMock(data=[])
        return mock_t

    mock_supabase.table.side_effect = table_router

    report = await audit_system_portfolios(
        target_date=target_date,
        lookback_days=1,
        auto_heal=True,
        supabase_client=mock_supabase,
    )

    assert report["status"] == "healed"
    assert any(a["type"] == "DESYNCED_EQUITY_DAILY_SPY" for a in report["anomalies"])
    healed = [h for h in report["healed"] if h["type"] == "DESYNCED_EQUITY_DAILY_SPY"][0]
    # 10025.51 - 3.64 = 10021.87
    assert healed["new_equity"] == 10021.87
    assert any(u.get("total_equity") == 10021.87 for u in performance_updates)
