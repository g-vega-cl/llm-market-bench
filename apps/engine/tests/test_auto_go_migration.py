"""Hermetic reproduction tests verifying migration of utility/homepage flows to auto-go."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml


def test_config_exposes_auto_go_defaults():
    from core import config

    assert config.AUTO_GO_MODEL == "auto-go"
    assert hasattr(config, "FREE_LLM_PROXY_URL")
    assert hasattr(config, "FREE_PROXY_MASTER_KEY")


def test_get_auto_go_client_configures_md_json_and_purpose():
    from core.llm.clients import get_auto_go_client

    with (
        patch("core.llm.clients.config.FREE_LLM_PROXY_URL", "https://llm.clvg.uk/v1"),
        patch("core.llm.clients.config.FREE_PROXY_MASTER_KEY", "test-proxy-key"),
        patch("core.llm.clients.AsyncOpenAI") as mock_openai,
        patch("core.llm.clients.instructor.from_openai") as mock_from_openai,
    ):
        get_auto_go_client(purpose="test-purpose")

        mock_openai.assert_called_once()
        kwargs = mock_openai.call_args.kwargs
        assert kwargs["api_key"] == "test-proxy-key"
        assert kwargs["base_url"] == "https://llm.clvg.uk/v1"
        assert kwargs["max_retries"] == 0
        assert kwargs["default_headers"] == {"X-Purpose": "test-purpose"}
        mock_from_openai.assert_called_once()


def test_get_auto_go_raw_client_requires_key_for_remote_proxy():
    from core.llm.clients import get_auto_go_raw_client

    with (
        patch("core.llm.clients.config.FREE_LLM_PROXY_URL", "https://llm.clvg.uk/v1"),
        patch("core.llm.clients.config.FREE_PROXY_MASTER_KEY", ""),
        pytest.raises(ValueError, match="FREE_PROXY_MASTER_KEY"),
    ):
        get_auto_go_raw_client()


@pytest.mark.asyncio
async def test_cleaner_uses_auto_go():
    from core.models import NewsletterCleaningResponse
    from ingest.cleaner import clean_newsletter_content

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(
        return_value=NewsletterCleaningResponse(
            cleaned_content="Fed holds rates steady.",
            ads_removed_count=1,
            ads_summary=["Promo"],
            is_pure_ad=False,
        )
    )

    with (
        patch("ingest.cleaner.clients.get_auto_go_client", return_value=mock_client) as mock_factory,
        patch("ingest.cleaner.clients.close_client", new_callable=AsyncMock),
    ):
        res = await clean_newsletter_content("Fed holds rates steady. Sponsor promo.")
        assert res == "Fed holds rates steady."
        mock_factory.assert_called_once()
        assert mock_client.chat.completions.create.call_args.kwargs["model"] == "auto-go"


@pytest.mark.asyncio
async def test_pre_filter_uses_auto_go():
    from analysis.pre_filter import NewsletterTriageItem, NewsletterTriageResponse, summarize_newsletters

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(
        return_value=NewsletterTriageResponse(
            summaries=[NewsletterTriageItem(source_id="src-1", summary="NVDA earnings beat.")]
        )
    )

    with (
        patch("analysis.pre_filter.clients.get_auto_go_client", return_value=mock_client) as mock_factory,
        patch("analysis.pre_filter.clients.close_client", new_callable=AsyncMock),
    ):
        res = await summarize_newsletters(
            [{"source_id": "src-1", "content": "NVDA beat.", "sender": "x", "subject": "y"}]
        )
        assert res == {"src-1": "NVDA earnings beat."}
        mock_factory.assert_called_once()
        assert mock_client.chat.completions.create.call_args.kwargs["model"] == "auto-go"


@pytest.mark.asyncio
async def test_calendar_pipeline_uses_auto_go():
    from core.models import DecisionsResponse
    from ingest.calendar import CalendarPipeline

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=DecisionsResponse(macro_events=[]))

    with (
        patch("ingest.calendar.get_auto_go_client", return_value=mock_client) as mock_factory,
        patch("ingest.calendar.get_supabase_client", return_value=MagicMock()),
        patch("ingest.calendar.close_client", new_callable=AsyncMock) as mock_close,
    ):
        pipe = CalendarPipeline()
        mock_factory.assert_called_once()
        with patch.object(
            pipe,
            "fetch_html",
            return_value=(
                '<table id="calendar"><tr><th colspan="6">Wednesday March 11 2026</th></tr>'
                '<tr data-event="CPI" data-country="united states">'
                "<td>10:00 AM</td><td>USA</td><td>CPI Data</td><td>3.2%</td><td>3.1%</td><td>3.0%</td>"
                "</tr></table>"
            ),
        ):
            await pipe.run()
        assert mock_client.chat.completions.create.call_args.kwargs["model"] == "auto-go"
        mock_close.assert_awaited_once_with(mock_client, "auto_go")


@pytest.mark.asyncio
async def test_government_pipeline_uses_auto_go():
    from core.models import DecisionsResponse
    from ingest.government import GovernmentPipeline

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=DecisionsResponse(macro_events=[]))

    with (
        patch("ingest.government.get_auto_go_client", return_value=mock_client) as mock_factory,
        patch("ingest.government.get_supabase_client", return_value=MagicMock()),
        patch("ingest.government.close_client", new_callable=AsyncMock) as mock_close,
    ):
        pipe = GovernmentPipeline()
        mock_factory.assert_called_once()
        with patch.object(pipe, "fetch_policy_grounding_context", new=AsyncMock(return_value="Verified FR text")):
            await pipe.extract_policy_memories()
        assert mock_client.chat.completions.create.call_args.kwargs["model"] == "auto-go"
        mock_close.assert_awaited_once_with(mock_client, "auto_go")


@pytest.mark.asyncio
async def test_post_analysis_uses_auto_go():
    from analysis.post_analysis import PostAnalysisResult, perform_post_analysis

    mock_sb = MagicMock()
    trade = {
        "id": "trade-1",
        "ticker": "AAPL",
        "quantity": 1,
        "price": 180.0,
        "signal": "BUY",
        "executed_at": (datetime.now(UTC) - timedelta(days=5)).isoformat(),
        "decisions": [{"reasoning": "Momentum", "model_name": "m1", "metadata": {}}],
    }
    mock_sb.table.return_value.select.return_value.filter.return_value.filter.return_value.execute.return_value.data = [
        trade
    ]
    mock_sb.table.return_value.select.return_value.filter.return_value.filter.return_value.filter.return_value.execute.return_value.data = []

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(
        return_value=PostAnalysisResult(lesson="Lesson", is_regret=False, sentiment_shift="Hold", importance_score=7)
    )
    mock_mdm = MagicMock()
    mock_mdm.get_quote = AsyncMock(return_value=MagicMock(price=185.0))

    with (
        patch("analysis.post_analysis.get_supabase_client", return_value=mock_sb),
        patch("analysis.post_analysis.get_auto_go_client", return_value=mock_client) as mock_factory,
        patch("analysis.post_analysis.MarketDataManager", return_value=mock_mdm),
        patch("analysis.post_analysis.add_memory", return_value=True),
        patch("analysis.post_analysis.close_client", new_callable=AsyncMock) as mock_close,
    ):
        await perform_post_analysis(windows=[5])
        mock_factory.assert_called_once()
        assert mock_client.chat.completions.create.call_args.kwargs["model"] == "auto-go"
        mock_close.assert_awaited_once_with(mock_client, "auto_go")


@pytest.mark.asyncio
async def test_cause_and_effect_and_earnings_ticker_tool_use_auto_go():
    from analysis.cause_and_effect_analysis import extract_related_tickers, perform_cause_and_effect_analysis
    from core.models import CauseAndEffectResult, TickerSuggestion
    from tools.earnings import execute_search_related_tickers_tool

    mock_ticker_client = MagicMock()
    mock_ticker_client.chat.completions.create = AsyncMock(
        return_value=TickerSuggestion(tickers=["NVDA"], reasoning="AI")
    )

    with (
        patch("analysis.cause_and_effect_analysis.get_auto_go_client", return_value=mock_ticker_client),
        patch("analysis.cause_and_effect_analysis.close_client", new_callable=AsyncMock),
    ):
        tickers = await extract_related_tickers("AI boom")
        assert tickers == ["NVDA"]
        assert mock_ticker_client.chat.completions.create.call_args.kwargs["model"] == "auto-go"

    mock_sb = MagicMock()
    event = {
        "id": "ev-1",
        "content": "AI capex surge",
        "created_at": (datetime.now(UTC) - timedelta(days=2)).isoformat(),
        "metadata": {},
    }
    mock_sb.table.return_value.select.return_value.filter.return_value.filter.return_value.execute.return_value.data = [
        event
    ]
    mock_sb.table.return_value.select.return_value.filter.return_value.execute.return_value.data = []

    mock_ce_client = MagicMock()
    mock_ce_client.chat.completions.create = AsyncMock(
        return_value=CauseAndEffectResult(
            analysis="Capex drove semis.", market_outcome="NVDA +5%", confidence=80, tags=["ai"]
        )
    )
    mock_mdm = MagicMock()
    mock_mdm.get_history = AsyncMock(
        return_value=[{"price": 105.0, "fetched_at": "2026-10-02"}, {"price": 100.0, "fetched_at": "2026-10-01"}]
    )

    with (
        patch("analysis.cause_and_effect_analysis.get_supabase_client", return_value=mock_sb),
        patch("analysis.cause_and_effect_analysis.get_auto_go_client", return_value=mock_ce_client),
        patch("analysis.cause_and_effect_analysis.MarketDataManager", return_value=mock_mdm),
        patch("analysis.cause_and_effect_analysis.find_similar_memory", return_value=None),
        patch("analysis.cause_and_effect_analysis.extract_related_tickers", new=AsyncMock(return_value=["NVDA"])),
        patch("analysis.cause_and_effect_analysis.close_client", new_callable=AsyncMock) as mock_close,
    ):
        await perform_cause_and_effect_analysis()
        assert mock_ce_client.chat.completions.create.call_args.kwargs["model"] == "auto-go"
        mock_close.assert_awaited_once_with(mock_ce_client, "auto_go")

    mock_tool_client = MagicMock()
    mock_tool_client.chat.completions.create = AsyncMock(
        return_value=TickerSuggestion(tickers=["AMD"], reasoning="Compute")
    )
    with patch("core.llm.clients.get_auto_go_client", return_value=mock_tool_client) as mock_factory:
        out = await execute_search_related_tickers_tool("AI chips")
        assert "AMD" in out
        mock_factory.assert_called_once()
        assert mock_tool_client.chat.completions.create.call_args.kwargs["model"] == "auto-go"


@pytest.mark.asyncio
async def test_memory_consolidation_rank_memories_and_audit_analyzer_use_auto_go():
    from core.audit.analyzer import analyze_log_blob, configure
    from memory.store import consolidate_overlapping_memories
    from scripts.rank_memories import ImportanceRanking, rank_existing_memories

    # 1. Memory consolidation
    mock_memories = [
        {
            "id": "m1",
            "content": "Fed cut",
            "embedding": [0.1, 0.2],
            "importance_score": 8,
            "memory_type": "MARKET_EVENT",
        },
        {
            "id": "m2",
            "content": "Fed cut 25bps",
            "embedding": [0.1, 0.2],
            "importance_score": 8,
            "memory_type": "MARKET_EVENT",
        },
    ]
    mock_sb = MagicMock()
    mock_sb.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = mock_memories
    mock_cons_client = MagicMock()
    mock_cons_client.chat.completions.create = AsyncMock(
        return_value=MagicMock(headline="Fed cut", summary="25bps", importance_score=8, memory_type="MARKET_EVENT")
    )
    with (
        patch("memory.store.get_supabase_client", return_value=mock_sb),
        patch("core.llm.get_auto_go_client", return_value=mock_cons_client) as mock_factory,
        patch("analysis.consensus.cosine_similarity", return_value=0.95),
        patch("memory.store.add_memory", return_value="m3"),
    ):
        await consolidate_overlapping_memories()
        mock_factory.assert_called_once()
        assert mock_cons_client.chat.completions.create.call_args.kwargs["model"] == "auto-go"

    # 2. rank_memories
    mock_rank_sb = MagicMock()
    mock_rank_sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"id": "mem-1", "content": "FOMC held rates", "metadata": {}}
    ]
    mock_rank_client = MagicMock()
    mock_rank_client.chat.completions.create = AsyncMock(
        return_value=ImportanceRanking(importance_score=9, reasoning="Central bank decision")
    )
    with (
        patch("scripts.rank_memories.get_supabase_client", return_value=mock_rank_sb),
        patch("scripts.rank_memories.get_auto_go_client", return_value=mock_rank_client) as mock_rank_factory,
    ):
        await rank_existing_memories()
        mock_rank_factory.assert_called_once()
        assert mock_rank_client.chat.completions.create.call_args.kwargs["model"] == "auto-go"

    # 3. Audit analyzer
    configure("proxy-key-123")
    mock_raw_client = MagicMock()
    mock_raw_client.chat.completions.create = AsyncMock(
        return_value=MagicMock(choices=[MagicMock(message=MagicMock(content=json.dumps([])))])
    )
    mock_raw_client.close = AsyncMock()
    try:
        with patch("core.audit.analyzer.get_auto_go_raw_client", return_value=mock_raw_client) as mock_raw_factory:
            res = await analyze_log_blob("sample logs")
            assert res == "[]"
            mock_raw_factory.assert_called_once()
            assert mock_raw_client.chat.completions.create.call_args.kwargs["model"] == "auto-go"
            mock_raw_client.close.assert_awaited_once()
    finally:
        configure(None)


@pytest.mark.asyncio
async def test_policy_lookup_remains_on_gemini_with_google_search():
    from core.llm.policy_lookup import lookup_policy

    mock_genai_client = MagicMock()
    mock_genai_client.aio.models.generate_content = AsyncMock(
        return_value=MagicMock(
            text=json.dumps(
                {
                    "policy_name": "CHIPS Act",
                    "status": "signed into law",
                    "description": "Semiconductor subsidies.",
                    "confidence": 95,
                }
            )
        )
    )
    with patch("core.llm.policy_lookup.genai.Client", return_value=mock_genai_client):
        res = await lookup_policy("semiconductor manufacturing subsidies")
        assert res is not None
        assert res.policy_name == "CHIPS Act"
        call_kwargs = mock_genai_client.aio.models.generate_content.call_args.kwargs
        assert call_kwargs["model"] != "auto-go"
        assert call_kwargs["config"].tools


def test_ci_workflows_inject_free_proxy_secrets():
    root = Path(__file__).resolve().parent.parent.parent.parent
    workflow_steps = [
        ("ingest.yml", "Run ingestion & consensus pipeline"),
        ("weekend-ingest.yml", "Run weekend ingestion pipeline"),
        ("generate-newsletter.yml", "Run Newsletter Generator"),
        ("generate-newsletter.yml", "Research Newsletter Mentioned Companies"),
        ("calendar.yml", "Run Calendar Ingestion"),
        ("update-earnings-alpha.yml", "Run earnings alpha and bellwether update script"),
        ("post-analysis.yml", "Run post-analysis pipeline"),
        ("cause-and-effect.yml", "Run Cause & Effect Analysis"),
        ("audit.yml", "Run system audit"),
        ("audit.yml", "Cleanup old records"),
        ("autoresearch.yml", "Run auto-research cycle"),
        ("daily-predictor.yml", "Run Daily Predictor Command"),
        ("daily-predictor.yml", "Run Daily TLT Bond Predictor"),
        ("daily-predictor.yml", "Run Day-1 Earnings Movement Predictor"),
        ("daily-predictor.yml", "Run Daily Stock Picker Arena (3 Up, 3 Down)"),
        ("frontier-tech.yml", "Execute Frontier Tech Supercycle Task"),
        ("future-forces.yml", "Execute Future Forces Task"),
    ]
    for wf_name, step_name in workflow_steps:
        wf_path = root / ".github" / "workflows" / wf_name
        data = yaml.safe_load(wf_path.read_text())
        all_steps = [s for job in data["jobs"].values() for s in job.get("steps", [])]
        step = next((s for s in all_steps if s.get("name") == step_name), None)
        assert step is not None, f"Missing step {step_name} in {wf_name}"
        env = step.get("env", {})
        assert env.get("FREE_PROXY_MASTER_KEY") == "${{ secrets.FREE_PROXY_MASTER_KEY }}", (
            f"{wf_name} -> {step_name} missing FREE_PROXY_MASTER_KEY"
        )
        assert env.get("FREE_LLM_PROXY_URL") == "${{ secrets.FREE_LLM_PROXY_URL }}", (
            f"{wf_name} -> {step_name} missing FREE_LLM_PROXY_URL"
        )


@pytest.mark.asyncio
async def test_synthesize_recent_news_avoids_800_token_truncation():
    from trading import runner

    mock_sb = MagicMock()
    mock_sb.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[{"source": "Reuters", "headline": "Fed flags sticky inflation; semis await NVDA"}]
    )
    mock_sb.table.return_value.select.return_value.order.return_value.limit.return_value.execute.return_value = (
        MagicMock(data=[{"id": "feeling-1"}])
    )

    with patch(
        "trading.runner.query_multi_tier_llm", new_callable=AsyncMock, return_value="Concise summary."
    ) as mock_llm:
        result = await runner.synthesize_recent_news(sb_client=mock_sb)

    assert result == "Concise summary."
    assert mock_llm.call_args.kwargs["max_tokens"] >= 2048


@pytest.mark.asyncio
async def test_cleaner_handles_client_init_error_gracefully():
    from ingest.cleaner import clean_newsletter_content

    original = "Important market content here."
    with patch(
        "ingest.cleaner.clients.get_auto_go_client",
        side_effect=ValueError("FREE_PROXY_MASTER_KEY is required"),
    ):
        result = await clean_newsletter_content(original)

    assert str(result) == original
    assert result.ads_removed_count == 0
