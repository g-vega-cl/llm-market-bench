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


def compute_intraday_hit_metrics(
    predicted_direction: str,
    expected_return_pct: float | None,
    open_price: float,
    high_price: float,
    low_price: float,
) -> tuple[bool, bool]:
    """Compute (intraday_hit, intraday_direction_hit).

    - intraday_direction_hit: True if market price moved in predicted direction at any point during session.
    - intraday_hit: True if market price reached/surpassed predicted expected_return_pct target intraday.
    """
    predicted_dir = predicted_direction.upper()

    if predicted_dir == "UP":
        intraday_direction_hit = high_price > open_price
        target_pct = abs(expected_return_pct) if (expected_return_pct is not None and expected_return_pct != 0) else 0.0
        max_return_pct = ((high_price - open_price) / open_price) * 100.0
        intraday_hit = max_return_pct >= target_pct
    else:  # DOWN
        intraday_direction_hit = low_price < open_price
        target_pct = (
            -abs(expected_return_pct) if (expected_return_pct is not None and expected_return_pct != 0) else 0.0
        )
        min_return_pct = ((low_price - open_price) / open_price) * 100.0
        intraday_hit = min_return_pct <= target_pct

    return intraday_hit, intraday_direction_hit


async def fetch_intraday_prices(
    ticker: str, target_date_str: str
) -> tuple[float | None, float | None, float | None, float | None]:
    """Fetch Open, High, Low, and Close prices for ticker on target_date via MarketDataManager."""
    try:
        from execution.market_data import MarketDataManager

        mdm = MarketDataManager()
        history = await mdm.get_history(ticker, days=10)

        if history:
            for entry in history:
                fetched_at = entry.get("fetched_at", "")
                date_part = fetched_at[:10]
                if date_part == target_date_str:
                    close_price = float(entry["price"])
                    open_price = float(entry.get("open", close_price))
                    high_price = float(entry.get("high", max(open_price, close_price)))
                    low_price = float(entry.get("low", min(open_price, close_price)))
                    return open_price, high_price, low_price, close_price

    except Exception as e:
        logger.warning(f"Error fetching intraday prices via MarketDataManager for {ticker} on {target_date_str}: {e}")

    return None, None, None, None


async def fetch_intraday_open_close(ticker: str, target_date_str: str) -> tuple[float | None, float | None]:
    """Backward compatible helper fetching Open and Close prices."""
    open_p, _high_p, _low_p, close_p = await fetch_intraday_prices(ticker, target_date_str)
    return open_p, close_p


async def evaluate_daily_predictions() -> int:
    """Evaluate all pending daily predictions against actual market Open, High, Low, and Close prices."""
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
        expected_return_pct = pred.get("expected_return_pct")

        open_p, high_p, low_p, close_p = await fetch_intraday_prices(ticker, target_date_str)
        if open_p is None or close_p is None or high_p is None or low_p is None:
            logger.warning(
                f"Could not retrieve Open/High/Low/Close price for {ticker} on {target_date_str}. Skipping evaluation."
            )
            continue

        actual_dir = "UP" if close_p >= open_p else "DOWN"
        is_correct = predicted_dir.upper() == actual_dir
        brier_score = calculate_brier_score(predicted_dir, confidence, actual_dir)
        intraday_hit, intraday_dir_hit = compute_intraday_hit_metrics(
            predicted_direction=predicted_dir,
            expected_return_pct=expected_return_pct,
            open_price=open_p,
            high_price=high_p,
            low_price=low_p,
        )

        client.table("daily_predictions").update(
            {
                "open_price": open_p,
                "high_price": high_p,
                "low_price": low_p,
                "close_price": close_p,
                "actual_direction": actual_dir,
                "is_correct": is_correct,
                "intraday_hit": intraday_hit,
                "intraday_direction_hit": intraday_dir_hit,
                "brier_score": brier_score,
                "status": "evaluated",
                "updated_at": datetime.now(UTC).isoformat(),
            }
        ).eq("id", pred_id).execute()

        # Trigger systematic daily SPY trader portfolio execution
        try:
            from execution.system_portfolios import execute_system_daily_trade

            intraday_data = {
                "open_price": open_p,
                "high_price": high_p,
                "low_price": low_p,
                "close_price": close_p,
                "intraday_hit": intraday_hit,
            }
            await execute_system_daily_trade(prediction=pred, intraday_data=intraday_data)
        except Exception as e:
            logger.exception(f"Failed to execute system daily trade for prediction {pred_id}: {e}")

        evaluated_count += 1
        logger.info(
            f"Evaluated daily prediction {pred_id} ({ticker} on {target_date_str}): "
            f"Predicted {predicted_dir}, Actual {actual_dir} (Open: {open_p:.2f}, High: {high_p:.2f}, Low: {low_p:.2f}, Close: {close_p:.2f}). "
            f"Correct: {is_correct}, IntradayHit: {intraday_hit}, Brier: {brier_score:.4f}"
        )

    return evaluated_count


if __name__ == "__main__":
    asyncio.run(evaluate_daily_predictions())
