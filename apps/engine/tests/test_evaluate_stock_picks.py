"""Hermetic test suite for Daily Stock Picker Evaluation Task.

Verifies post-market price fetching, halt handling, directional hit rate,
Long/Short spread alpha, and benchmark SPY comparison without live network calls.
"""

from unittest.mock import MagicMock, patch

import pytest

from tasks.evaluate_stock_picks import evaluate_stock_picks


@pytest.mark.asyncio
async def test_evaluate_stock_picks_skips_during_active_market():
    mock_now = MagicMock()
    mock_now.strftime.return_value = "2026-11-12"
    mock_now.hour = 11
    mock_now.minute = 30  # 11:30 AM ET < 16:05 ET

    with patch("tasks.evaluate_stock_picks.get_ny_now", return_value=mock_now):
        res = await evaluate_stock_picks(target_date="2026-11-12", force_recalc=False)
        assert res["status"] == "market_active"


@pytest.mark.asyncio
async def test_evaluate_stock_picks_math_and_halts():
    mock_supabase = MagicMock()

    mock_basket = {
        "id": "basket-abc",
        "target_date": "2026-11-11",
        "model_name": "consensus",
        "status": "pending",
    }
    mock_picks = [
        # UP #1: Hit (100 -> 102, +2%)
        {
            "id": "p-1",
            "basket_id": "basket-abc",
            "ticker": "CB",
            "direction": "UP",
            "rank": 1,
            "confidence": 75.0,
        },
        # UP #2: Miss (50 -> 49, -2%)
        {
            "id": "p-2",
            "basket_id": "basket-abc",
            "ticker": "ETR",
            "direction": "UP",
            "rank": 2,
            "confidence": 70.0,
        },
        # UP #3: Halt / zero open price -> cancelled
        {
            "id": "p-3",
            "basket_id": "basket-abc",
            "ticker": "HALT",
            "direction": "UP",
            "rank": 3,
            "confidence": 60.0,
        },
        # DOWN #1: Hit (200 -> 190, stock -5%, position +5%)
        {
            "id": "p-4",
            "basket_id": "basket-abc",
            "ticker": "ABNB",
            "direction": "DOWN",
            "rank": 1,
            "confidence": 80.0,
        },
        # DOWN #2: Hit (150 -> 145, stock -3.33%, position +3.33%)
        {
            "id": "p-5",
            "basket_id": "basket-abc",
            "ticker": "NVDA",
            "direction": "DOWN",
            "rank": 2,
            "confidence": 70.0,
        },
        # DOWN #3: Miss (100 -> 105, stock +5%, position -5%)
        {
            "id": "p-6",
            "basket_id": "basket-abc",
            "ticker": "GOOGL",
            "direction": "DOWN",
            "rank": 3,
            "confidence": 65.0,
        },
    ]

    basket_tbl = MagicMock()
    basket_tbl.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[mock_basket])
    basket_tbl.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[mock_basket])

    picks_tbl = MagicMock()
    picks_tbl.select.return_value.in_.return_value.execute.return_value = MagicMock(data=mock_picks)

    def mock_table(table_name):
        return basket_tbl if table_name == "daily_stock_baskets" else picks_tbl

    mock_supabase.table.side_effect = mock_table

    # Simulated prices (Open, High, Low, Close)
    price_fixtures = {
        "SPY": (500.0, 505.0, 498.0, 505.0),  # +1.0% return
        "CB": (100.0, 103.0, 99.0, 102.0),  # +2.0%
        "ETR": (50.0, 51.0, 48.0, 49.0),  # -2.0%
        "HALT": (0.0, 0.0, 0.0, 0.0),  # Exchange halt
        "ABNB": (200.0, 201.0, 189.0, 190.0),  # -5.0%
        "NVDA": (150.0, 151.0, 144.0, 145.0),  # -3.33%
        "GOOGL": (100.0, 106.0, 99.0, 105.0),  # +5.0%
    }

    async def mock_fetch_prices(ticker, target_date, force_refresh=False):
        return price_fixtures.get(ticker, (None, None, None, None))

    with (
        patch("tasks.evaluate_stock_picks.get_supabase_client", return_value=mock_supabase),
        patch("tasks.evaluate_stock_picks.fetch_intraday_prices", side_effect=mock_fetch_prices),
    ):
        result = await evaluate_stock_picks(target_date="2026-11-11", force_recalc=True)

        assert result["status"] == "success"
        assert result["baskets_evaluated"] == 1
        assert result["picks_evaluated"] == 6
        assert result["spy_return_pct"] == 1.0

        assert basket_tbl.upsert.called
        basket_update_arg = basket_tbl.upsert.call_args_list[0][0][0][0]

        assert basket_update_arg["status"] == "evaluated"
        assert basket_update_arg["benchmark_spy_return_pct"] == 1.0
        # Valid picks: 5 total (1 halt cancelled)
        # Hits: CB (UP hit), ABNB (DOWN hit), NVDA (DOWN hit). 3 out of 5 = 60.0%
        assert basket_update_arg["directional_hit_rate"] == 60.0


