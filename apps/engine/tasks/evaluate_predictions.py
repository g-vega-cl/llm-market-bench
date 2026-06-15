import asyncio
import os
import sys
from datetime import UTC, datetime

# Add the engine root directory to path for sibling package imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import logger
from core.db import get_supabase_client
from execution.providers.factory import get_financial_provider

# Standard universe of major sector ETFs used for benchmarking
SECTOR_TICKERS = ["XLK", "SMH", "XLE", "XLF", "XLV", "XLY", "XLI", "XLB", "XLU", "XLRE", "XLC", "XOP", "XME", "XBI"]


def calculate_percentile_score(target_ticker: str, sector_returns: dict[str, float]) -> float:
    """
    Calculate the percentile score of a target ticker relative to all other sectors.
    Returns 0.0 to 100.0.
    """
    target_ticker = target_ticker.upper()
    normalized_returns = {k.upper(): v for k, v in sector_returns.items()}

    if target_ticker not in normalized_returns:
        return 0.0

    all_returns = list(normalized_returns.values())
    if not all_returns:
        return 0.0

    target_return = normalized_returns[target_ticker]
    # Calculate percentile such that lowest is 0 and highest is 100
    if len(all_returns) <= 1:
        return 100.0
    rank = sum(1 for r in all_returns if r < target_return)
    percentile = (rank / (len(all_returns) - 1)) * 100.0
    return float(percentile)


def calculate_pair_percentile_score(target_pair: list[str], sector_returns: dict[str, float]) -> float:
    """
    Calculate the percentile score of the average return of a target pair
    relative to all possible pairs in the sector universe.
    Returns 0.0 to 100.0.
    """
    if not target_pair or len(target_pair) != 2:
        return 0.0

    normalized_returns = {k.upper(): v for k, v in sector_returns.items()}
    t1, t2 = target_pair[0].upper(), target_pair[1].upper()
    if t1 not in normalized_returns or t2 not in normalized_returns:
        return 0.0

    tickers = list(normalized_returns.keys())

    all_pair_returns = []
    for i in range(len(tickers)):
        for j in range(i + 1, len(tickers)):
            avg_ret = (normalized_returns[tickers[i]] + normalized_returns[tickers[j]]) / 2.0
            all_pair_returns.append(avg_ret)

    if not all_pair_returns:
        return 0.0

    target_avg = (normalized_returns[t1] + normalized_returns[t2]) / 2.0
    if len(all_pair_returns) <= 1:
        return 100.0
    rank = sum(1 for r in all_pair_returns if r < target_avg)
    percentile = (rank / (len(all_pair_returns) - 1)) * 100.0
    return float(percentile)


def get_price_for_date(history: list[dict], target_date) -> float | None:
    """Find price closest to or on target_date. Returns None if history is empty."""
    if not history:
        return None

    parsed_history = []
    for entry in history:
        try:
            # Parse date part YYYY-MM-DD
            dt = datetime.strptime(entry["fetched_at"][:10], "%Y-%m-%d").date()
            parsed_history.append((dt, entry["price"]))
        except Exception:
            continue

    if not parsed_history:
        return None

    # Sort chronological (oldest first)
    parsed_history.sort(key=lambda x: x[0])

    # Check for exact match
    for dt, price in parsed_history:
        if dt == target_date:
            return price

    # Fallback to closest available date
    closest_price = None
    min_diff = None
    for dt, price in parsed_history:
        diff = abs((dt - target_date).days)
        if min_diff is None or diff < min_diff:
            min_diff = diff
            closest_price = price

    return closest_price


