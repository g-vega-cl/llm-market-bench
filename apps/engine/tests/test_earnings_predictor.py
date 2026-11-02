"""Hermetic unit tests for Day-1 Earnings Predictor task across Luna, DeepSeek, and Jev."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.llm.earnings_predictor_prompts import EarningsPredictionOutput
from tasks.earnings_predictor import (
    discover_earnings_candidates,
    format_candidate_context,
    predict_with_deepseek,
    predict_with_jev,
    predict_with_luna,
    run_earnings_prediction,
)


@pytest.fixture
def sample_candidate():
    return {
        "snapshot_date": "2026-10-07",
        "ticker": "NVDA",
        "sector": "Technology",
        "report_date": "2026-10-07",
        "report_timing": "BMO",
        "actual_eps": 1.25,
        "estimated_eps": 1.10,
        "eps_surprise": 0.15,
        "revenue_actual": 30000000000,
        "revenue_estimated": 28500000000,
        "revenue_surprise_pct": 5.26,
        "sue_score": 3.40,
        "is_top_decile_sue": True,
        "sloan_accrual_ratio": 0.04,
        "is_sloan_accrual_clean": True,
        "pre_earnings_20d_return_pct": 4.5,
        "analyst_consensus": "Strong Buy",
        "target_consensus_upside_pct": 14.5,
    }


def test_format_candidate_context(sample_candidate):
    """Verify that candidate context generates dense textual metrics."""
    ctx = format_candidate_context(sample_candidate)
    assert "Asset: NVDA (Sector: Technology)" in ctx
    assert "Timing: BMO" in ctx
    assert "Actual EPS: $1.25 vs Estimated EPS: $1.10" in ctx
    assert "Revenue Surprise: +5.3%" in ctx
    assert "Standardized Unexpected Earnings (SUE): 3.40" in ctx
    assert "Clean Operating Cash Flow" in ctx


@pytest.mark.asyncio
async def test_predict_with_luna(sample_candidate):
    """Verify GPT Luna inference using mocked Instructor client."""
    mock_resp = EarningsPredictionOutput(
        predicted_direction="UP",
        confidence=85.0,
        expected_return_pct=2.8,
        rationale="Strong SUE beat with top-decile momentum.",
        catalysts=["Revenue beat +5.26%", "Clean Sloan cash accruals"],
    )

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)

    with patch("tasks.earnings_predictor.get_openai_client", return_value=mock_client):
        res = await predict_with_luna(sample_candidate, "sample context")
        assert res["predicted_direction"] == "UP"
        assert res["confidence"] == 85.0
        assert res["expected_return_pct"] == 2.8
        assert "GPT Luna:" in res["rationale"]
        assert len(res["catalysts"]) == 2


@pytest.mark.asyncio
async def test_predict_with_deepseek(sample_candidate):
    """Verify DeepSeek Flash inference using mocked Instructor client."""
    mock_resp = EarningsPredictionOutput(
        predicted_direction="DOWN",
        confidence=65.0,
        expected_return_pct=-1.5,
        rationale="Parabolic run-up will trigger sell the news.",
        catalysts=["Exhaustion"],
    )

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)

    with patch("tasks.earnings_predictor.get_deepseek_client", return_value=mock_client):
        res = await predict_with_deepseek(sample_candidate, "sample context")
        assert res["predicted_direction"] == "DOWN"
        assert res["confidence"] == 65.0
        assert res["expected_return_pct"] == -1.5
        assert "DeepSeek Flash:" in res["rationale"]


@pytest.mark.asyncio
async def test_predict_with_jev(sample_candidate):
    """Verify TypeSafe Jev decision classification using mocked OpenRouter Decisions API."""
    mock_response_data = {
        "answers": {
            "day1_earnings_direction": {
                "choice": "UP",
                "confidence": 0.78,
                "probabilities": {"UP": 0.78, "DOWN": 0.22},
            }
        }
    }

    mock_http_resp = MagicMock()
    mock_http_resp.status_code = 200
    mock_http_resp.json = MagicMock(return_value=mock_response_data)

    mock_client_instance = AsyncMock()
    mock_client_instance.post = AsyncMock(return_value=mock_http_resp)

    with (
        patch("tasks.earnings_predictor.OPENROUTER_API_KEY", "mock-openrouter-key"),
        patch("httpx.AsyncClient") as mock_http_cls,
    ):
        mock_http_cls.return_value.__aenter__.return_value = mock_client_instance

        res = await predict_with_jev(sample_candidate)
        assert res["predicted_direction"] == "UP"
        assert res["confidence"] == 78.0
        assert "TypeSafe Jev System One decision" in res["rationale"]


@pytest.mark.asyncio
async def test_run_earnings_prediction_end_to_end(sample_candidate):
    """Verify full arena orchestration and upsert into database."""
    mock_db = MagicMock()
    mock_table = MagicMock()
    mock_db.table.return_value = mock_table
    mock_table.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
    mock_table.upsert.return_value.execute.return_value = MagicMock()

    mock_luna = {
        "predicted_direction": "UP",
        "confidence": 80.0,
        "expected_return_pct": 2.0,
        "rationale": "Luna",
        "catalysts": [],
    }
    mock_ds = {
        "predicted_direction": "UP",
        "confidence": 75.0,
        "expected_return_pct": 1.5,
        "rationale": "DS",
        "catalysts": [],
    }
    mock_jev = {
        "predicted_direction": "DOWN",
        "confidence": 60.0,
        "expected_return_pct": 0.0,
        "rationale": "Jev",
        "catalysts": [],
    }

    with (
        patch("tasks.earnings_predictor.get_supabase_client", return_value=mock_db),
        patch("tasks.earnings_predictor.discover_earnings_candidates", AsyncMock(return_value=[sample_candidate])),
        patch("tasks.earnings_predictor.predict_with_luna", AsyncMock(return_value=mock_luna)),
        patch("tasks.earnings_predictor.predict_with_deepseek", AsyncMock(return_value=mock_ds)),
        patch("tasks.earnings_predictor.predict_with_jev", AsyncMock(return_value=mock_jev)),
    ):
        results = await run_earnings_prediction(target_date="2026-10-07", ticker="NVDA", force=True)
        assert len(results) == 3
        model_names = [r["model_name"] for r in results]
        assert "gpt-5.6-luna" in model_names
        assert "deepseek-chat" in model_names
        assert "~typesafe/jev-latest" in model_names
        assert mock_table.upsert.call_count == 3


@pytest.mark.asyncio
async def test_discover_earnings_candidates_explicit_ticker():
    """Verify explicit ticker query fetches and filters for that stock."""
    mock_db = MagicMock()
    mock_table = MagicMock()
    mock_db.table.return_value = mock_table
    mock_query = mock_table.select.return_value.eq.return_value.order.return_value.limit.return_value
    mock_query.execute.return_value.data = [
        {"ticker": "GOOGL", "report_date": "2026-10-28", "actual_eps": 2.12, "estimated_eps": 3.02}
    ]

    with patch("tasks.earnings_predictor.get_supabase_client", return_value=mock_db):
        candidates = await discover_earnings_candidates("2026-10-29", ticker="GOOGL")
        assert len(candidates) == 1
        assert candidates[0]["ticker"] == "GOOGL"
        assert candidates[0]["actual_eps"] == 2.12


@pytest.mark.asyncio
async def test_discover_earnings_candidates_auto_ignores_spy():
    """Verify that passing ticker='SPY' or None triggers auto-discovery and filters out SPY."""
    mock_db = MagicMock()
    mock_table = MagicMock()
    mock_db.table.return_value = mock_table
    mock_query = (
        mock_table.select.return_value.gte.return_value.order.return_value.order.return_value.limit.return_value
    )
    mock_query.execute.return_value.data = [
        {"ticker": "SPY", "report_date": "2026-11-02", "actual_eps": 1.0},
        {"ticker": "CVX", "report_date": "2026-10-30", "actual_eps": 5.28, "estimated_eps": 4.87, "sue_score": 1.66},
        {"ticker": "XOM", "report_date": "2026-10-30", "actual_eps": 4.23, "estimated_eps": 4.12, "sue_score": 1.44},
    ]

    with patch("tasks.earnings_predictor.get_supabase_client", return_value=mock_db):
        # Passing ticker="SPY" should NOT filter by ticker="SPY"
        candidates = await discover_earnings_candidates("2026-11-02", ticker="SPY")
        tickers = [c["ticker"] for c in candidates]
        assert "SPY" not in tickers
        assert "CVX" in tickers
        assert "XOM" in tickers


@pytest.mark.asyncio
async def test_discover_earnings_candidates_fmp_calendar_fallback():
    """Verify fallback to FMP live earnings calendar when snapshots are empty."""
    mock_db = MagicMock()
    mock_table = MagicMock()
    mock_db.table.return_value = mock_table
    mock_query = (
        mock_table.select.return_value.gte.return_value.order.return_value.order.return_value.limit.return_value
    )
    mock_query.execute.return_value.data = []

    mock_cal_data = [
        {
            "symbol": "MAR",
            "date": "2026-11-02",
            "epsActual": 3.02,
            "epsEstimated": 2.84,
            "revenueActual": 7000000000,
            "revenueEstimated": 6926000000,
        }
    ]

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json = MagicMock(return_value=mock_cal_data)

    mock_http_inst = AsyncMock()
    mock_http_inst.get = AsyncMock(return_value=mock_resp)

    with (
        patch("tasks.earnings_predictor.get_supabase_client", return_value=mock_db),
        patch("tasks.earnings_predictor.FMP_API_KEY", "mock-fmp-key"),
        patch("httpx.AsyncClient") as mock_client_cls,
    ):
        mock_client_cls.return_value.__aenter__.return_value = mock_http_inst
        candidates = await discover_earnings_candidates("2026-11-02", ticker=None)
        assert len(candidates) == 1
        assert candidates[0]["ticker"] == "MAR"
        assert candidates[0]["actual_eps"] == 3.02
        assert candidates[0]["estimated_eps"] == 2.84
        assert candidates[0]["is_top_decile_sue"] is True
