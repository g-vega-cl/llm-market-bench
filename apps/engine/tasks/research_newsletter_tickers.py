"""Asynchronous task for generating institutional-grade company/sector research dossiers from newsletter mentions."""

import asyncio
import json
import logging
import os
import time
from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field

from core.config import OPENAI_MODEL
from core.db import get_supabase_client
from core.llm.clients import get_openai_json_client
from execution.market_data import MarketDataManager
from tasks.ticker_extractor import CompanyMention, extract_and_deduplicate_mentions
from tools.analyst_personas import execute_call_warren_buffett_tool
from tools.technicals_options import execute_get_options_sentiment_tool
from tools.valuation import execute_key_metrics_tool, execute_sector_fundamentals_tool

logger = logging.getLogger("engine")

TTL_SKIP_HOURS = 24
TTL_WARM_DAYS = 7

# Uses Mode.JSON so gpt-5.6-luna can run with reasoning_effort="medium" without 400 tool conflict
get_research_openai_client = get_openai_json_client


class CompanyResearchDossierOutput(BaseModel):
    """Structured response model for an individual company or sector research dossier."""

    ticker: str = Field(description="Normalized ticker symbol uppercase.")
    company_name: str = Field(description="Full company or ETF name.")
    sector: str = Field(description="Industry or sector name.")
    is_sector_etf: bool = Field(default=False)
    entity_type: str = Field(default="stock", description="'stock' or 'etf'")
    verdict: str = Field(description="'bullish', 'bearish', or 'neutral'")
    conviction_score: int = Field(description="1 to 100 conviction score")
    risk_reward_score: float = Field(description="Estimated risk to reward ratio (e.g. 3.2)")
    target_horizon: str = Field(description="Target time horizon, e.g., '1-3 months', '3-6 months'")
    valuation_summary: str = Field(description="Summary of fundamental multiples, DCF fair value, margins, and growth.")
    buffett_moat_analysis: dict[str, Any] = Field(
        default_factory=dict,
        description="Dict with moat_rating ('Wide'/'Narrow'/'None'), pricing_power, capital_allocation, and rationale.",
    )
    options_sentiment_summary: str = Field(description="Options sentiment, skew, and IV regime summary.")
    catalyst_context: str = Field(
        description="The catalyst or news event that prompted this research from the briefing."
    )
    falsification_triggers: list[str] = Field(
        default_factory=list,
        description="3-5 concrete testable events/metrics that invalidate this thesis.",
    )
    full_report_markdown: str = Field(description="Full institutional-grade research dossier formatted in Markdown.")


async def gather_target_context(
    ticker: str,
    is_sector_etf: bool = False,
    session: str = "close",
    target_date: str | None = None,
    mdm: MarketDataManager | None = None,
) -> tuple[float | None, str]:
    """Gather live multi-dimensional context for the target stock or sector ETF."""
    manager = mdm or MarketDataManager()
    spot_price: float | None = None

    try:
        quote = await manager.get_reference_quote(ticker, session=session, target_date=target_date)
        spot_price = float(quote.get("price")) if quote and quote.get("price") is not None else None
    except Exception as e:
        logger.debug(f"Could not fetch reference quote for {ticker}: {e}")

    context_parts: list[str] = []

    # 1. Valuation / Key Metrics
    try:
        metrics = await execute_key_metrics_tool(ticker, period="annual", limit=2)
        if metrics and not metrics.startswith("Error"):
            context_parts.append(f"### Fundamental Key Metrics\n{metrics}")
    except Exception as e:
        logger.debug(f"Key metrics fetch failed for {ticker}: {e}")

    # 2. Moat / Warren Buffett Analysis (for single stocks) or Sector Fundamentals (for ETFs)
    if is_sector_etf:
        try:
            sector_data = await execute_sector_fundamentals_tool(limit=11)
            if sector_data and not sector_data.startswith("Error"):
                context_parts.append(f"### Sector Fundamentals\n{sector_data}")
        except Exception as e:
            logger.debug(f"Sector fundamentals fetch failed for {ticker}: {e}")
    else:
        try:
            buffett_data = await execute_call_warren_buffett_tool(ticker)
            if buffett_data and not buffett_data.startswith("Error"):
                context_parts.append(f"### Warren Buffett Moat & Quality Audit\n{buffett_data}")
        except Exception as e:
            logger.debug(f"Warren Buffett tool failed for {ticker}: {e}")

    # 3. Options Sentiment & Surface
    try:
        options_data = await execute_get_options_sentiment_tool(ticker)
        if options_data and not options_data.startswith("Error"):
            context_parts.append(f"### Options Sentiment & Volatility\n{options_data}")
    except Exception as e:
        logger.debug(f"Options sentiment failed for {ticker}: {e}")

    combined_context = "\n\n".join(context_parts) if context_parts else "No detailed metrics available."
    return spot_price, combined_context


