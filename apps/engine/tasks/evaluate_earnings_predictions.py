"""Evaluation task for Day-1 Earnings Movement predictions.

Fetches Regular Trading Hours (09:30-16:00 ET) Open and Close prices,
computes binary direction outcome, Brier score calibration, and updates
status in the earnings_predictions table.
"""

from core.config import logger
from core.db import get_supabase_client
from tasks.evaluate_daily_predictions import (
    calculate_brier_score,
    fetch_intraday_prices,
    get_ny_now,
)


async def evaluate_earnings_predictions(
    target_date: str | None = None,
    force_recalc: bool = False,
) -> int:
    """Evaluate earnings predictions against actual RTH market prices.

    Args:
        target_date: Optional specific ISO date string (YYYY-MM-DD).
        force_recalc: If True, re-evaluates already evaluated predictions.
    """
    client = get_supabase_client()
    query = client.table("earnings_predictions").select("*")

    if target_date:
        query = query.eq("target_date", target_date)
        if not force_recalc:
            query = query.eq("status", "pending")
    else:
        if not force_recalc:
            query = query.eq("status", "pending")

    response = query.execute()
    pending = response.data or []

    if not pending:
        logger.info(f"No earnings predictions found to evaluate (target_date={target_date}, force={force_recalc}).")
        return 0

    evaluated_count = 0
    price_cache: dict[tuple[str, str], tuple[float | None, float | None, float | None, float | None]] = {}

    for pred in pending:
        pred_id = pred["id"]
        ticker = pred["ticker"]
        target_date_str = pred["target_date"]
        predicted_dir = pred["predicted_direction"].upper()
        confidence = float(pred.get("confidence", 50.0))

        # Skip evaluating today's session if market is still active (prior to 16:05 ET)
        now_et = get_ny_now()
        today_et_str = now_et.date().isoformat()
        if (
            target_date_str == today_et_str
            and (now_et.hour < 16 or (now_et.hour == 16 and now_et.minute < 5))
            and not force_recalc
        ):
            logger.info(
                f"Skipping evaluation for earnings prediction {pred_id} ({ticker} on {target_date_str}): "
                f"Market session active ({now_et.strftime('%H:%M')} ET < 16:05 ET)."
            )
            continue

        cache_key = (ticker, target_date_str)
        if cache_key in price_cache:
            open_p, high_p, low_p, close_p = price_cache[cache_key]
        else:
            open_p, high_p, low_p, close_p = await fetch_intraday_prices(
                ticker, target_date_str, force_refresh=force_recalc
            )
            price_cache[cache_key] = (open_p, high_p, low_p, close_p)

        if open_p is None or close_p is None:
            logger.warning(
                f"Could not retrieve Open/Close price for {ticker} on {target_date_str}. Skipping evaluation."
            )
            continue

        actual_dir = "UP" if close_p >= open_p else "DOWN"
        is_correct = predicted_dir == actual_dir
        brier = calculate_brier_score(predicted_dir, confidence, actual_dir)

        update_payload = {
            "open_price": round(open_p, 4),
            "close_price": round(close_p, 4),
            "actual_direction": actual_dir,
            "is_correct": is_correct,
            "brier_score": round(brier, 4),
            "status": "evaluated",
        }

        try:
            client.table("earnings_predictions").update(update_payload).eq("id", pred_id).execute()
            evaluated_count += 1
            logger.info(
                f"Evaluated earnings prediction {ticker} ({pred.get('model_name')}) on {target_date_str}: "
                f"Pred={predicted_dir}, Actual={actual_dir}, Correct={is_correct}, Brier={brier:.4f}"
            )
        except Exception as e:
            logger.exception(f"Failed to update evaluated earnings prediction {pred_id}: {e}")

    return evaluated_count
