import asyncio
import os
import sys
from datetime import UTC, datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import DEEPSEEK_FLASH_MODEL, MINIMAX_MODEL, logger
from core.db import get_supabase_client
from core.llm.clients import close_client, get_deepseek_client
from core.llm.daily_predictor_prompts import (
    DAILY_PREDICTOR_PROMPT,
    DailyPredictionOutput,
)
from core.llm.minimax import MiniMaxClient


async def seed_daily_predictor_prompt(model_name: str = DEEPSEEK_FLASH_MODEL) -> tuple[str, str]:
    """Seed the Auto-Researcher optimized prompt as the active live baseline for a specific model in Supabase."""
    client = get_supabase_client()
    today = datetime.now(UTC).date()
    tag = f"daily-pred-seeded-{model_name}"

    try:
        # Demote previous active/baseline live predictor prompts for this track to saved
        client.table("prompt_experiments").update({"status": "saved"}).eq("prompt_name", "DAILY_PREDICTOR_PROMPT").eq(
            "track_id", model_name
        ).eq("status", "active").execute()

        # Insert new seeded prompt as active baseline
        client.table("prompt_experiments").insert(
            {
                "variant_tag": tag,
                "prompt_name": "DAILY_PREDICTOR_PROMPT",
                "prompt_content": DAILY_PREDICTOR_PROMPT,
                "track_id": model_name,
                "week_start": today.isoformat(),
                "week_end": (today + timedelta(days=7)).isoformat(),
                "status": "active",
                "experiment_type": "baseline",
                "change_description": f"Seeded symmetric zero-mean anti-bias predictor prompt for {model_name}.",
            }
        ).execute()

        logger.info(f"Successfully seeded and deployed live active prompt variant for {model_name}: {tag}")
        return tag, DAILY_PREDICTOR_PROMPT
    except Exception as e:
        logger.error(f"Error seeding daily predictor prompt for {model_name}: {e}")

    return tag, DAILY_PREDICTOR_PROMPT


