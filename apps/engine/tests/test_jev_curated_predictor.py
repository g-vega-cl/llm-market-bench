import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from apps.engine.local_autoresearch.manifest import DataManifest, pack_daily_context

from core.llm.daily_predictor_prompts import (
    JEV_DEFAULT_CRITERIA,
    parse_jev_curated_prompt_content,
)


def test_parse_jev_curated_prompt_content():
    """Verify parsing of prompt_content storing criteria, min_confidence, and manifest."""
    # 1. Fallback / None
    crit, min_conf, manifest = parse_jev_curated_prompt_content(None)
    assert crit["UP"] == JEV_DEFAULT_CRITERIA["UP"]
    assert min_conf == 50.0
    assert manifest == {}

    # 2. Legacy criteria only
    legacy_json = json.dumps({"UP": "Legacy Up", "DOWN": "Legacy Down"})
    crit, min_conf, manifest = parse_jev_curated_prompt_content(legacy_json)
    assert crit["UP"] == "Legacy Up"
    assert crit["DOWN"] == "Legacy Down"
    assert min_conf == 50.0
    assert manifest == {}

    # 3. Rich curated format
    curated_json = json.dumps(
        {
            "criteria": {
                "UP": "SPY gap >= 0.30% with QQQ confirmation",
                "DOWN": "SPY gap <= -0.30% with QQQ confirmation",
            },
            "min_confidence": 61.0,
            "manifest": {
                "selected_newsletters": ["Sherwood News", "Chartr"],
                "include_macro_proxies": ["QQQ", "IWM"],
                "include_options_derivatives": True,
                "include_intraday_profile": True,
                "include_currency_uup": False,
                "include_market_health_barometer": False,
            },
        }
    )
    crit, min_conf, manifest = parse_jev_curated_prompt_content(curated_json)
    assert "SPY gap >= 0.30%" in crit["UP"]
    assert "SPY gap <= -0.30%" in crit["DOWN"]
    assert min_conf == 61.0
    assert manifest["selected_newsletters"] == ["Sherwood News", "Chartr"]
    assert manifest["include_macro_proxies"] == ["QQQ", "IWM"]
    assert manifest["include_options_derivatives"] is True
    assert manifest["include_currency_uup"] is False


def test_pack_daily_context_curation():
    """Verify pack_daily_context isolates exactly the requested Box of Data."""
    manifest = DataManifest(
        selected_newsletters=["Sherwood News", "Chartr"],
        include_synthetic_newsletter=True,
        include_macro_proxies=["QQQ", "IWM"],
        include_currency_uup=False,
        include_options_derivatives=True,
        include_economic_calendar=True,
        include_market_health_barometer=False,
        include_recent_market_feeling=False,
        include_intraday_profile=True,
    )

    day_record = {
        "target_date": "2026-10-09",
        "ticker": "SPY",
        "economic_calendar": "8:30 AM CPI release: Core MoM +0.2% vs +0.3% exp",
        "synthetic_newsletter": "AI Wall Street Summary: Tech rally carries momentum",
        "newsletters": [
            {"sender": "Sherwood News", "subject": "Market Open", "content": "Tech leads overnight."},
            {"sender": "Chartr", "subject": "Daily Visual", "content": "Earnings growth dispersion."},
            {"sender": "Random Crypto Letter", "subject": "BTC Rally", "content": "Noise to ignore."},
        ],
        "proxies": {
            "QQQ": {"price": 500.0, "change_pct": 0.45},
            "IWM": {"price": 220.0, "change_pct": 0.20},
            "TLT": {"price": 95.0, "change_pct": -0.50},
            "UUP": {"price": 28.5, "change_pct": 0.10},
        },
        "options_sentiment": "Max Pain: $580 | Put/Call Ratio: 0.85",
        "intraday_profile": "Prior Session VWAP: $578.50 | CLV: +0.65",
        "market_barometer": "50% of stocks above 200 SMA",
        "market_feeling": "Bullish euphoric mood",
    }

    curated_context = pack_daily_context(day_record, manifest)

    # Inclusions
    assert "8:30 AM CPI release" in curated_context
    assert "Tech rally carries momentum" in curated_context
    assert "Sherwood News" in curated_context
    assert "Chartr" in curated_context
    assert "- QQQ: $500.00 (+0.45%)" in curated_context
    assert "- IWM: $220.00 (+0.20%)" in curated_context
    assert "Max Pain: $580" in curated_context
    assert "Prior Session VWAP: $578.50" in curated_context

    # Exclusions
    assert "Random Crypto Letter" not in curated_context
    assert "- TLT" not in curated_context
    assert "- UUP" not in curated_context
    assert "50% of stocks above 200 SMA" not in curated_context
    assert "Bullish euphoric mood" not in curated_context


