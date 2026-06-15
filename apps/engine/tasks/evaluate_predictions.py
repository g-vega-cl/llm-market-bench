import os
import sys

# Add the engine root directory to path for sibling package imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def calculate_percentile_score(target_ticker: str, sector_returns: dict[str, float]) -> float:
    """
    Calculate the percentile score of a target ticker relative to all other sectors.
    Returns 0.0 to 100.0.
    """
    if target_ticker not in sector_returns:
        return 0.0

    all_returns = list(sector_returns.values())
    if not all_returns:
        return 0.0

    target_return = sector_returns[target_ticker]
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

    t1, t2 = target_pair[0], target_pair[1]
    if t1 not in sector_returns or t2 not in sector_returns:
        return 0.0

    tickers = list(sector_returns.keys())

    all_pair_returns = []
    for i in range(len(tickers)):
        for j in range(i + 1, len(tickers)):
            avg_ret = (sector_returns[tickers[i]] + sector_returns[tickers[j]]) / 2.0
            all_pair_returns.append(avg_ret)

    if not all_pair_returns:
        return 0.0

    target_avg = (sector_returns[t1] + sector_returns[t2]) / 2.0
    if len(all_pair_returns) <= 1:
        return 100.0
    rank = sum(1 for r in all_pair_returns if r < target_avg)
    percentile = (rank / (len(all_pair_returns) - 1)) * 100.0
    return float(percentile)
