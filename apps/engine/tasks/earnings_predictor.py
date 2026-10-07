"""Day-1 Earnings Movement Predictor Arena Task.

Dispatches earnings day-1 movement predictions (RTH Open-to-Close UP/DOWN)
across GPT Luna (gpt-5.6-luna), DeepSeek Flash (deepseek-chat), and TypeSafe Jev (~typesafe/jev-latest).
"""

from datetime import UTC, datetime
from typing import Any

import httpx

from core.config import (
    DEEPSEEK_FLASH_MODEL,
    JEV_MODEL,
    OPENAI_MODEL,
    OPENROUTER_API_KEY,
    logger,
)
from core.db import get_supabase_client
from core.llm.clients import get_deepseek_client, get_openai_client
from core.llm.earnings_predictor_prompts import (
    EARNINGS_JEV_DEFAULT_CRITERIA,
    EARNINGS_JEV_INSTRUCTIONS,
    EARNINGS_JEV_QUESTION_KEY,
    EARNINGS_JEV_QUESTION_TYPE,
    EARNINGS_PREDICTOR_PROMPT,
    EarningsPredictionOutput,
)


def format_candidate_context(candidate: dict[str, Any]) -> str:
    """Format fundamental earnings metrics into dense contextual text for generative LLMs."""
    ticker = str(candidate.get("ticker", "UNKNOWN")).upper()
    sector = str(candidate.get("sector", "Unknown"))
    report_date = str(candidate.get("report_date", "Unknown"))
    timing = str(candidate.get("report_timing", "BMO")).upper()

    actual_eps = candidate.get("actual_eps")
    est_eps = candidate.get("estimated_eps")
    eps_surprise = candidate.get("eps_surprise")
    rev_surprise_pct = candidate.get("revenue_surprise_pct")
    sue = candidate.get("sue_score")
    is_top_decile = candidate.get("is_top_decile_sue", False)
    sloan_clean = candidate.get("is_sloan_accrual_clean", True)
    pre_runup = candidate.get("pre_earnings_20d_return_pct", 0.0)
    consensus = candidate.get("analyst_consensus", "Hold")
    target_upside = candidate.get("target_consensus_upside_pct")

    actual_eps_str = f"${actual_eps:.2f}" if actual_eps is not None else "N/A"
    est_eps_str = f"${est_eps:.2f}" if est_eps is not None else "N/A"
    eps_surp_str = f"{eps_surprise:+.2f}" if eps_surprise is not None else "N/A"
    rev_surp_str = f"{rev_surprise_pct:+.1f}%" if rev_surprise_pct is not None else "N/A"
    sue_str = f"{sue:.2f}" if sue is not None else "N/A"
    sloan_str = "Clean Operating Cash Flow" if sloan_clean else "High Non-Cash Accruals"
    upside_str = f"{target_upside:+.1f}%" if target_upside is not None else "N/A"

    return f"""Asset: {ticker} (Sector: {sector})
Report Date: {report_date} (Timing: {timing})

Earnings Report Fundamentals:
- Actual EPS: {actual_eps_str} vs Estimated EPS: {est_eps_str} (Surprise: {eps_surp_str})
- Revenue Surprise: {rev_surp_str}
- Standardized Unexpected Earnings (SUE): {sue_str} (Top-Decile: {is_top_decile})
- Sloan Accrual Quality: {sloan_str}
- Pre-Earnings 20-Day Momentum: {pre_runup:+.1f}%
- Analyst Consensus: {consensus} (Price Target Upside: {upside_str})
"""


async def predict_with_luna(candidate: dict[str, Any], context: str) -> dict[str, Any]:
    """Execute prediction using OpenAI Luna (gpt-5.6-luna) with reasoning."""
    client = get_openai_client()
    messages = [
        {"role": "system", "content": EARNINGS_PREDICTOR_PROMPT},
        {"role": "user", "content": f"Analyze this reporting stock and predict Day-1 RTH direction:\n\n{context}"},
    ]

    try:
        resp = await client.chat.completions.create(
            model=OPENAI_MODEL,
            response_model=EarningsPredictionOutput,
            messages=messages,
        )
        return {
            "predicted_direction": resp.predicted_direction,
            "confidence": float(resp.confidence),
            "expected_return_pct": resp.expected_return_pct,
            "rationale": f"GPT Luna: {resp.rationale}",
            "catalysts": resp.catalysts,
        }
    except Exception as e:
        logger.exception(f"Error predicting earnings movement with GPT Luna for {candidate.get('ticker')}: {e}")
        return {
            "predicted_direction": "UP",
            "confidence": 50.0,
            "expected_return_pct": 0.0,
            "rationale": f"GPT Luna fallback: error during inference: {e}",
            "catalysts": [],
        }


