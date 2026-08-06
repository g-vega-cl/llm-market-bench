import asyncio
import os
import sys
from datetime import UTC, datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import logger
from core.db import get_supabase_client


def calculate_brier_score(predicted_direction: str, confidence: float, actual_direction: str) -> float:
    """Calculate Brier Score for binary outcome.

    Confidence is expressed as percentage (50-100%).
    Forecast probability p = confidence / 100.0.
    Actual outcome y = 1.0 if prediction was correct, else 0.0.
    Brier Score = (p - y)^2. Lower score is better (0.0 is perfect calibration).
    """
    is_correct = predicted_direction.upper() == actual_direction.upper()
    p = float(confidence) / 100.0
    y = 1.0 if is_correct else 0.0
    return float((p - y) ** 2)


async def fetch_intraday_open_close(ticker: str, target_date_str: str) -> tuple[float | None, float | None]:
    """Fetch Open and Close prices for ticker on target_date via canonical MarketDataManager (FMP)."""
    try:
        from execution.market_data import MarketDataManager

        mdm = MarketDataManager()
        history = await mdm.get_history(ticker, days=10)

        if history:
            for entry in history:
                fetched_at = entry.get("fetched_at", "")
                date_part = fetched_at[:10]
                if date_part == target_date_str:
                    open_price = float(entry.get("open", entry["price"]))
                    close_price = float(entry["price"])
                    return open_price, close_price

    except Exception as e:
        logger.warning(f"Error fetching intraday prices via MarketDataManager for {ticker} on {target_date_str}: {e}")

    return None, None


async def evaluate_daily_predictions() -> int:
    """Evaluate all pending daily predictions against actual market Open vs Close prices."""
    client = get_supabase_client()

    response = client.table("daily_predictions").select("*").eq("status", "pending").execute()

    pending = response.data
    if not pending:
        logger.info("No pending daily predictions found to evaluate.")
        return 0

    evaluated_count = 0

    for pred in pending:
        pred_id = pred["id"]
        ticker = pred["ticker"]
        target_date_str = pred["target_date"]
        predicted_dir = pred["predicted_direction"]
        confidence = pred.get("confidence", 50.0)

        open_p, close_p = await fetch_intraday_open_close(ticker, target_date_str)
        if open_p is None or close_p is None:
            logger.warning(
                f"Could not retrieve Open/Close price for {ticker} on {target_date_str}. Skipping evaluation."
            )
            continue

        actual_dir = "UP" if close_p >= open_p else "DOWN"
        is_correct = predicted_dir.upper() == actual_dir
        brier_score = calculate_brier_score(predicted_dir, confidence, actual_dir)

        client.table("daily_predictions").update(
            {
                "open_price": open_p,
                "close_price": close_p,
                "actual_direction": actual_dir,
                "is_correct": is_correct,
                "brier_score": brier_score,
                "status": "evaluated",
                "updated_at": datetime.now(UTC).isoformat(),
            }
        ).eq("id", pred_id).execute()

        evaluated_count += 1
        logger.info(
            f"Evaluated daily prediction {pred_id} ({ticker} on {target_date_str}): "
            f"Predicted {predicted_dir}, Actual {actual_dir} (Open: {open_p:.2f}, Close: {close_p:.2f}). "
            f"Correct: {is_correct}, Brier: {brier_score:.4f}"
        )

    return evaluated_count


if __name__ == "__main__":
    asyncio.run(evaluate_daily_predictions())
