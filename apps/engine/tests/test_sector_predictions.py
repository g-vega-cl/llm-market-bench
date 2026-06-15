# Assuming these modules will be created
from tasks.evaluate_predictions import calculate_pair_percentile_score, calculate_percentile_score


def test_calculate_percentile_score():
    """Test the percentile ranking calculation for sector prediction evaluation."""
    # Mock universe of sector returns
    sector_returns = {"XLK": 10.0, "XLF": 5.0, "XLV": 2.0, "XLE": -1.0, "XLU": -5.0}

    # Highest return (10.0) out of 5 items should be 100th percentile
    # Lowest return (-5.0) out of 5 items should be 0th percentile
    # Middle return (2.0) should be 50th percentile

    assert calculate_percentile_score("XLK", sector_returns) == 100.0
    assert calculate_percentile_score("XLU", sector_returns) == 0.0
    assert calculate_percentile_score("XLV", sector_returns) == 50.0

    # Test pair percentile
    # Pair XLK, XLF is the highest (avg 7.5), should be 100.0
    assert calculate_pair_percentile_score(["XLK", "XLF"], sector_returns) == 100.0
    # Pair XLE, XLU is the lowest (avg -3.0), should be 0.0
    assert calculate_pair_percentile_score(["XLE", "XLU"], sector_returns) == 0.0