async def research_single_target(
    mention: CompanyMention,
    session: str,
    newsletter_id: str | None = None,
    sb_client: Any | None = None,
    openai_client: Any | None = None,
    target_date: str | None = None,
    force_refresh: bool = False,
) -> dict[str, Any]:
    """Evaluates a single company or sector mention, applying smart TTL deduplication and OpenAI Luna with thinking."""
    sb = sb_client or get_supabase_client()
    effective_date = target_date or datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d")

    # 1. Check existing reports for Smart TTL Deduplication
    if not force_refresh:
        try:
            res = (
                sb.table("company_research_reports")
                .select("*")
                .eq("ticker", mention.ticker)
                .order("date", desc=True)
                .limit(1)
                .execute()
            )
            existing_rows = res.data or []
            if existing_rows:
                latest_report = existing_rows[0]
                created_dt_str = latest_report.get("created_at") or f"{latest_report.get('date')}T00:00:00Z"
                try:
                    report_time = datetime.fromisoformat(created_dt_str.replace("Z", "+00:00"))
                except Exception:
                    report_time = datetime.now(UTC)

                age = datetime.now(UTC) - report_time
                if age < timedelta(hours=TTL_SKIP_HOURS):
                    logger.info(
                        f"Smart TTL: {mention.ticker} researched {age.total_seconds() / 3600:.1f}h ago. "
                        f"Reusing existing report {latest_report['id']}."
                    )
                    # Link new newsletter mention if provided
                    if newsletter_id:
                        mention_payload = {
                            "newsletter_id": newsletter_id,
                            "ticker": mention.ticker,
                            "research_report_id": latest_report["id"],
                        }
                        sb.table("newsletter_company_mentions").upsert(
                            mention_payload, on_conflict="newsletter_id,ticker"
                        ).execute()
                    return latest_report
        except Exception as e:
            logger.warning(f"Could not check existing research report for {mention.ticker}: {e}")

    # 2. Gather live context
    spot_price, live_context = await gather_target_context(
        ticker=mention.ticker,
        is_sector_etf=mention.is_sector_etf,
        session=session,
        target_date=target_date,
    )

    # 3. Prompt GPT-5.6 Luna with thinking (reasoning_effort="medium")
    price_str = f"${spot_price:.2f}" if spot_price is not None else "N/A"
    prompt = (
        f"Target: {mention.company_name} ({mention.ticker})\n"
        f"Entity Type: {'Sector Benchmark ETF' if mention.is_sector_etf else 'Single Stock Equity'}\n"
        f"Sector / Industry: {mention.sector or 'Unspecified'}\n"
        f"Spot Price: {price_str}\n"
        f"Newsletter Context: {mention.context_snippet or 'Featured in daily market briefing spotlight.'}\n\n"
        f"### Live Fundamentals & Market Context:\n{live_context}\n\n"
        "Instructions:\n"
        "1. Conduct a rigorous institutional-grade deep dive. Determine whether it is worth investing in.\n"
        "2. Deliver a clear, definitive verdict: 'bullish', 'bearish', or 'neutral' with a conviction score (1-100).\n"
        "3. Provide valuation appraisal (DCF/multiples), Buffett economic moat check, and options volatility skew.\n"
        "4. Define 3-5 concrete falsification triggers that would invalidate the investment thesis.\n"
        "5. Output complete Markdown formatted dossier under `full_report_markdown`."
    )

    client = openai_client or get_research_openai_client()
    target_model = OPENAI_MODEL
    kwargs: dict[str, Any] = {"reasoning_effort": "medium"}

    dossier: CompanyResearchDossierOutput = await client.chat.completions.create(
        model=target_model,
        response_model=CompanyResearchDossierOutput,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are Benchify's chief equity research analyst producing institutional deep-dive dossiers. "
                    "You evaluate fundamentals, economic moats, and volatility surfaces to render decisive verdicts."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        **kwargs,
    )

    # 4. Save to database
    payload = {
        "ticker": dossier.ticker,
        "company_name": dossier.company_name,
        "sector": dossier.sector,
        "is_sector_etf": dossier.is_sector_etf,
        "entity_type": dossier.entity_type,
        "session": session,
        "date": effective_date,
        "verdict": dossier.verdict.lower(),
        "conviction_score": max(1, min(100, dossier.conviction_score)),
        "risk_reward_score": (
            round(max(0.1, min(99.0, float(dossier.risk_reward_score))), 1)
            if dossier.risk_reward_score is not None
            else None
        ),
        "target_horizon": dossier.target_horizon,
        "spot_price_at_report": spot_price,
        "valuation_summary": dossier.valuation_summary,
        "buffett_moat_analysis": dossier.buffett_moat_analysis,
        "options_sentiment_summary": dossier.options_sentiment_summary,
        "catalyst_context": dossier.catalyst_context,
        "falsification_triggers": dossier.falsification_triggers,
        "full_report_markdown": dossier.full_report_markdown,
    }

    try:
        report_res = sb.table("company_research_reports").upsert(payload, on_conflict="ticker,date,session").execute()
        saved_row = report_res.data[0] if report_res.data else payload
    except Exception as e:
        logger.exception(f"Failed to upsert company research report for {mention.ticker}: {e}")
        saved_row = payload

    report_id = saved_row.get("id")
    if newsletter_id and report_id:
        try:
            mention_payload = {
                "newsletter_id": newsletter_id,
                "ticker": mention.ticker,
                "research_report_id": report_id,
            }
            sb.table("newsletter_company_mentions").upsert(
                mention_payload, on_conflict="newsletter_id,ticker"
            ).execute()
        except Exception as e:
            logger.warning(f"Could not link newsletter mention for {mention.ticker}: {e}")

    return saved_row


