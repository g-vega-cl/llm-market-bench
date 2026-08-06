import asyncio
import os
import sys
from datetime import UTC, datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import logger
from core.db import get_supabase_client
from core.llm.clients import close_client, get_deepseek_client
from core.llm.daily_predictor_prompts import (
    DAILY_PREDICTOR_PROMPT,
    DailyPredictionOutput,
)


async def seed_daily_predictor_prompt() -> tuple[str, str]:
    """Seed the Auto-Researcher optimized prompt as the active live baseline in Supabase."""
    client = get_supabase_client()
    today = datetime.now(UTC).date()
    tag = "daily-pred-seeded-v1"

    try:
        # Demote previous active/baseline live predictor prompts to saved
        client.table("prompt_experiments").update({"status": "saved"}).eq("prompt_name", "DAILY_PREDICTOR_PROMPT").eq(
            "status", "active"
        ).execute()

        # Insert new seeded prompt as active baseline
        client.table("prompt_experiments").insert(
            {
                "variant_tag": tag,
                "prompt_name": "DAILY_PREDICTOR_PROMPT",
                "prompt_content": DAILY_PREDICTOR_PROMPT,
                "week_start": today.isoformat(),
                "week_end": (today + timedelta(days=7)).isoformat(),
                "status": "active",
                "experiment_type": "baseline",
                "change_description": "Seeded from 12-week backtest Auto-Researcher optimization.",
            }
        ).execute()

        logger.info(f"Successfully seeded and deployed live active prompt variant: {tag}")
        return tag, DAILY_PREDICTOR_PROMPT
    except Exception as e:
        logger.error(f"Error seeding daily predictor prompt: {e}")

    return tag, DAILY_PREDICTOR_PROMPT


