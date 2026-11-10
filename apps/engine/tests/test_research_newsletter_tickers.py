"""Hermetic unit tests for newsletter company research deep-dive generation and deduplication."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tasks.research_newsletter_tickers import (
    CompanyResearchDossierOutput,
    research_newsletter_targets,
    research_single_target,
)
from tasks.ticker_extractor import CompanyMention


class MockTableQuery:
    def __init__(self, data=None):
        self._data = data or []

    def select(self, *args, **kwargs):
        return self

    def eq(self, *args, **kwargs):
        return self

    def order(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def upsert(self, data, *args, **kwargs):
        if isinstance(data, list):
            self._data = data
        else:
            self._data = [data]
        return self

    def execute(self):
        res = MagicMock()
        res.data = self._data
        return res


@pytest.fixture
def mock_supabase():
    sb = MagicMock()
    tables = {
        "company_research_reports": MockTableQuery(),
        "newsletter_company_mentions": MockTableQuery(),
    }
    sb.table.side_effect = lambda name: tables.get(name, MockTableQuery())
    return sb


@pytest.mark.asyncio
async def test_smart_ttl_skips_llm_within_24h(mock_supabase):
    today_str = datetime.now(UTC).strftime("%Y-%m-%d")
    existing_report = {
        "id": "11111111-1111-1111-1111-111111111111",
        "ticker": "NVDA",
        "company_name": "NVIDIA Corp",
        "sector": "Semiconductors",
        "verdict": "bullish",
        "conviction_score": 85,
        "date": today_str,
        "session": "open",
        "created_at": f"{today_str}T09:15:00Z",
    }

    mock_reports_query = MockTableQuery([existing_report])
    mock_mentions_query = MockTableQuery()
    mock_supabase.table.side_effect = lambda name: {
        "company_research_reports": mock_reports_query,
        "newsletter_company_mentions": mock_mentions_query,
    }[name]

    mock_openai = MagicMock()

    mention = CompanyMention(
        ticker="NVDA",
        company_name="NVIDIA",
        sector="Semiconductors",
        is_sector_etf=False,
        entity_type="stock",
    )

    result = await research_single_target(
        mention=mention,
        session="close",
        newsletter_id="22222222-2222-2222-2222-222222222222",
        sb_client=mock_supabase,
        openai_client=mock_openai,
    )

    # Assert OpenAI was not called because fresh report exists within 24h
    mock_openai.chat.completions.create.assert_not_called()
    assert result["id"] == existing_report["id"]
    assert result["ticker"] == "NVDA"


@pytest.mark.asyncio
async def test_fresh_research_calls_gpt_luna_with_medium_reasoning(mock_supabase):
    today_str = datetime.now(UTC).strftime("%Y-%m-%d")

    # No existing report
    mock_reports_query = MockTableQuery([])
    mock_mentions_query = MockTableQuery()
    mock_supabase.table.side_effect = lambda name: {
        "company_research_reports": mock_reports_query,
        "newsletter_company_mentions": mock_mentions_query,
    }[name]

    mock_output = CompanyResearchDossierOutput(
        ticker="SMH",
        company_name="VanEck Semiconductor ETF",
        sector="Semiconductors",
        is_sector_etf=True,
        entity_type="etf",
        verdict="bullish",
        conviction_score=82,
        risk_reward_score=3.5,
        target_horizon="3-6 months",
        valuation_summary="Forward P/E of 28x with top constituent foundry capacity above 90%.",
        buffett_moat_analysis={"moat_rating": "Wide", "pricing_power": "High"},
        options_sentiment_summary="Call skew elevated; IV/RV ratio 1.15.",
        catalyst_context="Mentioned in morning briefing regarding AI CapEx acceleration.",
        falsification_triggers=["Hyperscaler CapEx guidance cuts below $180B."],
        full_report_markdown="# SMH Semiconductor Deep Dive\nDetailed dossier content...",
    )

    mock_openai = MagicMock()
    mock_openai.chat.completions.create = AsyncMock(return_value=mock_output)

    mention = CompanyMention(
        ticker="SMH",
        company_name="VanEck Semiconductor ETF",
        sector="Semiconductors",
        is_sector_etf=True,
        entity_type="etf",
        context_snippet="Semiconductors leading broad market rotation.",
    )

    with patch("tasks.research_newsletter_tickers.gather_target_context", new_callable=AsyncMock) as mock_ctx:
        mock_ctx.return_value = (150.0, "Key metrics and options data for SMH")

        result = await research_single_target(
            mention=mention,
            session="open",
            newsletter_id="33333333-3333-3333-3333-333333333333",
            sb_client=mock_supabase,
            openai_client=mock_openai,
            target_date=today_str,
        )

        assert mock_openai.chat.completions.create.called
        call_kwargs = mock_openai.chat.completions.create.call_args.kwargs
        # Verify reasoning_effort="medium" was explicitly passed as requested by user
        assert call_kwargs.get("reasoning_effort") == "medium"
        assert result["ticker"] == "SMH"
        assert result["verdict"] == "bullish"
        assert result["conviction_score"] == 82


@pytest.mark.asyncio
async def test_research_newsletter_targets_deduplicates_batch(mock_supabase):
    raw_mentions = [
        {"ticker": "NVDA", "company_name": "NVIDIA", "sector": "Semiconductors"},
        {"ticker": "$nvda", "company_name": "Nvidia Corp", "sector": "Semis"},
        {"ticker": "Semiconductors", "company_name": "Semis", "sector": "Semiconductors"},
    ]

    mock_reports_query = MockTableQuery([])
    mock_mentions_query = MockTableQuery()
    mock_supabase.table.side_effect = lambda name: {
        "company_research_reports": mock_reports_query,
        "newsletter_company_mentions": mock_mentions_query,
    }[name]

    mock_single_research = AsyncMock(side_effect=lambda mention, **kwargs: {"ticker": mention.ticker, "status": "ok"})

    with patch("tasks.research_newsletter_tickers.research_single_target", mock_single_research):
        results = await research_newsletter_targets(
            raw_mentions=raw_mentions,
            session="open",
            newsletter_id="44444444-4444-4444-4444-444444444444",
            sb_client=mock_supabase,
        )

        # 3 raw items (with duplicates and sector) must resolve to exactly 2 calls: NVDA and SMH
        assert len(results) == 2
        called_tickers = [c.kwargs["mention"].ticker for c in mock_single_research.call_args_list]
        assert called_tickers == ["NVDA", "SMH"]
