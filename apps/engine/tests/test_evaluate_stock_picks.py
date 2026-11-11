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
