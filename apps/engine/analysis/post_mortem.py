"""Regret-Driven Reinforcement Loop (Post-Mortem analysis).

This module analyzes past trades against actual price performance to generate
'lessons learned' for long-term memory.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from core.config import logger, GEMINI_MODEL
from core.db import get_supabase_client
from core.llm import get_gemini_client, prompts
from execution.market_data import MarketDataManager
from memory.store import add_memory
from pydantic import BaseModel, Field

class PostMortemResult(BaseModel):
    lesson: str = Field(..., description="A concise lesson learned")
    is_regret: bool = Field(..., description="Whether the trade was a mistake")
    sentiment_shift: str = Field(..., description="How to adjust view on this ticker/sector")

async def perform_post_mortems(days_back: int = 5):
    """Analyzes trades from N days ago and generates self-corrective memories.

    Args:
        days_back: Look exactly N days ago to evaluate trade performance.
    """
    logger.info(f"Starting Post-Mortem analysis for trades {days_back} days ago...")
    sb_client = get_supabase_client()
    mdm = MarketDataManager()
    
    # 1. Fetch trades from the target window
    target_date = (datetime.now(timezone.utc) - timedelta(days=days_back)).date()
    start_time = datetime.combine(target_date, datetime.min.time()).isoformat()
    end_time = datetime.combine(target_date, datetime.max.time()).isoformat()
    
    # Join with decisions to get reasoning
    res = sb_client.table("trades").select(
        "id, ticker, quantity, price, signal, executed_at, decisions(reasoning, model_name)"
    ).filter("executed_at", "gte", start_time).filter("executed_at", "lte", end_time).execute()
    
    trades = res.data if res.data else []
    if not trades:
        logger.info(f"No trades found for post-mortem analysis on {target_date}.")
        return

    logger.info(f"Analyzing {len(trades)} trades for {target_date}...")
    
    # Use Gemini Flash 3 as the Manager Agent
    client = get_gemini_client()

    for trade in trades:
        ticker = trade["ticker"]
        entry_price = trade["price"]
        signal = trade["signal"]
        # decisions is a list because of the join, but it should be 1:1 if correctly linked
        decision_data = trade.get("decisions", [{}])[0] if trade.get("decisions") else {}
        reasoning = decision_data.get("reasoning", "No reasoning found.")
        model_name = decision_data.get("model_name", "unknown_model")
        
        # 2. Get current price
        quote = await mdm.get_quote(ticker)
        if not quote:
            continue
            
        current_price = quote.price
        price_change_pct = ((current_price - entry_price) / entry_price) * 100
        if signal.upper() == "SELL":
            price_change_pct = -price_change_pct
            
        is_successful = price_change_pct > 0
        
        # 3. Ask Manager Agent to analyze the "Regret" or "Success"
        prompt = prompts.MANAGER_USER_PROMPT_TEMPLATE.format(
            ticker=ticker,
            signal=signal,
            entry_price=entry_price,
            current_price=current_price,
            price_change_pct=price_change_pct,
            reasoning=reasoning
        )
        
        try:
            # Note: instructor handles the structured output
            resp = await client.chat.completions.create(
                model=GEMINI_MODEL,
                response_model=PostMortemResult,
                messages=[
                    {"role": "system", "content": prompts.MANAGER_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ]
            )
            
            # 4. Inject into Memory
            memory_content = (
                f"POST-MORTEM LESSON ({ticker}): {resp.lesson} | "
                f"ORIGINAL TRADE: {signal} @ ${entry_price:.2f} | "
                f"OUTCOME: {price_change_pct:.2f}% | "
                f"ADVICE: {resp.sentiment_shift}"
            )
            
            success = add_memory(
                content=memory_content,
                memory_type="LESSON_LEARNED",
                metadata={
                    "type": "post_mortem",
                    "ticker": ticker,
                    "trade_id": trade["id"],
                    "model_name": model_name,
                    "is_regret": resp.is_regret,
                    "price_change_pct": price_change_pct
                }
            )
            
            if success:
                logger.info(f"Generated post-mortem memory for {ticker} ({signal}). Lesson: {resp.lesson}")
            
        except Exception as e:
            logger.error(f"Post-mortem failed for trade {trade['id']} ({ticker}): {e}")

    logger.info("Post-Mortem processing complete.")
