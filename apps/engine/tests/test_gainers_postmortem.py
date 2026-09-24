"""Unit tests for the Benchify Missed Gainers Post-Mortem Audit pipeline.

Hermetic tests: strictly mock all external APIs (FMP, OpenAI, Supabase).
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from analysis.gainers_postmortem import (
    GainerItem,
    MissedGainerDiagnosis,
    PredictionAuditRecord,
    audit_internal_predictions,
    diagnose_missed_gainer,
    fetch_recent_ticker_news,
    fetch_top_gainers,
    run_gainers_postmortem,
    save_gainer_postmortem_memory,
)


@pytest.fixture(autouse=True)
def mock_fmp_api_key(monkeypatch):
    """Ensure FMP_API_KEY is hermetically mocked for all postmortem tests."""
    monkeypatch.setattr("analysis.gainers_postmortem.FMP_API_KEY", "mock-fmp-key")


@pytest.mark.asyncio
async def test_fetch_top_gainers_daily_filters_penny_stocks():
    """Verify daily gainers endpoint filters out stocks under $2.00."""
    mock_data = [
        {"symbol": "PENN", "price": 0.45, "changesPercentage": 120.0, "volume": 50000},
        {"symbol": "GOOD", "price": 15.20, "changesPercentage": 45.0, "volume": 1500000},
        {"symbol": "BEST", "price": 28.50, "changesPercentage": 85.0, "volume": 800000},
    ]
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_data
        mock_get.return_value = mock_resp

        gainers = await fetch_top_gainers(timeframe="daily", limit=5)
        symbols = [g.symbol for g in gainers]
        assert "PENN" not in symbols
        assert symbols == ["BEST", "GOOD"]
        assert gainers[0].change_pct == 85.0


@pytest.mark.asyncio
async def test_fetch_top_gainers_weekly_and_monthly():
    """Verify weekly (5D) and monthly (1M) gainers are properly sorted from screener and price change data."""
    screener_mock = [{"symbol": "AMD"}, {"symbol": "NVDA"}, {"symbol": "META"}]
    price_change_mock = [
        {"symbol": "AMD", "5D": 12.5, "1M": 20.1},
        {"symbol": "NVDA", "5D": 3.2, "1M": 8.0},
        {"symbol": "META", "5D": 8.1, "1M": 35.4},
    ]
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_screener_resp = MagicMock(status_code=200, json=MagicMock(return_value=screener_mock))
        mock_pc_resp = MagicMock(status_code=200, json=MagicMock(return_value=price_change_mock))
        mock_get.side_effect = [mock_screener_resp, mock_pc_resp]

        weekly = await fetch_top_gainers(timeframe="weekly", limit=2)
        assert len(weekly) == 2
        assert weekly[0].symbol == "AMD"
        assert weekly[0].change_pct == 12.5

        mock_get.side_effect = [mock_screener_resp, mock_pc_resp]
        monthly = await fetch_top_gainers(timeframe="monthly", limit=2)
        assert len(monthly) == 2
        assert monthly[0].symbol == "META"
        assert monthly[0].change_pct == 35.4


@pytest.mark.asyncio
async def test_fetch_top_gainers_handles_fmp_error_gracefully():
    """Verify FMP connection error returns empty list without raising."""
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.side_effect = Exception("FMP connection timeout")
        gainers = await fetch_top_gainers(timeframe="daily", limit=5)
        assert gainers == []


@pytest.mark.asyncio
async def test_fetch_recent_ticker_news():
    """Verify news extraction pulls headlines and formats context cleanly."""
    mock_news = [
        {"title": "AMD announces new AI chips", "publishedDate": "2026-09-24 10:00:00"},
        {"title": "Semiconductor sector gains momentum", "publishedDate": "2026-09-23 15:30:00"},
    ]
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_resp = MagicMock(status_code=200, json=MagicMock(return_value=mock_news))
        mock_get.return_value = mock_resp

        headlines = await fetch_recent_ticker_news("AMD", limit=2)
        assert len(headlines) == 2
        assert "AMD announces new AI chips" in headlines[0]


@pytest.mark.asyncio
async def test_fetch_top_gainers_missing_fmp_api_key(monkeypatch):
    """Verify empty list returned when FMP_API_KEY is unset."""
    monkeypatch.setattr("analysis.gainers_postmortem.FMP_API_KEY", "")
    gainers = await fetch_top_gainers(timeframe="daily", limit=5)
    assert gainers == []


@pytest.mark.asyncio
async def test_fetch_recent_ticker_news_missing_fmp_api_key(monkeypatch):
    """Verify empty list returned when FMP_API_KEY is unset."""
    monkeypatch.setattr("analysis.gainers_postmortem.FMP_API_KEY", "")
    headlines = await fetch_recent_ticker_news("AMD", limit=2)
    assert headlines == []


@pytest.mark.asyncio
async def test_fetch_top_gainers_explicit_api_key():
    """Verify explicit api_key argument overrides environment."""
    mock_data = [
        {"symbol": "GOOD", "price": 15.20, "changesPercentage": 45.0, "volume": 1500000},
    ]
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_resp = MagicMock(status_code=200, json=MagicMock(return_value=mock_data))
        mock_get.return_value = mock_resp

        gainers = await fetch_top_gainers(timeframe="daily", limit=1, api_key="custom-key")
        assert len(gainers) == 1
        assert gainers[0].symbol == "GOOD"
        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args.kwargs
        assert call_kwargs["params"]["apikey"] == "custom-key"


@pytest.mark.asyncio
async def test_audit_internal_predictions_when_missed():
    """Verify audit correctly reports completely missed ticker with zero decisions or trades."""
    mock_sb = MagicMock()
    mock_sb.table().select().eq().gte().execute.return_value = MagicMock(data=[])
    mock_sb.table().select().order().limit().execute.return_value = MagicMock(data=[])

    audit = await audit_internal_predictions(ticker="XYZ", timeframe="weekly", sb_client=mock_sb)
    assert audit.ticker == "XYZ"
    assert audit.found_in_decisions is False
    assert audit.found_in_trades is False
    assert audit.was_missed is True


@pytest.mark.asyncio
async def test_audit_internal_predictions_when_faded():
    """Verify audit captures prior HOLD/SELL signals when model considered the ticker."""
    mock_sb = MagicMock()
    mock_decision = [
        {
            "ticker": "AMD",
            "signal": "HOLD",
            "confidence": 70,
            "reasoning": "Valuation stretched at 45x forward earnings.",
            "model_name": "deepseek-chat",
            "created_at": "2026-09-20T10:00:00Z",
        }
    ]
    mock_sb.table().select().eq().gte().execute.side_effect = [
        MagicMock(data=mock_decision),  # decisions
        MagicMock(data=[]),  # trades
    ]
    mock_sb.table().select().order().limit().execute.return_value = MagicMock(data=[])

    audit = await audit_internal_predictions(ticker="AMD", timeframe="weekly", sb_client=mock_sb)
    assert audit.found_in_decisions is True
    assert "HOLD" in audit.signals_seen
    assert audit.was_missed is True
    assert "deepseek-chat" in audit.decisions_summary


@pytest.mark.asyncio
async def test_diagnose_missed_gainer_uses_gpt_5_6_luna_with_thinking():
    """Verify diagnose_missed_gainer calls gpt-5.6-luna with thinking (reasoning_effort='medium') via Mode.JSON."""
    gainer = GainerItem(
        symbol="AMD",
        name="Advanced Micro Devices",
        timeframe="weekly",
        price=162.0,
        change_pct=11.9,
    )
    audit = PredictionAuditRecord(
        ticker="AMD",
        found_in_decisions=True,
        signals_seen=["HOLD"],
        decisions_summary="DeepSeek called HOLD due to valuation.",
        found_in_trades=False,
        trades_summary="No trades executed.",
        sector_name="Semiconductors",
        sector_prediction_summary="SMH predicted #1 top sector.",
        was_missed=True,
    )
    expected_diagnosis = MissedGainerDiagnosis(
        ticker="AMD",
        timeframe="weekly",
        return_pct=11.9,
        actual_catalyst="Hyperscaler ASIC guidance update.",
        predictability_score=4,
        missed_reason_category="MOMENTUM_TIMIDITY",
        why_missed="Models faded breakout despite strong sector tailwinds.",
        actionable_lesson="Loosen valuation ceilings when sector conviction is high.",
    )

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=expected_diagnosis)

    with patch("analysis.gainers_postmortem.get_diagnosis_openai_client", return_value=mock_client):
        res = await diagnose_missed_gainer(gainer, audit, headlines=["AMD launches chip"])
        assert res.ticker == "AMD"
        assert res.missed_reason_category == "MOMENTUM_TIMIDITY"

        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert call_kwargs["model"] == "gpt-5.6-luna"
        assert call_kwargs["reasoning_effort"] == "medium"
        assert call_kwargs["response_model"] == MissedGainerDiagnosis


@pytest.mark.asyncio
async def test_save_gainer_postmortem_memory_deduplication():
    """Verify 7-day deduplication prevents duplicate memory insertions."""
    diagnosis = MissedGainerDiagnosis(
        ticker="AMD",
        timeframe="weekly",
        return_pct=11.9,
        actual_catalyst="Hyperscaler guidance.",
        predictability_score=4,
        missed_reason_category="MOMENTUM_TIMIDITY",
        why_missed="Models faded breakout.",
        actionable_lesson="Loosen valuation ceilings on high-conviction sectors.",
    )
    mock_sb = MagicMock()

    # Case A: Memory already exists in last 7 days -> skips
    mock_sb.table().select().filter().filter().filter().gte().execute.return_value = MagicMock(
        data=[{"id": "existing-1"}]
    )
    saved = await save_gainer_postmortem_memory(diagnosis, sb_client=mock_sb)
    assert saved is None

    # Case B: No existing memory -> calls add_memory
    mock_sb.table().select().filter().filter().filter().gte().execute.return_value = MagicMock(data=[])
    with patch("analysis.gainers_postmortem.add_memory", return_value=True) as mock_add:
        saved = await save_gainer_postmortem_memory(diagnosis, sb_client=mock_sb)
        assert saved is not None
        assert mock_add.called
        kwargs = mock_add.call_args.kwargs
        assert kwargs["memory_type"] == "POST_MORTEM"
        assert kwargs["metadata"]["ticker"] == "AMD"
        assert kwargs["metadata"]["category"] == "MOMENTUM_TIMIDITY"


@pytest.mark.asyncio
async def test_run_gainers_postmortem_orchestration():
    """Verify run_gainers_postmortem coordinates fetching, auditing, diagnosing, and memory storage."""
    mock_gainers = [GainerItem(symbol="AMD", name="AMD", timeframe="weekly", price=162.0, change_pct=11.9)]
    mock_diag = MissedGainerDiagnosis(
        ticker="AMD",
        timeframe="weekly",
        return_pct=11.9,
        actual_catalyst="AI chip growth.",
        predictability_score=4,
        missed_reason_category="MOMENTUM_TIMIDITY",
        why_missed="Missed move.",
        actionable_lesson="Track sector momentum.",
    )

    with (
        patch("analysis.gainers_postmortem.fetch_top_gainers", new_callable=AsyncMock, return_value=mock_gainers),
        patch("analysis.gainers_postmortem.fetch_recent_ticker_news", new_callable=AsyncMock, return_value=["News"]),
        patch(
            "analysis.gainers_postmortem.audit_internal_predictions",
            new_callable=AsyncMock,
            return_value=PredictionAuditRecord(
                ticker="AMD",
                found_in_decisions=False,
                signals_seen=[],
                decisions_summary="",
                found_in_trades=False,
                trades_summary="",
                sector_name=None,
                sector_prediction_summary="",
                was_missed=True,
            ),
        ),
        patch("analysis.gainers_postmortem.diagnose_missed_gainer", new_callable=AsyncMock, return_value=mock_diag),
        patch(
            "analysis.gainers_postmortem.save_gainer_postmortem_memory",
            new_callable=AsyncMock,
            return_value="mem-123",
        ),
    ):
        results = await run_gainers_postmortem(timeframe="weekly", limit=1, save_memory=True)
        assert len(results) == 1
        assert results[0].ticker == "AMD"


def test_main_cli_gainers_postmortem_dispatch():
    """Verify main.py CLI routes gainers-postmortem subcommand properly."""
    import sys

    import main

    with (
        patch.object(
            sys,
            "argv",
            ["main.py", "gainers-postmortem", "--timeframe", "weekly", "--limit", "2", "--no-save-memory"],
        ),
        patch("analysis.gainers_postmortem.run_gainers_postmortem", new_callable=AsyncMock) as mock_run,
    ):
        main.main()
        mock_run.assert_called_once_with(timeframe="weekly", limit=2, save_memory=False)