async def research_newsletter_targets(
    raw_mentions: list[dict[str, Any]],
    session: str,
    newsletter_id: str | None = None,
    text_fallback: str | None = None,
    sb_client: Any | None = None,
    target_date: str | None = None,
    force_refresh: bool = False,
) -> list[dict[str, Any]]:
    """Deduplicates mentions and generates research dossiers for all unique targets."""
    deduped_targets = extract_and_deduplicate_mentions(raw_mentions, text_fallback=text_fallback)
    if not deduped_targets:
        logger.info("No company or sector targets extracted to research.")
        return []

    logger.info(f"Researching {len(deduped_targets)} unique targets from newsletter session '{session}'...")
    sem = asyncio.Semaphore(3)

    async def _bounded_research(target: CompanyMention) -> dict[str, Any] | None:
        async with sem:
            try:
                return await research_single_target(
                    mention=target,
                    session=session,
                    newsletter_id=newsletter_id,
                    sb_client=sb_client,
                    target_date=target_date,
                    force_refresh=force_refresh,
                )
            except Exception as e:
                logger.exception(f"Error researching target {target.ticker}: {e}")
                return None

    tasks = [_bounded_research(target) for target in deduped_targets]
    raw_results = await asyncio.gather(*tasks)
    return [r for r in raw_results if r is not None]


async def research_latest_newsletter(
    session: str = "open",
    target_date: str | None = None,
    sb_client: Any | None = None,
    force_refresh: bool = False,
) -> list[dict[str, Any]]:
    """Researches targets from the latest generated newsletter for the specified session.

    First attempts to read the handoff file written by generate_daily_newsletter (/tmp/latest_newsletter_{session}.json),
    falling back to querying the latest generated_newsletters row from Supabase.
    """
    sb = sb_client or get_supabase_client()
    newsletter_id: str | None = None
    raw_mentions: list[dict[str, Any]] = []
    content: str | None = None

    handoff_path = f"/tmp/latest_newsletter_{session}.json"
    if os.path.exists(handoff_path):
        try:
            with open(handoff_path) as f:
                data = json.load(f)
            file_matches_session = data.get("session") == session
            if target_date:
                file_matches_date = data.get("target_date") == target_date
            else:
                # Require handoff file to be younger than 4 hours for live runs
                file_matches_date = (time.time() - os.path.getmtime(handoff_path)) < 14400

            if file_matches_session and file_matches_date:
                newsletter_id = data.get("newsletter_id")
                raw_mentions = data.get("mentioned_companies") or []
                content = data.get("content")
                logger.info(f"Loaded newsletter handoff for session '{session}' (ID: {newsletter_id})")
        except Exception as e:
            logger.warning(f"Failed to read newsletter handoff file {handoff_path}: {e}")

    if not newsletter_id or not content:
        try:
            query = sb.table("generated_newsletters").select("id, title, content, created_at").eq("session", session)
            if target_date:
                query = query.gte("created_at", f"{target_date}T00:00:00Z").lte(
                    "created_at", f"{target_date}T23:59:59Z"
                )
            res = query.order("created_at", desc=True).limit(1).execute()
            rows = res.data or []
            if rows:
                latest = rows[0]
                newsletter_id = latest.get("id")
                content = latest.get("content")
                logger.info(f"Fetched latest newsletter from database for session '{session}' (ID: {newsletter_id})")
        except Exception as e:
            logger.warning(f"Could not fetch latest newsletter from DB for session '{session}': {e}")

    if not content:
        logger.warning(f"No generated newsletter found for session '{session}' to research.")
        return []

    return await research_newsletter_targets(
        raw_mentions=raw_mentions,
        session=session,
        newsletter_id=newsletter_id,
        text_fallback=content,
        sb_client=sb,
        target_date=target_date,
        force_refresh=force_refresh,
    )