async def fetch_active_daily_prompt(model_name: str = DEEPSEEK_FLASH_MODEL) -> tuple[str, str]:
    """Fetch active DAILY_PREDICTOR_PROMPT for a specific model track from database, or bootstrap baseline."""
    client = get_supabase_client()
    try:
        # Try track-specific query first
        response = (
            client.table("prompt_experiments")
            .select("variant_tag, prompt_content")
            .eq("prompt_name", "DAILY_PREDICTOR_PROMPT")
            .eq("track_id", model_name)
            .eq("status", "active")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        if response.data:
            return response.data[0]["variant_tag"], response.data[0]["prompt_content"]

        # Fallback to general active prompt if track_id not yet populated
        general_resp = (
            client.table("prompt_experiments")
            .select("variant_tag, prompt_content")
            .eq("prompt_name", "DAILY_PREDICTOR_PROMPT")
            .eq("status", "active")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if general_resp.data:
            return general_resp.data[0]["variant_tag"], general_resp.data[0]["prompt_content"]

        logger.info(f"No active DAILY_PREDICTOR_PROMPT found for {model_name}. Seeding baseline...")
        return await seed_daily_predictor_prompt(model_name=model_name)
    except Exception as e:
        logger.error(f"Error fetching active daily predictor prompt for {model_name}: {e}")

    return f"fallback-daily-{model_name}", DAILY_PREDICTOR_PROMPT


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

    # 1. Price Action, Technicals & Pre-Market Live Quote via MarketDataManager (FMP)
    try:
        mdm = MarketDataManager()
        is_pm = await mdm.is_premarket()

        if is_pm:
            context_lines.append("=== LIVE PRE-MARKET ACTION & GAP ANALYSIS ===")
            # Pre-Market Live Quote for Target
            pm_quote = await mdm.get_premarket_quote(ticker)
            if pm_quote:
                pm_price = pm_quote["price"]
                pm_change = pm_quote["change"]
                pm_change_pct = pm_quote["change_pct"]
                context_lines.append(
                    f"Target Asset ({ticker}): ${pm_price:.2f} | "
                    f"Overnight Gap: {pm_change:+.2f} ({pm_change_pct:+.2f}%) vs Prev Close ${pm_quote['previous_close']:.2f}"
                )

            # Benchmark Equities & Key Macro Drivers (Gold, WTI Crude Oil)
            macro_proxies = [
                ("QQQ", "Nasdaq 100"),
                ("DIA", "Dow Jones"),
                ("IWM", "Russell 2000"),
                ("GLD", "Gold"),
                ("USO", "WTI Crude Oil"),
            ]
            proxy_lines = []
            for sym, label in macro_proxies:
                if sym == ticker:
                    continue
                q = await mdm.get_premarket_quote(sym)
                if q:
                    proxy_lines.append(f"- {sym} ({label}): ${q['price']:.2f} | Gap: {q['change_pct']:+.2f}%")
            if proxy_lines:
                context_lines.append("Pre-Market Benchmark Indices & Key Macro Drivers:")
                context_lines.extend(proxy_lines)
            context_lines.append("=============================================")
        else:
            pm_quote = await mdm.get_premarket_quote(ticker)
            if pm_quote:
                pm_price = pm_quote["price"]
                pm_change = pm_quote["change"]
                pm_change_pct = pm_quote["change_pct"]
                context_lines.append(
                    f"Live Pre-Market / Early Session Quote: ${pm_price:.2f} | "
                    f"Overnight Gap: {pm_change:+.2f} ({pm_change_pct:+.2f}%) vs Prev Close ${pm_quote['previous_close']:.2f}"
                )

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
        logger.warning(
            f"Error fetching technical indicators & pre-market quote via MarketDataManager for {ticker}: {e}"
        )

    # 2. Macro & Market Feeling Context via Canonical Tools
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

    context_lines.append(f"Prediction Target Date: {today_str}")
    return "\n".join(context_lines)


async def run_daily_prediction(ticker: str = "SPY") -> list[dict]:
    """Run daily predictions at 8:00 AM ET for target ticker across model arena (DeepSeek & MiniMax)."""
    client = get_supabase_client()
    context = await get_daily_market_context(ticker=ticker)

    today = datetime.now(UTC).date()
    user_msg = (
        f"Market Context:\n{context}\n\n"
        f"Analyze the market context and predict whether {ticker} will close HIGHER (UP) or LOWER (DOWN) "
        f"at 4:00 PM ET today compared to the 9:30 AM ET Open price."
    )

    models = [
        {"name": DEEPSEEK_FLASH_MODEL, "type": "instructor", "provider": "deepseek"},
        {"name": MINIMAX_MODEL, "type": "minimax", "provider": "minimax"},
    ]

    results = []

    for model_cfg in models:
        model_name = model_cfg["name"]
        m_type = model_cfg["type"]
        provider = model_cfg["provider"]
        prompt_tag, prompt_content = await fetch_active_daily_prompt(model_name=model_name)

        success = False
        for attempt in range(3):
            try:
                if m_type == "instructor":
                    deepseek_client = get_deepseek_client()
                    try:
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

                        pred_dir = resp.predicted_direction.upper()
                        confidence = float(resp.confidence)
                        expected_return_pct = float(resp.expected_return_pct)
                        rationale = resp.rationale
                        catalysts = resp.catalysts
                    finally:
                        await close_client(deepseek_client, provider)

                elif m_type == "minimax":
                    minimax_client = MiniMaxClient()
                    try:
                        messages = [
                            {"role": "system", "content": prompt_content},
                            {"role": "user", "content": user_msg},
                        ]
                        parsed_json = await minimax_client.chat_with_json_response(messages, model=model_name)
                        pred_dir = str(parsed_json.get("predicted_direction", "UP")).upper()
                        confidence = float(parsed_json.get("confidence", 50.0))
                        expected_return_pct = float(parsed_json.get("expected_return_pct", 0.0))
                        rationale = str(parsed_json.get("rationale", ""))
                        catalysts = parsed_json.get("catalysts", [])
                    finally:
                        await minimax_client.close()

                prediction_row = {
                    "prediction_date": today.isoformat(),
                    "target_date": today.isoformat(),
                    "ticker": ticker.upper(),
                    "model_name": model_name,
                    "prompt_variant_tag": prompt_tag,
                    "predicted_direction": pred_dir,
                    "confidence": confidence,
                    "expected_return_pct": expected_return_pct,
                    "rationale": rationale,
                    "catalysts": catalysts,
                    "status": "pending",
                }

                client.table("daily_predictions").upsert(
                    prediction_row,
                    on_conflict="target_date,ticker,model_name",
                ).execute()

                logger.info(
                    f"Successfully logged daily prediction for {ticker} ({model_name}) on {today}: "
                    f"{pred_dir} with {confidence}% confidence."
                )
                results.append(prediction_row)
                success = True
                break
            except Exception as e:
                logger.warning(f"Prediction attempt {attempt + 1} failed for {model_name} on {ticker}: {e}")
                if attempt < 2:
                    await asyncio.sleep(2)
        if not success:
            logger.error(f"Daily prediction failed for {model_name} on {ticker} after 3 attempts.")

    return results


if __name__ == "__main__":
    asyncio.run(run_daily_prediction(ticker="SPY"))
