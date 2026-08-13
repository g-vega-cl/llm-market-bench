import asyncio
import os
import sys
from datetime import UTC, datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pydantic import BaseModel

from core.config import DEEPSEEK_FLASH_MODEL, GEMINI_MODEL, MINIMAX_MODEL, OPENAI_MODEL, logger
from core.db import get_supabase_client
from core.llm.clients import (
    close_client,
    get_deepseek_client,
    get_gemini_client,
    get_openai_client,
)
from core.llm.minimax import MiniMaxClient
from core.llm.predictor_prompts import SECTOR_PREDICTOR_PROMPT


class SectorPredictionResponse(BaseModel):
    predicted_sector: str
    predicted_pair: list[str]
    confidence: float = 75.0
    reasoning: str


async def fetch_active_prompt() -> tuple[str, str]:
    """Fetch the active SECTOR_PREDICTOR_PROMPT from the database, or use fallback."""
    client = get_supabase_client()
    try:
        response = (
            client.table("prompt_experiments")
            .select("variant_tag, prompt_content")
            .eq("prompt_name", "SECTOR_PREDICTOR_PROMPT")
            .eq("status", "active")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        if response.data:
            return response.data[0]["variant_tag"], response.data[0]["prompt_content"]

        # If no active prompt in DB, bootstrap the baseline
        logger.info("No active SECTOR_PREDICTOR_PROMPT found. Bootstrapping baseline...")
        today = datetime.now(UTC).date()
        week_start = today - timedelta(days=7)
        week_end = today
        tag = "sector-pred-baseline"

        client.table("prompt_experiments").insert(
            {
                "variant_tag": tag,
                "prompt_name": "SECTOR_PREDICTOR_PROMPT",
                "prompt_content": SECTOR_PREDICTOR_PROMPT,
                "week_start": week_start.isoformat(),
                "week_end": week_end.isoformat(),
                "status": "active",
                "experiment_type": "baseline",
                "change_description": "Initial baseline sector predictor prompt.",
            }
        ).execute()
        return tag, SECTOR_PREDICTOR_PROMPT
    except Exception as e:
        logger.error(f"Error fetching active predictor prompt: {e}")

    return "fallback-base", SECTOR_PREDICTOR_PROMPT


async def get_predictor_data() -> str:
    """Fetch recent correlation and macro data to feed the predictor."""
    client = get_supabase_client()
    try:
        # Get latest run
        runs = client.table("correlation_runs").select("id, run_date").order("run_date", desc=True).limit(1).execute()
        if not runs.data:
            return "No historical correlation data available."

        run_id = runs.data[0]["id"]
        run_date = runs.data[0]["run_date"]

        # Get correlation data
        res = client.table("correlation_data").select("*").eq("run_id", run_id).execute()
        if not res.data:
            return f"No correlation data found for run {run_date}."

        # Extract returns and correlations
        assets = {}
        uncorrelated_pairs = []

        for row in res.data:
            a, b = row["ticker_a"], row["ticker_b"]
            ret_a = row.get("returns_a_90d") or 0.0
            ret_b = row.get("returns_b_90d") or 0.0
            corr = row.get("pearson_corr")

            assets[a] = {
                "7d": row.get("returns_a_7d") or 0.0,
                "30d": row.get("returns_a_30d") or 0.0,
                "90d": ret_a,
            }
            assets[b] = {
                "7d": row.get("returns_b_7d") or 0.0,
                "30d": row.get("returns_b_30d") or 0.0,
                "90d": ret_b,
            }

            if corr is not None and abs(corr) < 0.3:
                uncorrelated_pairs.append((a, b, corr, (ret_a + ret_b) / 2))

        # Sort uncorrelated pairs by absolute correlation ascending
        uncorrelated_pairs.sort(key=lambda x: abs(x[2]))

        data_str = f"Market Correlation and Return Data (Run Date: {run_date})\n\n"
        data_str += "Asset Performance:\n"
        for asset, returns in sorted(assets.items()):
            data_str += f"- {asset}: 7d Return: {returns['7d']:.2f}%, 30d Return: {returns['30d']:.2f}%, 90d Return: {returns['90d']:.2f}%\n"

        data_str += "\nTop Uncorrelated Asset Pairs (Correlation < 0.3):\n"
        for a, b, corr, avg_ret in uncorrelated_pairs[:15]:
            data_str += f"- {a} and {b}: Correlation: {corr:.2f}, Average 90d Return: {avg_ret:.2f}%\n"

        return data_str
    except Exception as e:
        logger.error(f"Error fetching predictor data: {e}")
        return "Error loading market correlation and returns data."


async def run_sector_predictions():
    client = get_supabase_client()
    prompt_tag, prompt_content = await fetch_active_prompt()
    data_block = await get_predictor_data()

    today = datetime.now(UTC).date()

    models = [
        {"name": DEEPSEEK_FLASH_MODEL, "client": get_deepseek_client(), "type": "instructor", "provider": "deepseek"},
        {"name": MINIMAX_MODEL, "client": MiniMaxClient(), "type": "minimax", "provider": "minimax"},
        {"name": GEMINI_MODEL, "client": get_gemini_client(), "type": "instructor", "provider": "gemini"},
        {"name": OPENAI_MODEL, "client": get_openai_client(), "type": "instructor", "provider": "openai"},
    ]

    timeframes = ["7d", "30d", "60d", "90d"]

    for tf in timeframes:
        days = int(tf.replace("d", ""))
        target_date = today + timedelta(days=days)

        for model in models:
            success = False
            for attempt in range(3):
                try:
                    user_msg = f"Data:\n{data_block}\nPredict the best sector and pair for the next {tf}."
                    if attempt > 0 and model["type"] == "minimax":
                        # Add a hint to keep it concise to avoid token limit issues
                        user_msg += "\nNote: Keep your internal reasoning/thinking process concise to avoid token limit truncation."

                    if model["type"] == "instructor":
                        client_inst = model["client"]
                        create_kwargs = {
                            "model": model["name"],
                            "response_model": SectorPredictionResponse,
                            "messages": [
                                {"role": "system", "content": prompt_content},
                                {"role": "user", "content": user_msg},
                            ],
                        }
                        if model.get("provider") == "openai":
                            create_kwargs["reasoning_effort"] = "none"

                        resp_awaitable = client_inst.chat.completions.create(**create_kwargs)
                        if hasattr(resp_awaitable, "__await__") or asyncio.iscoroutine(resp_awaitable):
                            resp = await resp_awaitable
                        else:
                            resp = resp_awaitable
                        result = {
                            "predicted_sector": resp.predicted_sector,
                            "predicted_pair": resp.predicted_pair,
                            "confidence": resp.confidence,
                            "reasoning": resp.reasoning,
                        }
                    elif model["type"] == "minimax":
                        # MiniMax uses its own client
                        messages = [
                            {"role": "system", "content": prompt_content},
                            {"role": "user", "content": user_msg},
                        ]
                        result = await model["client"].chat_with_json_response(messages, model=model["name"])

                    # Upsert prediction to prevent duplicates on the same date/model/timeframe
                    client.table("sector_predictions").upsert(
                        {
                            "prediction_date": today.isoformat(),
                            "target_date": target_date.isoformat(),
                            "timeframe": tf,
                            "model_name": model["name"],
                            "prompt_tag": prompt_tag,
                            "predicted_sector": result.get("predicted_sector", "UNKNOWN"),
                            "predicted_pair": result.get("predicted_pair", []),
                            "confidence": float(result.get("confidence", 75.0)),
                            "reasoning": result.get("reasoning", ""),
                        },
                        on_conflict="prediction_date,model_name,timeframe",
                    ).execute()
                    success = True
                    break
                except Exception as e:
                    logger.warning(f"Prediction attempt {attempt + 1} failed for {model['name']} on {tf}: {e}")
                    if attempt < 2:
                        await asyncio.sleep(2)
            if not success:
                logger.error(f"Prediction failed for {model['name']} on {tf} after 3 attempts.")

    # Close clients
    for model in models:
        if model["type"] == "minimax":
            await model["client"].close()
        elif model["type"] == "instructor":
            await close_client(model["client"], model.get("provider", "instructor"))


if __name__ == "__main__":
    asyncio.run(run_sector_predictions())
