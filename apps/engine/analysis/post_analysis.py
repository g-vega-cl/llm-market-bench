"""Continuous Post-Analysis Logic.

This module analyzes past trades at multiple intervals (5, 14, 30 days)
against actual price performance to generate 'lessons learned' for long-term memory.
"""

import asyncio
from datetime import UTC, datetime, timedelta

from pydantic import BaseModel, Field

from core.config import GEMINI_MODEL, logger
from core.db import get_supabase_client
from core.llm import get_gemini_client
from core.llm.prompt_factory import PromptFactory
from execution.market_data import MarketDataManager
from memory.store import add_memory


class PostAnalysisResult(BaseModel):
    lesson: str = Field(..., description="A concise lesson learned")
    is_regret: bool = Field(..., description="Whether the trade was a mistake")
    sentiment_shift: str = Field(..., description="How to adjust view on this ticker/sector")


async def perform_post_analysis(windows: list[int] = None):
    """Analyzes trades from specific intervals ago and generates self-corrective memories.

    Args:
        windows: List of days-back intervals to evaluate trade performance.
    """
    if windows is None:
        windows = [5, 14, 30]
    logger.info(f"Starting Post-Analysis for windows: {windows} days ago...")
    sb_client = get_supabase_client()
    mdm = MarketDataManager()

    # Use Gemini Flash 3 as the Manager Agent
    client = get_gemini_client()

    for days_back in windows:
        # 1. Fetch trades from the target window
        target_date = (datetime.now(UTC) - timedelta(days=days_back)).date()
        start_time = datetime.combine(target_date, datetime.min.time()).isoformat()
        end_time = datetime.combine(target_date, datetime.max.time()).isoformat()

        logger.info(f"Checking window: {days_back} days ago ({target_date})...")

        # Join with decisions to get reasoning
        res = (
            sb_client.table("trades")
            .select("id, ticker, quantity, price, signal, executed_at, decisions(reasoning, model_name, metadata)")
            .filter("executed_at", "gte", start_time)
            .filter("executed_at", "lte", end_time)
            .execute()
        )

        trades = res.data if res.data else []
        if not trades:
            logger.info(f"No trades found for post-analysis on {target_date}.")
            continue

        logger.info(f"Analyzing {len(trades)} trades for window {days_back}d...")

        for trade in trades:
            ticker = trade["ticker"]
            entry_price = trade["price"]
            signal = trade["signal"]
            decision_data = trade.get("decisions", [{}])[0] if trade.get("decisions") else {}
            reasoning = decision_data.get("reasoning", "No reasoning found.")
            model_name = decision_data.get("model_name", "Unknown")
            meta = decision_data.get("metadata", {})
            strategy_reasoning = meta.get("strategy_reasoning", "None")

            # 3. Check for existing post-analysis lesson FOR THIS SPECIFIC WINDOW
            existing_memory = (
                sb_client.table("memories")
                .select("id")
                .filter("metadata->>trade_id", "eq", str(trade["id"]))
                .filter("metadata->>analysis_window", "eq", str(days_back))
                .filter("memory_type", "eq", "POST_MORTEM")
                .execute()
            )

            if existing_memory.data:
                logger.debug(
                    f"Skipping trade {trade['id']} ({ticker}) for {days_back}d window: Analysis already exists."
                )
                continue

            # 4. Get current price
            quote = await mdm.get_quote(ticker)
            if not quote:
                continue

            current_price = quote.price
            price_change_pct = ((current_price - entry_price) / entry_price) * 100
            if signal.upper() == "SELL":
                price_change_pct = -price_change_pct

            try:
                messages = PromptFactory.build_manager_messages(
                    provider="gemini",
                    ticker=ticker,
                    signal=signal,
                    entry_price=entry_price,
                    current_price=current_price,
                    price_change_pct=price_change_pct,
                    reasoning=reasoning,
                    strategy_reasoning=strategy_reasoning,
                )

                # Use a modified system prompt or context if it's a longer term window
                # For now, using same templates but adding window context in the lesson content
                for msg in messages:
                    if msg["role"] == "user":
                        msg["content"] = f"[WINDOW: {days_back} DAYS] " + msg["content"]

                resp_awaitable = client.chat.completions.create(
                    model=GEMINI_MODEL, response_model=PostAnalysisResult, messages=messages
                )

                if hasattr(resp_awaitable, "__await__") or asyncio.iscoroutine(resp_awaitable):
                    resp = await resp_awaitable
                else:
                    resp = resp_awaitable

                # 6. Inject into Memory
                memory_content = (
                    f"{days_back}-DAY POST-ANALYSIS ({ticker}): {resp.lesson} | "
                    f"ORIGINAL TRADE: {signal} @ ${entry_price:.2f} | "
                    f"OUTCOME: {price_change_pct:.2f}% | "
                    f"ADVICE: {resp.sentiment_shift}"
                )

                success = add_memory(
                    content=memory_content,
                    memory_type="POST_MORTEM",
                    metadata={
                        "price_change_pct": price_change_pct,
                        "trade_id": str(trade["id"]),
                        "analysis_window": str(days_back),
                        "model_name": model_name,
                    },
                    check_similarity=True,
                )

                if success:
                    logger.info(f"Generated {days_back}d post-analysis memory for {ticker}. Lesson: {resp.lesson}")

            except Exception as e:
                logger.error(f"Post-analysis failed for trade {trade['id']} ({ticker}) in {days_back}d window: {e}")

    logger.info("Post-Analysis processing complete.")