async def predict_with_deepseek(candidate: dict[str, Any], context: str) -> dict[str, Any]:
    """Execute prediction using DeepSeek Flash (deepseek-chat)."""
    client = get_deepseek_client()
    messages = [
        {"role": "system", "content": EARNINGS_PREDICTOR_PROMPT},
        {"role": "user", "content": f"Analyze this reporting stock and predict Day-1 RTH direction:\n\n{context}"},
    ]

    try:
        resp = await client.chat.completions.create(
            model=DEEPSEEK_FLASH_MODEL,
            response_model=EarningsPredictionOutput,
            messages=messages,
        )
        return {
            "predicted_direction": resp.predicted_direction,
            "confidence": float(resp.confidence),
            "expected_return_pct": resp.expected_return_pct,
            "rationale": f"DeepSeek Flash: {resp.rationale}",
            "catalysts": resp.catalysts,
        }
    except Exception as e:
        logger.exception(f"Error predicting earnings movement with DeepSeek for {candidate.get('ticker')}: {e}")
        return {
            "predicted_direction": "UP",
            "confidence": 50.0,
            "expected_return_pct": 0.0,
            "rationale": f"DeepSeek fallback: error during inference: {e}",
            "catalysts": [],
        }


async def predict_with_jev(
    candidate: dict[str, Any],
    criteria: dict[str, str] | None = None,
    model_name: str = JEV_MODEL,
) -> dict[str, Any]:
    """Execute prediction using TypeSafe Jev via OpenRouter Decisions API."""
    key = OPENROUTER_API_KEY
    if not key:
        logger.warning("OPENROUTER_API_KEY is unset. Returning default fallback for Jev.")
        return {
            "predicted_direction": "UP",
            "confidence": 50.0,
            "expected_return_pct": 0.0,
            "rationale": "Jev fallback: OPENROUTER_API_KEY not configured.",
            "catalysts": [],
        }

    ticker = str(candidate.get("ticker", "UNKNOWN")).upper()
    crit = criteria or EARNINGS_JEV_DEFAULT_CRITERIA

    state = {
        "ticker": ticker,
        "sector": candidate.get("sector", "Unknown"),
        "report_date": str(candidate.get("report_date", "")),
        "report_timing": candidate.get("report_timing", "BMO"),
        "actual_eps": candidate.get("actual_eps"),
        "estimated_eps": candidate.get("estimated_eps"),
        "eps_surprise": candidate.get("eps_surprise"),
        "revenue_surprise_pct": candidate.get("revenue_surprise_pct"),
        "sue_score": candidate.get("sue_score"),
        "is_top_decile_sue": candidate.get("is_top_decile_sue", False),
        "is_sloan_accrual_clean": candidate.get("is_sloan_accrual_clean", True),
        "analyst_consensus": candidate.get("analyst_consensus", "Unknown"),
        "target_consensus_upside_pct": candidate.get("target_consensus_upside_pct"),
    }

    payload = {
        "model": model_name,
        "state": state,
        "questions": {
            EARNINGS_JEV_QUESTION_KEY: {
                "type": EARNINGS_JEV_QUESTION_TYPE,
                "instructions": EARNINGS_JEV_INSTRUCTIONS,
                "criteria": {
                    "UP": crit.get("UP", EARNINGS_JEV_DEFAULT_CRITERIA["UP"]),
                    "DOWN": crit.get("DOWN", EARNINGS_JEV_DEFAULT_CRITERIA["DOWN"]),
                },
            }
        },
    }

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post("https://openrouter.ai/api/alpha/decisions", headers=headers, json=payload)
            if resp.status_code != 200:
                raise RuntimeError(f"OpenRouter Decisions API error {resp.status_code}: {resp.text}")
            data = resp.json()

        answers = data.get("answers", {})
        dir_ans = answers.get(EARNINGS_JEV_QUESTION_KEY, {})
        choice = str(dir_ans.get("choice", "UP")).upper()
        probabilities = dir_ans.get("probabilities", {})
        prob = float(probabilities.get(choice, dir_ans.get("confidence", 0.5)))
        confidence = round(prob * 100.0, 1) if prob <= 1.0 else round(prob, 1)

        rationale = (
            f"TypeSafe Jev System One decision: {choice} (P={prob:.2f}, "
            f"confidence={dir_ans.get('confidence', 0):.2f}, "
            f"distribution={probabilities})"
        )

        return {
            "predicted_direction": choice,
            "confidence": confidence,
            "expected_return_pct": 0.0,
            "rationale": rationale,
            "catalysts": [],
        }
    except Exception as e:
        logger.exception(f"Error predicting earnings movement with Jev for {ticker}: {e}")
        return {
            "predicted_direction": "UP",
            "confidence": 50.0,
            "expected_return_pct": 0.0,
            "rationale": f"Jev fallback: {e}",
            "catalysts": [],
        }