@pytest.mark.asyncio
async def test_evaluate_stock_picks_full_row_batch_upsert_and_cancelled_basket():
    """Verify O(1) batch upserts preserve NOT NULL columns, uniform keys, and cancelled-basket clearing."""
    required_not_null = {
        "daily_stock_baskets": {"target_date", "model_name"},
        "daily_stock_picks": {"basket_id", "target_date", "model_name", "ticker", "direction", "rank", "confidence"},
    }

    mock_baskets = [
        {
            "id": "basket-1",
            "target_date": "2026-11-13",
            "model_name": "consensus",
            "status": "pending",
        },
        {
            "id": "basket-2",
            "target_date": "2026-11-13",
            "model_name": "deepseek-v4-flash",
            "status": "evaluated",
            "directional_hit_rate": 100.0,
            "ls_spread_alpha_pct": 2.5,
        },
    ]
    mock_picks = [
        {
            "id": "pick-1",
            "basket_id": "basket-1",
            "target_date": "2026-11-13",
            "model_name": "consensus",
            "ticker": "AMD",
            "direction": "UP",
            "rank": 1,
            "confidence": 80.0,
        },
        {
            "id": "pick-2",
            "basket_id": "basket-1",
            "target_date": "2026-11-13",
            "model_name": "consensus",
            "ticker": "NVDA",
            "direction": "DOWN",
            "rank": 1,
            "confidence": 75.0,
        },
        {
            "id": "pick-3",
            "basket_id": "basket-2",
            "target_date": "2026-11-13",
            "model_name": "deepseek-v4-flash",
            "ticker": "SUBCENT",
            "direction": "UP",
            "rank": 1,
            "confidence": 70.0,
        },
    ]

    upserted: dict[str, list[dict]] = {"daily_stock_picks": [], "daily_stock_baskets": []}

    def _make_table(name: str):
        tbl = MagicMock()
        if name == "daily_stock_baskets":
            tbl.select.return_value.eq.return_value.execute.return_value = MagicMock(data=mock_baskets)
            tbl.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=mock_baskets)
        else:
            tbl.select.return_value.in_.return_value.execute.return_value = MagicMock(data=mock_picks)

        def _strict_upsert(rows, *_args, **kwargs):
            assert kwargs.get("on_conflict") == "id"
            expected_keys = set(rows[0].keys())
            for row in rows:
                missing = required_not_null[name] - set(row.keys())
                if missing:
                    raise RuntimeError(f"null value in column {sorted(missing)[0]!r} violates not-null constraint")
                assert set(row.keys()) == expected_keys, "PostgREST batch upsert requires uniform object keys"
            upserted[name].append(rows)
            return MagicMock()

        tbl.upsert.side_effect = _strict_upsert
        return tbl

    mock_supabase = MagicMock()
    mock_supabase.table.side_effect = _make_table

    async def mock_fetch_prices(ticker, target_date, force_refresh=False):
        return {
            "SPY": (500.0, 505.0, 498.0, 502.0),
            "AMD": (100.0, 104.0, 99.0, 103.0),
            "NVDA": (200.0, 201.0, 194.0, 195.0),
            "SUBCENT": (0.001, 0.002, 0.001, 0.002),  # rounds to 0.00 -> must cancel
        }.get(ticker, (None, None, None, None))

    with (
        patch("tasks.evaluate_stock_picks.get_supabase_client", return_value=mock_supabase),
        patch("tasks.evaluate_stock_picks.fetch_intraday_prices", side_effect=mock_fetch_prices),
    ):
        result = await evaluate_stock_picks(target_date="2026-11-13", force_recalc=True)

    assert result["status"] == "success"
    assert len(upserted["daily_stock_picks"]) == 1
    assert len(upserted["daily_stock_baskets"]) == 1

    picks_by_id = {p["id"]: p for p in upserted["daily_stock_picks"][0]}
    assert picks_by_id["pick-1"]["status"] == "evaluated"
    assert picks_by_id["pick-1"]["is_hit"] is True
    assert picks_by_id["pick-2"]["status"] == "evaluated"
    assert picks_by_id["pick-2"]["is_hit"] is True
    assert picks_by_id["pick-3"]["status"] == "cancelled"
    assert picks_by_id["pick-3"]["open_price"] is None

    baskets_by_id = {b["id"]: b for b in upserted["daily_stock_baskets"][0]}
    assert baskets_by_id["basket-1"]["status"] == "evaluated"
    assert baskets_by_id["basket-1"]["directional_hit_rate"] == 100.0
    assert baskets_by_id["basket-2"]["status"] == "cancelled"
    assert baskets_by_id["basket-2"]["directional_hit_rate"] is None
    assert baskets_by_id["basket-2"]["ls_spread_alpha_pct"] is None
