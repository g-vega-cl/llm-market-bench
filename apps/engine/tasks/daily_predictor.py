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
    """Fetch recent market data context (market feeling, barometer, technicals)."""
    client = get_supabase_client()
    context_lines = [f"Asset: {ticker} (S&P 500 ETF)"]
    today_str = datetime.now(UTC).date().isoformat()

    try:
        # Fetch latest market feeling if available
        mf_res = (
            client.table("market_feeling")
            .select("sentiment_label, news_summary, created_at")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if mf_res.data:
            feeling = mf_res.data[0].get("sentiment_label")
            summary = mf_res.data[0].get("news_summary")
            if feeling:
                context_lines.append(f"Recent Market Sentiment / Feeling: {feeling}")
            if summary:
                context_lines.append(f"Latest News Summary: {summary[:500]}...")

        # Fetch recent market barometer
        mb_res = (
            client.table("market_barometer")
            .select("score, macro_trend, created_at")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if mb_res.data:
            baro = mb_res.data[0]
            context_lines.append(f"Market Barometer Score: {baro.get('score')} ({baro.get('macro_trend')})")

    except Exception as e:
        logger.warning(f"Error fetching daily context: {e}")

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
