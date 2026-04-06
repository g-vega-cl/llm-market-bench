"""Cause and Effect Analysis Service.

This module analyzes past market events to understand their actual impact
on the market, creating a historical library of cause-and-effect relationships.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Any

from core.config import logger, GEMINI_MODEL
from core.db import get_supabase_client
from core.llm import get_gemini_client
from core.llm.prompt_factory import PromptFactory
from core.models import CauseAndEffectResult, TickerSuggestion
from execution.market_data import MarketDataManager
from memory.store import find_similar_memory

async def extract_related_tickers(event_summary: str) -> list[str]:
    """Uses LLM to suggest relevant tickers for an event."""
    client = get_gemini_client()
    try:
        messages = PromptFactory.build_ticker_suggestion_messages(
            provider="gemini",
            event_summary=event_summary
        )
        resp = client.chat.completions.create(
            model=GEMINI_MODEL,
            response_model=TickerSuggestion,
            messages=messages
        )
        # Handle instructor's potential sync/async return
        import asyncio
        if asyncio.iscoroutine(resp):
            resp = await resp
            
        logger.info(f"LLM suggested tickers for event: {resp.tickers} ({resp.reasoning})")
        return resp.tickers
    except Exception as e:
        logger.error(f"Failed to suggest tickers: {e}")
        return []

async def perform_cause_and_effect_analysis():
    """Analyzes recent market events and their impact."""
    logger.info("Starting Cause & Effect Analysis...")
    sb_client = get_supabase_client()
    mdm = MarketDataManager()
    client = get_gemini_client()

    # 1. Fetch recent unresolved MARKET_EVENT memories
    # We look for events that are older than 24h OR have passed their target_date
    now = datetime.now(timezone.utc)
    one_day_ago = (now - timedelta(days=1)).isoformat()

    res = sb_client.table("memories").select(
        "id, content, metadata, created_at, target_date"
    ).filter("memory_type", "eq", "MARKET_EVENT").filter("created_at", "lt", one_day_ago).execute()

    events = res.data if res.data else []
    if not events:
        logger.info("No mature market events found for cause & effect analysis.")
        return

    logger.info(f"Analyzing {len(events)} events for causal impact...")

    for event in events:
        event_id = event["id"]
        content = event["content"]
        meta = event.get("metadata", {})
        scenario_analysis = meta.get("scenario_analysis", "None provided.")
        created_at = datetime.fromisoformat(event["created_at"])
        
        # 2. Check if analysis already exists (exact ID or semantic similarity)
        existing = sb_client.table("cause_and_effect").select("id").filter("event_id", "eq", event_id).execute()
        if existing.data:
            logger.debug(f"Skipping event {event_id}: Analysis already exists (exact).")
            continue
        
        # Semantic deduplication: check if a very similar event was already analyzed
        # We look back 7 days to avoid repeating the same market narrative analysis.
        # Use a slightly lower threshold (0.85) to catch 'really similar' events as requested.
        similar_event_id = find_similar_memory(content, threshold=0.85, hours=168)
        if similar_event_id:
            # Check if THIS similar event already has a cause_and_effect entry
            existing_similar = sb_client.table("cause_and_effect").select("id").filter("event_id", "eq", similar_event_id).execute()
            if existing_similar.data:
                logger.info(f"Skipping event {event_id}: Semantic duplicate of {similar_event_id} already analyzed.")
                continue
            else:
                # Even if no analysis exists, we might want to skip if it's a near-duplicate 
                # but for Cause & Effect we need at least ONE analysis per narrative.
                # So we only skip if the existing one HAS analysis.
                pass

        # Dynamic Ticker Discovery: Find which stocks moved because of this
        suggested_tickers = await extract_related_tickers(content)
        
        # Priority: Suggested Tickers > Benchmarks
        # We include benchmarks as a secondary comparison point
        tickers_to_check = list(set(suggested_tickers)) if suggested_tickers else []
        
        # Only add benchmarks if we have room or if no specific tickers found
        benchmarks = ["SPY", "QQQ"]
        for b in benchmarks:
            if b not in tickers_to_check:
                tickers_to_check.append(b)
                
        # Limit to top 5 tickers to keep context manageable but granular
        tickers_to_check = tickers_to_check[:5]
        TICKER_BLACKLIST = {"EVENT", "AI", "US", "A", "THE", "AND", "MARKET", "GDP", "CPI", "FDA", "SEC", "FED"}
        
        # Extract tickers from content if possible (regex for 1-5 uppercase letters)
        import re
        content_tickers = re.findall(r'\b[A-Z]{1,5}\b', content)
        filtered_tickers = [t for t in content_tickers if t not in TICKER_BLACKLIST]
        
        tickers_to_check.extend(filtered_tickers)
        tickers_to_check = list(set(tickers_to_check))

        performance_text = ""
        market_context = []
        for ticker in tickers_to_check:
            # get_history returns a list of dicts with 'price' and 'fetched_at'
            # ordered by fetched_at DESC (newest first)
            history = await mdm.get_history(ticker, days=14)
            if history and len(history) >= 2:
                # get_history returns newest first, so history[0] is latest, history[-1] is oldest
                start_price = history[-1]["price"]
                end_price = history[0]["price"]
                change = ((end_price - start_price) / start_price) * 100
                market_context.append(f"{ticker}: {change:+.2f}% (${start_price:.2f} -> ${end_price:.2f})")

        performance_text = "\n".join(market_context) if market_context else "No specific market data available."

        # 4. Generate Analysis via LLM
        messages = PromptFactory.build_cause_effect_messages(
            provider="gemini",
            event_name=content[:100], # Use first 100 chars as name if none
            event_summary=content,
            scenario_analysis=scenario_analysis,
            market_performance=performance_text
        )

        try:
            # Gemini client from instructor.from_genai is synchronous
            create_call = client.chat.completions.create(
                model=GEMINI_MODEL,
                response_model=CauseAndEffectResult,
                messages=messages
            )
            
            import asyncio
            if asyncio.iscoroutine(create_call):
                resp = await create_call
            else:
                resp = create_call

            # 5. Save to database
            sb_client.table("cause_and_effect").insert({
                "event_id": event_id,
                "analysis": resp.analysis,
                "market_outcome": resp.market_outcome,
                "confidence": resp.confidence,
                "tags": resp.tags
            }).execute()

            logger.info(f"Generated cause & effect entry for event {event_id}. Outcome: {resp.market_outcome}")

        except Exception as e:
            logger.error(f"Failed to generate cause & effect analysis for event {event_id}: {e}")

    logger.info("Cause & Effect Analysis complete.")
