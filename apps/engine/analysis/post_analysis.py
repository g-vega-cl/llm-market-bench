"""Continuous Post-Analysis Logic.

This module analyzes past trades at multiple intervals (5, 14, 30 days)
against actual price performance to generate 'lessons learned' for long-term memory.
"""

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

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
    importance_score: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Rating from 1-10 on lesson significance or blunder severity (1=minor noise, 5=standard outcome, 8-10=critical blunder/breakthrough)",
    )


def _resolve_trade_context(trade: dict[str, Any]) -> tuple[str, str, str]:
    """Resolve (model_name, reasoning, strategy_reasoning) from a trade row."""
    decision_data = trade.get("decisions", [{}])[0] if trade.get("decisions") else {}
    reasoning = decision_data.get("reasoning") or trade.get("reasoning") or "No reasoning found."

    portfolio_owner = (trade.get("portfolios") or {}).get("owner_id")
    dec_model = decision_data.get("model_name")
    if dec_model and dec_model.strip().lower() != "unknown":
        model_name = dec_model.strip()
    elif portfolio_owner and portfolio_owner.strip().lower() != "unknown":
        model_name = portfolio_owner.strip()
    else:
        model_name = "system"

    meta = decision_data.get("metadata", {}) or {}
    strategy_reasoning = meta.get("strategy_reasoning") or trade.get("reasoning") or "None"
    return model_name, reasoning, strategy_reasoning


def _extract_importance_score(raw_score: Any) -> int:
    """Safely bound and cast an importance score to the 1-10 range."""
    if raw_score is None:
        return 5
    try:
        return max(1, min(10, int(raw_score)))
    except (ValueError, TypeError):
        return 5


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

        # Join with portfolios and decisions to get model attribution and reasoning
        res = (
            sb_client.table("trades")
            .select(
                "id, ticker, quantity, price, signal, executed_at, reasoning, portfolio_id, "
                "portfolios(owner_id), decisions(reasoning, model_name, metadata)"
            )
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
            model_name, reasoning, strategy_reasoning = _resolve_trade_context(trade)

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

                # 6. Inject into Memory with dynamic importance score
                importance_score = _extract_importance_score(getattr(resp, "importance_score", None))

                memory_content = (
                    f"{days_back}-DAY POST-ANALYSIS ({ticker}): {resp.lesson} | "
                    f"ORIGINAL TRADE: {signal} @ ${entry_price:.2f} | "
                    f"OUTCOME: {price_change_pct:.2f}% | "
                    f"ADVICE: {resp.sentiment_shift}"
                )

                success = add_memory(
                    content=memory_content,
                    memory_type="POST_MORTEM",
                    importance_score=importance_score,
                    metadata={
                        "price_change_pct": price_change_pct,
                        "trade_id": str(trade["id"]),
                        "analysis_window": str(days_back),
                        "model_name": model_name,
                        "is_regret": resp.is_regret,
                    },
                    check_similarity=True,
                )

                if success:
                    logger.info(f"Generated {days_back}d post-analysis memory for {ticker}. Lesson: {resp.lesson}")

            except Exception as e:
                logger.error(f"Post-analysis failed for trade {trade['id']} ({ticker}) in {days_back}d window: {e}")

    logger.info("Post-Analysis processing complete.")
