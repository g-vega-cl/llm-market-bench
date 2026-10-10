"""Unit tests for local_autoresearch.manifest."""

from apps.engine.local_autoresearch.manifest import (
    AutoresearchMutation,
    DataManifest,
    JevCriteriaConfig,
    format_jev_payload,
    pack_daily_context,
)


def test_manifest_defaults():
    manifest = DataManifest()
    assert manifest.include_synthetic_newsletter is True
    assert manifest.include_currency_uup is False
    assert manifest.include_options_derivatives is True
    assert "QQQ" in manifest.include_macro_proxies


def test_pack_daily_context_filters_newsletters_and_currency():
    day_record = {
        "target_date": "2026-10-09",
        "ticker": "SPY",
        "economic_calendar": "CPI YoY came at 2.4% vs 2.3% expected.",
        "synthetic_newsletter": "Synthetic Morning Wall St Briefing: Tech rally slows.",
        "newsletters": [
            {"sender": "The Kobeissi Letter", "subject": "Market Outlook", "content": "Rates at crossroad."},
            {"sender": "Morning Brew", "subject": "Morning Coffee", "content": "Retail sales update."},
            {"sender": "ZeroHedge Macro", "subject": "Overnight Liquidity", "content": "Repo spike alert."},
        ],
        "proxies": {
            "QQQ": {"price": 490.5, "change_pct": 0.45},
            "TLT": {"price": 94.2, "change_pct": -0.30},
            "UUP": {"price": 28.1, "change_pct": 0.20},
        },
        "options_sentiment": "SPY Max Pain at 575. Put/Call ratio 0.85.",
        "intraday_profile": "Prior day trend-up day with VWAP hold at 573.",
    }

    # Manifest with only Kobeissi Letter, currency disabled
    manifest = DataManifest(
        selected_newsletters=["The Kobeissi Letter"],
        include_currency_uup=False,
        include_macro_proxies=["QQQ", "TLT"],
    )

    context = pack_daily_context(day_record, manifest)

    assert "SPY (2026-10-09)" in context
    assert "The Kobeissi Letter" in context
    assert "Morning Brew" not in context
    assert "ZeroHedge" not in context
    assert "QQQ: $490.50 (+0.45%)" in context
    assert "UUP" not in context
    assert "Max Pain at 575" in context


def test_pack_daily_context_toggles_blocks():
    day_record = {
        "target_date": "2026-10-09",
        "ticker": "SPY",
        "options_sentiment": "Max Pain at 575",
        "market_barometer": "Health score 72/100",
        "market_feeling": "Bullish cautious",
    }

    manifest = DataManifest(
        include_synthetic_newsletter=False,
        include_options_derivatives=False,
        include_market_health_barometer=True,
        include_recent_market_feeling=True,
    )

    context = pack_daily_context(day_record, manifest)
    assert "Max Pain" not in context
    assert "Market Health Barometer" in context
    assert "Qualitative Market Feeling" in context


def test_format_jev_payload():
    criteria = JevCriteriaConfig(
        criteria_up="Hold above VWAP and positive gap follow-through.",
        criteria_down="Rejection at 580 resistance or bond yields surge.",
        min_confidence=60.0,
    )
    payload = format_jev_payload("Test Context", criteria, ticker="SPY")

    assert payload["model"] == "~typesafe/jev-latest"
    assert payload["state"]["ticker"] == "SPY"
    assert payload["state"]["market_context"] == "Test Context"
    assert payload["questions"]["direction"]["type"] == "choice"
    assert "Hold above VWAP" in payload["questions"]["direction"]["criteria"]["UP"]
    assert "Rejection at 580" in payload["questions"]["direction"]["criteria"]["DOWN"]


def test_autoresearch_mutation_schema():
    mutation = AutoresearchMutation(
        criteria=JevCriteriaConfig(
            criteria_up="VWAP hold",
            criteria_down="VWAP break",
            min_confidence=65.0,
        ),
        manifest=DataManifest(
            include_currency_uup=True,
            selected_newsletters=["Chartr", "Exec Sum"],
        ),
        hypothesis="Adding currency data and narrowing newsletters clarifies yield-sensitive regime.",
    )
    assert mutation.criteria.min_confidence == 65.0
    assert mutation.manifest.include_currency_uup is True
    assert "Chartr" in mutation.manifest.selected_newsletters