async def discover_earnings_candidates(
    target_date_str: str, ticker: str | None = None, limit: int = 5
) -> list[dict[str, Any]]:
    """Query recent snapshots from earnings_alpha_snapshots for reporting companies."""
    client = get_supabase_client()
    try:
        query = client.table("earnings_alpha_snapshots").select("*")
        query = query.eq("ticker", ticker.upper()) if ticker else query.order("snapshot_date", desc=True)
        res = query.limit(limit).execute()

        if res.data:
            return res.data
    except Exception as e:
        logger.warning(f"Error querying earnings snapshots for candidates: {e}")

    # Fallback candidate if database is empty or unpopulated
    sample_ticker = ticker.upper() if ticker else "NVDA"
    return [
        {
            "snapshot_date": target_date_str,
            "ticker": sample_ticker,
            "sector": "Technology",
            "report_date": target_date_str,
            "report_timing": "BMO",
            "actual_eps": 1.25,
            "estimated_eps": 1.10,
            "eps_surprise": 0.15,
            "revenue_actual": 30000000000,
            "revenue_estimated": 28500000000,
            "revenue_surprise_pct": 5.26,
            "sue_score": 3.40,
            "is_top_decile_sue": True,
            "sloan_accrual_ratio": 0.04,
            "is_sloan_accrual_clean": True,
            "analyst_consensus": "Strong Buy",
            "target_consensus_upside_pct": 14.5,
        }
    ]


async def run_earnings_prediction(
    target_date: str | None = None,
    ticker: str | None = None,
    force: bool = False,
) -> list[dict[str, Any]]:
    """Run earnings day-1 prediction pipeline across Luna, DeepSeek, and Jev."""
    today_dt = datetime.now(UTC).date()
    target_date_str = target_date or today_dt.isoformat()
    prediction_date_str = today_dt.isoformat()

    logger.info(f"Running Day-1 Earnings Predictor Arena for target_date={target_date_str} (force={force})")

    candidates = await discover_earnings_candidates(target_date_str, ticker=ticker)
    if not candidates:
        logger.info("No earnings candidates found to predict.")
        return []

    client = get_supabase_client()
    saved_records = []

    for cand in candidates:
        cand_ticker = cand["ticker"].upper()
        context = format_candidate_context(cand)

        models_to_run = [
            ("gpt-5.6-luna", predict_with_luna(cand, context)),
            ("deepseek-chat", predict_with_deepseek(cand, context)),
            ("~typesafe/jev-latest", predict_with_jev(cand)),
        ]

        for model_name, coroutine in models_to_run:
            # Check if prediction already exists
            if not force:
                try:
                    existing = (
                        client.table("earnings_predictions")
                        .select("id")
                        .eq("target_date", target_date_str)
                        .eq("ticker", cand_ticker)
                        .eq("model_name", model_name)
                        .execute()
                    )
                    if existing.data:
                        logger.debug(
                            f"Prediction for {cand_ticker} ({model_name}) on {target_date_str} already exists. Skipping."
                        )
                        continue
                except Exception as e:
                    logger.debug(f"Error checking existing earnings prediction: {e}")

            pred = await coroutine
            record = {
                "prediction_date": prediction_date_str,
                "target_date": target_date_str,
                "ticker": cand_ticker,
                "model_name": model_name,
                "prompt_variant_tag": f"earnings-pred-{model_name}",
                "predicted_direction": pred["predicted_direction"],
                "confidence": pred["confidence"],
                "expected_return_pct": pred.get("expected_return_pct"),
                "rationale": pred["rationale"],
                "catalysts": pred.get("catalysts", []),
                "report_timing": cand.get("report_timing", "BMO"),
                "actual_eps": cand.get("actual_eps"),
                "estimated_eps": cand.get("estimated_eps"),
                "eps_surprise": cand.get("eps_surprise"),
                "revenue_surprise_pct": cand.get("revenue_surprise_pct"),
                "sue_score": cand.get("sue_score"),
                "status": "pending",
            }

            try:
                client.table("earnings_predictions").upsert(
                    record, on_conflict="target_date,ticker,model_name"
                ).execute()
                saved_records.append(record)
                logger.info(
                    f"Recorded earnings prediction: {cand_ticker} by {model_name} -> "
                    f"{record['predicted_direction']} ({record['confidence']}%)"
                )
            except Exception as e:
                logger.exception(f"Failed to upsert prediction for {cand_ticker} ({model_name}): {e}")

    return saved_records