@pytest.mark.asyncio
async def test_run_daily_prediction_jev_curated_high_confidence():
    """Verify jev-local-autoresearched predicts direction when confidence exceeds threshold."""
    from tasks.daily_predictor import run_daily_prediction

    mock_sb = MagicMock()
    # No existing predictions
    mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []

    # Mock active prompt experiment for jev-local-autoresearched
    curated_payload = json.dumps(
        {
            "criteria": {"UP": "Up rule", "DOWN": "Down rule"},
            "min_confidence": 61.0,
            "manifest": {
                "selected_newsletters": ["Sherwood News"],
                "include_macro_proxies": ["QQQ"],
            },
        }
    )
    mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
        {"variant_tag": "qwen-jev-243de1", "prompt_content": curated_payload}
    ]

    mock_mdm = MagicMock()
    mock_mdm.is_trading_day = AsyncMock(return_value=True)

    mock_deepseek = MagicMock()
    mock_deepseek.chat.completions.create = AsyncMock(
        return_value=MagicMock(
            predicted_direction="UP",
            confidence=70.0,
            expected_return_pct=0.3,
            rationale="Rationale",
            catalysts=[],
        )
    )
    mock_minimax = MagicMock()
    mock_minimax.chat_with_json_response = AsyncMock(
        return_value={
            "predicted_direction": "UP",
            "confidence": 70.0,
            "expected_return_pct": 0.3,
            "rationale": "Rationale",
            "catalysts": [],
        }
    )
    mock_minimax.close = AsyncMock()

    with (
        patch("tasks.daily_predictor.get_supabase_client", return_value=mock_sb),
        patch("execution.market_data.MarketDataManager", return_value=mock_mdm),
        patch("tasks.daily_predictor.get_deepseek_client", return_value=mock_deepseek),
        patch("tasks.daily_predictor.MiniMaxClient", return_value=mock_minimax),
        patch("tasks.daily_predictor.close_client", new_callable=AsyncMock),
        patch("tasks.daily_predictor.get_structured_daily_market_context", new_callable=AsyncMock) as mock_ctx,
        patch("tasks.daily_predictor.predict_daily_with_jev", new_callable=AsyncMock) as mock_jev,
    ):
        mock_ctx.return_value = ("Monolithic text", {"ticker": "SPY", "target_date": "2026-10-09", "proxies": {}})
        mock_jev.return_value = {
            "predicted_direction": "UP",
            "confidence": 74.0,
            "expected_return_pct": 0.0,
            "rationale": "Strong pre-market confirmation.",
            "catalysts": [],
        }

        # Run with force=True to bypass time-of-day checks
        results = await run_daily_prediction(ticker="SPY", force=True)

        # Assert jev-local-autoresearched was included and predicted UP with 74%
        jev_curated_res = [r for r in results if r["model_name"] == "jev-local-autoresearched"]
        assert len(jev_curated_res) == 1
        assert jev_curated_res[0]["predicted_direction"] == "UP"
        assert jev_curated_res[0]["confidence"] == 74.0
        assert jev_curated_res[0]["prompt_variant_tag"] == "qwen-jev-243de1"


@pytest.mark.asyncio
async def test_run_daily_prediction_jev_curated_gated_no_trade():
    """Verify jev-local-autoresearched gates to NO_TRADE when confidence is below min_confidence."""
    from tasks.daily_predictor import run_daily_prediction

    mock_sb = MagicMock()
    mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []

    curated_payload = json.dumps(
        {
            "criteria": {"UP": "Up rule", "DOWN": "Down rule"},
            "min_confidence": 61.0,
            "manifest": {"selected_newsletters": ["Sherwood News"]},
        }
    )
    mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
        {"variant_tag": "qwen-jev-243de1", "prompt_content": curated_payload}
    ]

    mock_mdm = MagicMock()
    mock_mdm.is_trading_day = AsyncMock(return_value=True)

    mock_deepseek = MagicMock()
    mock_deepseek.chat.completions.create = AsyncMock(
        return_value=MagicMock(
            predicted_direction="UP",
            confidence=70.0,
            expected_return_pct=0.3,
            rationale="Rationale",
            catalysts=[],
        )
    )
    mock_minimax = MagicMock()
    mock_minimax.chat_with_json_response = AsyncMock(
        return_value={
            "predicted_direction": "UP",
            "confidence": 70.0,
            "expected_return_pct": 0.3,
            "rationale": "Rationale",
            "catalysts": [],
        }
    )
    mock_minimax.close = AsyncMock()

    with (
        patch("tasks.daily_predictor.get_supabase_client", return_value=mock_sb),
        patch("execution.market_data.MarketDataManager", return_value=mock_mdm),
        patch("tasks.daily_predictor.get_deepseek_client", return_value=mock_deepseek),
        patch("tasks.daily_predictor.MiniMaxClient", return_value=mock_minimax),
        patch("tasks.daily_predictor.close_client", new_callable=AsyncMock),
        patch("tasks.daily_predictor.get_structured_daily_market_context", new_callable=AsyncMock) as mock_ctx,
        patch("tasks.daily_predictor.predict_daily_with_jev", new_callable=AsyncMock) as mock_jev,
    ):
        mock_ctx.return_value = ("Monolithic text", {"ticker": "SPY", "target_date": "2026-10-09", "proxies": {}})
        mock_jev.return_value = {
            "predicted_direction": "UP",
            "confidence": 56.5,  # Below 61.0%!
            "expected_return_pct": 0.0,
            "rationale": "Borderline signal.",
            "catalysts": [],
        }

        results = await run_daily_prediction(ticker="SPY", force=True)

        jev_curated_res = [r for r in results if r["model_name"] == "jev-local-autoresearched"]
        assert len(jev_curated_res) == 1
        assert jev_curated_res[0]["predicted_direction"] == "NO_TRADE"
        assert jev_curated_res[0]["confidence"] == 56.5
        assert "NO_TRADE" in jev_curated_res[0]["rationale"]