async def fetch_active_daily_prompt() -> tuple[str, str]:
    """Fetch active DAILY_PREDICTOR_PROMPT from database, or bootstrap baseline."""
    client = get_supabase_client()
    try:
        response = (
            client.table("prompt_experiments")
            .select("variant_tag, prompt_content")
            .eq("prompt_name", "DAILY_PREDICTOR_PROMPT")
            .eq("status", "active")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        if response.data:
            return response.data[0]["variant_tag"], response.data[0]["prompt_content"]

        logger.info("No active DAILY_PREDICTOR_PROMPT found. Seeding baseline...")
        return await seed_daily_predictor_prompt()
    except Exception as e:
        logger.error(f"Error fetching active daily predictor prompt: {e}")

    return "fallback-daily-base", DAILY_PREDICTOR_PROMPT


async def get_daily_market_context(ticker: str = "SPY") -> str:
    """Fetch recent market data context using canonical MarketDataManager (FMP) and pre-made tools."""
    from core.llm.tools import (
        execute_get_global_macro_context_tool,
        execute_get_market_feeling_tool,
        execute_get_volatility_index_details_tool,
        execute_market_health_barometer_tool,
    )
    from execution.market_data import MarketDataManager

    context_lines = [f"Asset: {ticker} (S&P 500 ETF)"]
    today_str = datetime.now(UTC).date().isoformat()

    # 1. Macro & Market Feeling Context via Canonical Tools
    try:
        macro_str = await execute_get_global_macro_context_tool()
        if macro_str and not macro_str.startswith("Error"):
            context_lines.append(f"Global Macro Baseline:\n{macro_str}")
    except Exception as e:
        logger.warning(f"Error fetching global macro context: {e}")

    try:
        vol_str = await execute_get_volatility_index_details_tool()
        if vol_str and not vol_str.startswith("Error"):
            context_lines.append(f"Volatility Index Details:\n{vol_str}")
    except Exception as e:
        logger.warning(f"Error fetching volatility index details: {e}")

    try:
        baro_str = await execute_market_health_barometer_tool()
        if baro_str and not baro_str.startswith("Error"):
            context_lines.append(f"Market Health Barometer:\n{baro_str}")
    except Exception as e:
        logger.warning(f"Error fetching market health barometer: {e}")

    try:
        feeling_str = await execute_get_market_feeling_tool()
        if feeling_str and not feeling_str.startswith("Error"):
            context_lines.append(f"Recent Market Feeling:\n{feeling_str[:500]}")
    except Exception as e:
        logger.warning(f"Error fetching market feeling: {e}")

    # 2. Price Action & Technicals via MarketDataManager (FMP)
    try:
        mdm = MarketDataManager()
        history = await mdm.get_history(ticker, days=30)
        if history and len(history) >= 2:
            sorted_hist = sorted(history, key=lambda x: x.get("fetched_at", ""))
            prev_row = sorted_hist[-1]
            prev_close = float(prev_row["price"])
            prev_date = str(prev_row.get("fetched_at", ""))[:10]

            context_lines.append(f"Previous Trading Session ({prev_date}) Close: ${prev_close:.2f}")

            if len(sorted_hist) >= 5:
                five_day_first = float(sorted_hist[-5]["price"])
                five_day_change_pct = ((prev_close - five_day_first) / five_day_first) * 100.0
                context_lines.append(f"5-Day Return: {five_day_change_pct:+.2f}%")

            if len(sorted_hist) >= 20:
                recent_prices = [float(r["price"]) for r in sorted_hist[-20:]]
                sma_20 = sum(recent_prices) / len(recent_prices)
                context_lines.append(f"20-Day Simple Moving Average (SMA20): ${sma_20:.2f}")

    except Exception as e:
        logger.warning(f"Error fetching technical indicators via MarketDataManager for {ticker}: {e}")

    context_lines.append(f"Prediction Target Date: {today_str}")
    return "\n".join(context_lines)


async def run_daily_prediction(ticker: str = "SPY") -> dict | None:
    """Run daily prediction at 8:00 AM ET for the target ticker (default SPY)."""
    client = get_supabase_client()
    prompt_tag, prompt_content = await fetch_active_daily_prompt()
    context = await get_daily_market_context(ticker=ticker)

    today = datetime.now(UTC).date()
    model_name = "deepseek-v4-flash"
    deepseek_client = get_deepseek_client()

    try:
        user_msg = (
            f"Market Context:\n{context}\n\n"
            f"Analyze the market context and predict whether {ticker} will close HIGHER (UP) or LOWER (DOWN) "
            f"at 4:00 PM ET today compared to the 9:30 AM ET Open price."
        )

        resp_awaitable = deepseek_client.chat.completions.create(
            model=model_name,
            response_model=DailyPredictionOutput,
            messages=[
                {"role": "system", "content": prompt_content},
                {"role": "user", "content": user_msg},
            ],
        )

        if hasattr(resp_awaitable, "__await__") or asyncio.iscoroutine(resp_awaitable):
            resp = await resp_awaitable
        else:
            resp = resp_awaitable

        prediction_row = {
            "prediction_date": today.isoformat(),
            "target_date": today.isoformat(),
            "ticker": ticker.upper(),
            "model_name": model_name,
            "prompt_variant_tag": prompt_tag,
            "predicted_direction": resp.predicted_direction.upper(),
            "confidence": float(resp.confidence),
            "expected_return_pct": float(resp.expected_return_pct),
            "rationale": resp.rationale,
            "catalysts": resp.catalysts,
            "status": "pending",
        }

        # Upsert prediction row in Supabase
        client.table("daily_predictions").upsert(
            prediction_row,
            on_conflict="target_date,ticker,model_name",
        ).execute()

        logger.info(
            f"Successfully logged daily prediction for {ticker} on {today}: "
            f"{resp.predicted_direction} with {resp.confidence}% confidence."
        )
        return prediction_row
    except Exception as e:
        logger.error(f"Error running daily prediction for {ticker}: {e}")
        return None
    finally:
        await close_client(deepseek_client, "deepseek")


if __name__ == "__main__":
    asyncio.run(run_daily_prediction(ticker="SPY"))
