"""Day-1 Earnings Movement Predictor Arena Task.

Dispatches earnings day-1 movement predictions (RTH Open-to-Close UP/DOWN)
across GPT Luna (gpt-5.6-luna), DeepSeek Flash (deepseek-chat), and TypeSafe Jev (~typesafe/jev-latest).
"""

from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from core.config import (
    DEEPSEEK_FLASH_MODEL,
    FMP_API_KEY,
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

FMP_BASE_URL = "https://financialmodelingprep.com/stable"


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
            reasoning_effort="none",
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
    """Query recent snapshots from earnings_alpha_snapshots and earnings calendar for reporting companies."""
    # If ticker is provided and is not SPY (since SPY is an ETF without earnings), target that specific stock
    explicit_ticker = ticker.upper() if ticker and ticker.upper() != "SPY" else None
    client = get_supabase_client()
    seen_tickers: set[str] = set()
    candidates: list[dict[str, Any]] = []

    # 1. Query Supabase earnings_alpha_snapshots
    try:
        query = client.table("earnings_alpha_snapshots").select("*")
        if explicit_ticker:
            query = query.eq("ticker", explicit_ticker).order("snapshot_date", desc=True)
        else:
            # Look for companies reporting within 5 days of target date (covering weekends)
            try:
                target_dt = datetime.strptime(target_date_str, "%Y-%m-%d").date()
                min_report_date = (target_dt - timedelta(days=5)).strftime("%Y-%m-%d")
            except Exception:
                min_report_date = target_date_str
            query = (
                query.gte("report_date", min_report_date).order("report_date", desc=True).order("sue_score", desc=True)
            )

        res = query.limit(limit * 3).execute()
        if res.data:
            for row in res.data:
                sym = str(row.get("ticker", "")).upper()
                if sym and sym != "SPY" and sym not in seen_tickers:
                    seen_tickers.add(sym)
                    candidates.append(row)
                    if len(candidates) >= limit:
                        break
    except Exception as e:
        logger.warning(f"Error querying earnings snapshots for candidates: {e}")

    # 2. If under limit and FMP_API_KEY is available, check FMP live earnings calendar
    if not explicit_ticker and len(candidates) < limit and FMP_API_KEY:
        try:
            url = f"{FMP_BASE_URL}/earnings-calendar"
            async with httpx.AsyncClient(timeout=10.0) as http_client:
                resp = await http_client.get(
                    url, params={"from": target_date_str, "to": target_date_str, "apikey": FMP_API_KEY}
                )
                if resp.status_code == 200:
                    cal_data = resp.json()
                    if isinstance(cal_data, list):
                        with_eps = [
                            e
                            for e in cal_data
                            if e.get("symbol")
                            and e["symbol"].upper() != "SPY"
                            and e["symbol"].upper() not in seen_tickers
                            and (e.get("epsEstimated") is not None or e.get("epsActual") is not None)
                        ]
                        with_eps.sort(key=lambda x: float(x.get("revenueEstimated") or 0.0), reverse=True)
                        for entry in with_eps:
                            sym = entry["symbol"].upper()
                            seen_tickers.add(sym)
                            actual_eps = entry.get("epsActual")
                            est_eps = entry.get("epsEstimated")
                            actual_rev = entry.get("revenueActual")
                            est_rev = entry.get("revenueEstimated")
                            rev_surp = (
                                ((actual_rev - est_rev) / est_rev * 100.0)
                                if (actual_rev is not None and est_rev is not None and est_rev > 0)
                                else None
                            )
                            candidates.append(
                                {
                                    "snapshot_date": target_date_str,
                                    "ticker": sym,
                                    "sector": "Reporting Earnings",
                                    "report_date": entry.get("date", target_date_str),
                                    "report_timing": "BMO" if actual_eps is not None else "AMC",
                                    "actual_eps": actual_eps,
                                    "estimated_eps": est_eps,
                                    "eps_surprise": (
                                        (actual_eps - est_eps)
                                        if (actual_eps is not None and est_eps is not None)
                                        else None
                                    ),
                                    "revenue_actual": actual_rev,
                                    "revenue_estimated": est_rev,
                                    "revenue_surprise_pct": rev_surp,
                                    "sue_score": (
                                        2.0
                                        if (actual_eps is not None and est_eps is not None and actual_eps > est_eps)
                                        else 0.0
                                    ),
                                    "is_top_decile_sue": bool(
                                        actual_eps is not None and est_eps is not None and actual_eps > est_eps
                                    ),
                                    "is_sloan_accrual_clean": True,
                                    "analyst_consensus": "Moderate Buy",
                                    "target_consensus_upside_pct": 10.0,
                                }
                            )
                            if len(candidates) >= limit:
                                break
        except Exception as e:
            logger.debug(f"Could not fetch FMP earnings calendar for {target_date_str}: {e}")

    if candidates:
        return candidates

    # Fallback candidate if database and calendar are completely empty
    sample_ticker = explicit_ticker if explicit_ticker else "NVDA"
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
