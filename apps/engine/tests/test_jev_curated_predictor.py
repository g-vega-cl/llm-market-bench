import json
from unittest.mock import AsyncMock, patch

import pytest

from core.llm.daily_predictor_prompts import (
    HOLD_CONFIDENCE_THRESHOLD,
    JEV_DEFAULT_CRITERIA,
    parse_jev_curated_prompt_content,
)
from local_autoresearch.manifest import DataManifest, pack_daily_context


@pytest.fixture(autouse=True)
def mock_unconfigured_arena_models():
    """Hermetic test fixture: isolate daily predictor tests from unconfigured Laya models and external calls."""
    with (
        patch(
            "tasks.daily_predictor.generate_daily_document", side_effect=RuntimeError("Strata disabled for unit test")
        ),
        patch("tasks.daily_predictor.evaluate_with_laya", side_effect=RuntimeError("Laya disabled for unit test")),
    ):
        yield


def test_parse_jev_curated_prompt_content():
    """Verify parsing of prompt_content storing criteria, min_confidence, and manifest."""
    # 1. Fallback / None defaults to HOLD_CONFIDENCE_THRESHOLD (56.0)
    crit, min_conf, manifest = parse_jev_curated_prompt_content(None)
    assert crit["UP"] == JEV_DEFAULT_CRITERIA["UP"]
    assert min_conf == HOLD_CONFIDENCE_THRESHOLD
    assert manifest == {}

    # Custom default_conf override
    crit_custom, min_conf_custom, _ = parse_jev_curated_prompt_content(None, default_conf=52.0)
    assert min_conf_custom == 52.0

    # 2. Legacy criteria only
    legacy_json = json.dumps({"UP": "Legacy Up", "DOWN": "Legacy Down"})
    crit, min_conf, manifest = parse_jev_curated_prompt_content(legacy_json)
    assert crit["UP"] == "Legacy Up"
    assert crit["DOWN"] == "Legacy Down"
    assert min_conf == HOLD_CONFIDENCE_THRESHOLD
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
        "trend_vector": {
            "summary": "Previous Trading Session (2026-10-08) Close: $577.20\n5-Day Return: +1.80%\n20-Day Simple Moving Average (SMA20): $572.10 (Distance: +0.89%)",
        },
    }

    curated_context = pack_daily_context(day_record, manifest)

    # Inclusions
    assert "--- Multi-Day Momentum & Trend Vector ---" in curated_context
    assert "5-Day Return: +1.80%" in curated_context
    assert "20-Day Simple Moving Average (SMA20): $572.10" in curated_context
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
async def test_jev_curated_executor_predicts_direction_above_threshold():
    """The curated executor still resolves direction/confidence/min_confidence for research tooling.

    The champion left the daily arena on 2026-11-18; the executor branch stays because the
    offline Strata ratchet uses it.
    """
    from tasks.daily_predictor import JEV_MODEL, _execute_model_daily_prediction

    curated_payload = json.dumps(
        {
            "criteria": {"UP": "Up rule", "DOWN": "Down rule"},
            "min_confidence": 61.0,
            "manifest": {"selected_newsletters": ["Sherwood News"], "include_macro_proxies": ["QQQ"]},
        }
    )
    model_cfg = {"name": "jev-four-regime-champion", "type": "jev_curated", "provider": "openrouter"}

    with patch("tasks.daily_predictor.predict_daily_with_jev", new_callable=AsyncMock) as mock_jev:
        mock_jev.return_value = {
            "predicted_direction": "UP",
            "confidence": 74.0,
            "expected_return_pct": 0.0,
            "rationale": "Strong pre-market confirmation.",
            "catalysts": [],
        }
        direction, confidence, ret, _, _, _, min_conf = await _execute_model_daily_prediction(
            model_cfg,
            "SPY",
            "Monolithic text",
            {"ticker": "SPY", "target_date": "2026-10-09", "proxies": {}},
            "user",
            curated_payload,
            curated_payload,
        )

    assert direction == "UP"
    assert confidence == 74.0
    assert ret == 0.0
    assert min_conf == 61.0
    assert mock_jev.call_args.kwargs["model_name"] == JEV_MODEL


@pytest.mark.asyncio
async def test_jev_curated_executor_keeps_zero_abstention_contract():
    """Curated criteria never emit NO_TRADE: low confidence still commits to a direction."""
    from tasks.daily_predictor import _execute_model_daily_prediction

    curated_payload = json.dumps(
        {
            "criteria": {"UP": "Up rule", "DOWN": "Down rule"},
            "min_confidence": 0.0,
            "manifest": {"selected_newsletters": ["Sherwood News"]},
        }
    )
    model_cfg = {"name": "jev-four-regime-champion", "type": "jev_curated", "provider": "openrouter"}

    with patch("tasks.daily_predictor.predict_daily_with_jev", new_callable=AsyncMock) as mock_jev:
        mock_jev.return_value = {
            "predicted_direction": "UP",
            "confidence": 52.5,
            "expected_return_pct": 0.0,
            "rationale": "Borderline signal.",
            "catalysts": [],
        }
        direction, confidence, _, _, _, _, min_conf = await _execute_model_daily_prediction(
            model_cfg,
            "SPY",
            "Monolithic text",
            {"ticker": "SPY", "target_date": "2026-10-09", "proxies": {}},
            "user",
            curated_payload,
            curated_payload,
        )

    assert direction == "UP"
    assert direction != "NO_TRADE"
    assert confidence == 52.5
    assert min_conf == 0.0