async def run_evaluation():
    """Find pending sector predictions whose target_date has passed, fetch returns, and score them."""
    client = get_supabase_client()
    today = datetime.now(UTC).date()

    try:
        # Fetch pending predictions where target_date <= today
        response = (
            client.table("sector_predictions")
            .select("*")
            .eq("status", "pending")
            .lte("target_date", today.isoformat())
            .execute()
        )
    except Exception as e:
        logger.exception(f"Failed to query pending predictions from DB: {e}")
        return

    pending = response.data
    if not pending:
        logger.info("No pending sector predictions ripe for evaluation.")
        return

    logger.info(f"Found {len(pending)} pending predictions to evaluate.")
    provider = get_financial_provider()

    # Get unique prediction dates to fetch correlation runs
    prediction_dates = {p["prediction_date"] for p in pending}
    run_tickers_by_date = {}

    for pred_date in prediction_dates:
        try:
            # Query closest correlation run on or before prediction_date
            run_res = (
                client.table("correlation_runs")
                .select("tickers")
                .lte("run_date", pred_date)
                .order("run_date", desc=True)
                .limit(1)
                .execute()
            )
            if run_res.data and run_res.data[0].get("tickers"):
                run_tickers_by_date[pred_date] = run_res.data[0]["tickers"]
            else:
                run_tickers_by_date[pred_date] = SECTOR_TICKERS
        except Exception as e:
            logger.warning(f"Failed to query correlation run for {pred_date}: {e}")
            run_tickers_by_date[pred_date] = SECTOR_TICKERS

    # Collect all unique tickers we need to fetch history for
    tickers_to_fetch = set()
    for p in pending:
        pred_date = p["prediction_date"]
        # Add tickers from this prediction's reference universe
        ref_tickers = run_tickers_by_date.get(pred_date, SECTOR_TICKERS)
        for t in ref_tickers:
            tickers_to_fetch.add(t.upper())
        # Add predicted sector/pair
        sec = p.get("predicted_sector")
        if sec:
            tickers_to_fetch.add(sec.upper())
        pair = p.get("predicted_pair") or []
        for t in pair:
            if t:
                tickers_to_fetch.add(t.upper())

    # Fetch price history for all needed tickers in parallel
    prices_history = {}

    async def fetch_history_for_ticker(ticker: str, days_needed: int):
        try:
            # Fetch with a small buffer to ensure coverage
            history = await provider.get_history(ticker, days=days_needed + 7)
            prices_history[ticker] = history
        except Exception as e:
            logger.error(f"Failed to fetch history for ticker {ticker}: {e}")

    # Find the maximum days back we need to fetch
    min_pred_date = today
    for p in pending:
        pred_date = datetime.strptime(p["prediction_date"], "%Y-%m-%d").date()
        if pred_date < min_pred_date:
            min_pred_date = pred_date

    days_back = (today - min_pred_date).days

    tasks = [fetch_history_for_ticker(t, days_back) for t in tickers_to_fetch]
    await asyncio.gather(*tasks)

    # Evaluate each prediction
    for p in pending:
        pred_id = p["id"]
        pred_date_str = p["prediction_date"]
        pred_date = datetime.strptime(pred_date_str, "%Y-%m-%d").date()
        target_date = datetime.strptime(p["target_date"], "%Y-%m-%d").date()

        # Get the reference universe specific to this prediction date
        ref_tickers = run_tickers_by_date.get(pred_date_str, SECTOR_TICKERS)
        ref_tickers_upper = {t.upper() for t in ref_tickers}

        # Always include the prediction's specific sector and pair in the universe
        predicted_sec = p.get("predicted_sector")
        if predicted_sec:
            predicted_sec = predicted_sec.upper()
            ref_tickers_upper.add(predicted_sec)

        predicted_pair = p.get("predicted_pair") or []
        predicted_pair = [t.upper() for t in predicted_pair if t]
        for t in predicted_pair:
            ref_tickers_upper.add(t)

        # Calculate returns for the specific reference universe
        sector_returns = {}
        for ticker in ref_tickers_upper:
            history = prices_history.get(ticker, [])
            p_start = get_price_for_date(history, pred_date)
            p_end = get_price_for_date(history, target_date)

            if p_start is not None and p_end is not None and p_start > 0:
                ret = ((p_end / p_start) - 1.0) * 100.0
                sector_returns[ticker] = ret

        if not sector_returns:
            logger.warning(f"No price history found for any sectors for prediction {pred_id}. Skipping.")
            continue

        if predicted_sec not in sector_returns:
            logger.warning(f"Predicted sector {predicted_sec} has no return data. Skipping.")
            continue

        if any(t not in sector_returns for t in predicted_pair):
            logger.warning(f"Predicted pair {predicted_pair} contains tickers without return data. Skipping.")
            continue

        # Compute percentile scores
        sec_score = calculate_percentile_score(predicted_sec, sector_returns)
        pair_score = calculate_pair_percentile_score(predicted_pair, sector_returns)

        try:
            client.table("sector_predictions").update(
                {"sector_percentile_score": sec_score, "pair_percentile_score": pair_score, "status": "evaluated"}
            ).eq("id", pred_id).execute()
            logger.info(
                f"Successfully evaluated prediction {pred_id} (Sector {predicted_sec}: {sec_score:.1f}%, Pair {predicted_pair}: {pair_score:.1f}%)"
            )
        except Exception as e:
            logger.exception(f"Failed to update prediction {pred_id} in database: {e}")


if __name__ == "__main__":
    asyncio.run(run_evaluation())
