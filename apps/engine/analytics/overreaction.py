"""Market Overreaction and Structural Repricing Audit Analytics Engine.

Determines whether an asset's sharp price decline or surge represents:
1. STATISTICAL_OVERREACTION:
   - Move exceeds 2.2-sigma of historical return distribution.
   - RVOL >= 2.0 (capitulation volume / institutional turnover).
   - Actual price move exceeds >= 1.8x options-implied daily move cone.
   - Fundamental consensus targets and revisions remain intact (high reversion probability).
2. JUSTIFIED_REPRICING:
   - Price drop matched by severe downward analyst consensus price target cuts (<= -15%) or
     fundamental deterioration (falling knife risk).
3. NORMAL_VOLATILITY:
   - Price move within normal 1.5-sigma bounds and expected options cone.
"""

import math
from typing import Any

import httpx

from analytics.options_surface import get_options_vol_surface_report
from core.config import FMP_API_KEY, logger
from execution.market_data import MarketDataManager


async def fetch_analyst_targets(ticker: str) -> list[dict[str, Any]]:
    """Fetch analyst price targets and recommendations consensus from FMP."""
    if not FMP_API_KEY:
        return []

    url = "https://financialmodelingprep.com/stable/price-target-consensus"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params={"symbol": ticker.upper(), "apikey": FMP_API_KEY})
            if resp.status_code == 200:
                data = resp.json()
                return data if isinstance(data, list) else [data]
    except Exception as e:
        logger.debug(f"Could not fetch analyst targets for {ticker}: {e}")
    return []


def calculate_return_shock_zscore(current_return_pct: float, closes: list[float]) -> tuple[float, float]:
    """Calculate Z-score of today's return against historical close-to-close daily returns.

    Returns:
        tuple of (z_score, daily_std_pct)
    """
    if not closes or len(closes) < 3:
        return 0.0, 2.0

    valid_closes = [float(p) for p in closes if p and float(p) > 0]
    if len(valid_closes) < 3:
        return 0.0, 2.0

    pct_returns = [
        ((valid_closes[i] - valid_closes[i - 1]) / valid_closes[i - 1]) * 100.0 for i in range(1, len(valid_closes))
    ]

    n = len(pct_returns)
    mean_ret = sum(pct_returns) / n
    variance = sum((r - mean_ret) ** 2 for r in pct_returns) / (n - 1 if n > 1 else 1)
    daily_std = math.sqrt(variance)

    if daily_std <= 1e-4:
        return 0.0, 0.0

    z_score = (current_return_pct - mean_ret) / daily_std
    return round(z_score, 2), round(daily_std, 2)


def classify_overreaction(
    change_pct: float,
    z_score: float,
    rvol: float,
    cone_multiplier: float,
    consensus_cut_pct: float | None,
) -> str:
    """Classify market move into STATISTICAL_OVERREACTION, JUSTIFIED_REPRICING, or NORMAL_VOLATILITY."""
    abs_z = abs(z_score)

    # 1. Structural Repricing: Downward price move matched by explicit downward target/estimate revision
    if (change_pct <= -5.0 or z_score <= -1.5) and consensus_cut_pct is not None and consensus_cut_pct <= -15.0:
        return "JUSTIFIED_REPRICING"

    # 2. Statistical Overreaction: Requires significant return shock, move exceeding cone, AND high volume capitulation
    if abs_z >= 2.0 and cone_multiplier >= 1.8 and rvol >= 1.8:
        if consensus_cut_pct is not None and consensus_cut_pct <= -15.0:
            return "JUSTIFIED_REPRICING"
        return "STATISTICAL_OVERREACTION"

    return "NORMAL_VOLATILITY"


def format_overreaction_report_markdown(data: dict[str, Any]) -> str:
    """Format overreaction analysis into structured Markdown."""
    ticker = data.get("ticker", "N/A")
    verdict = data.get("verdict", "NORMAL_VOLATILITY")
    spot = data.get("spot_price", 0.0)
    change_pct = data.get("change_pct", 0.0)
    z_score = data.get("z_score", 0.0)
    daily_std = data.get("daily_std_pct", 0.0)
    rvol = data.get("rvol", 1.0)
    cone_pct = data.get("options_cone_pct", 0.0)
    cone_mult = data.get("cone_multiplier", 1.0)
    target_cut = data.get("consensus_target_change_pct")
    upside_pct = data.get("consensus_upside_pct")
    target_str = f"{target_cut:+.1f}%" if target_cut is not None else "Intact / No Cut Reported"
    upside_str = f"{upside_pct:+.1f}%" if upside_pct is not None else "N/A"

    verdict_badge = f"**`{verdict}`**"
    if verdict == "STATISTICAL_OVERREACTION":
        explanation = (
            "⚠️ **Setup: Mean-Reversion Opportunity**. The price move represents a statistical tail-risk shock "
            "(>1.8x daily options cone with capitulation volume RVOL >= 1.8x) while underlying analyst estimates "
            "remain intact. Watch for liquidity bounce / oversold reversal."
        )
    elif verdict == "JUSTIFIED_REPRICING":
        explanation = (
            "🚨 **Setup: Structural Repricing Warning**. The selloff is confirmed by severe downward revisions "
            "to forward consensus price targets / earnings estimates. Do NOT catch falling knives."
        )
    else:
        explanation = "ℹ️ **Setup: Normal Market Fluctuation**. The price move is within standard 1.5-sigma bounds."

    return (
        f"### 🎯 Market Overreaction Audit: {ticker}\n\n"
        f"- **Verdict**: {verdict_badge}\n"
        f"- **Spot Price**: `${spot:.2f}` (`{change_pct:+.2f}%` today)\n"
        f"- **Return Shock Z-Score**: `{z_score:+.2f}σ` (vs 20d daily baseline `±{daily_std:.2f}%`)\n"
        f"- **Relative Volume (RVOL)**: `{rvol:.2f}x` 20d ADV\n"
        f"- **Options 1-Sigma Daily Cone**: `±{cone_pct:.2f}%` (Actual move is **`{cone_mult:.2f}x`** the cone)\n"
        f"- **Consensus Target Revision**: `{target_str}` (Target Upside: `{upside_str}`)\n\n"
        f"{explanation}"
    )


async def audit_price_overreaction_report(ticker: str, lookback_days: int = 20) -> dict[str, Any]:
    """Execute overreaction audit for a given ticker."""
    ticker = ticker.upper().strip()
    try:
        lookback_days = int(lookback_days)
    except (ValueError, TypeError):
        lookback_days = 20

    mdm = MarketDataManager()

    # 1. Fetch quote and recent history
    quote = await mdm.get_quote(ticker)
    spot_price = float(getattr(quote, "price", 0.0) or 0.0)
    change_pct = float(getattr(quote, "change_percent", 0.0) or 0.0)
    today_vol = float(getattr(quote, "volume", 0.0) or 0.0)
    avg_vol = float(getattr(quote, "avg_volume", 0.0) or 0.0)

    # 2. Fetch history for daily return standard deviation
    closes: list[float] = []
    try:
        bars = await mdm.get_history(ticker, days=lookback_days + 10)
        if bars:
            for b in bars[:lookback_days]:
                px = b.get("price") if isinstance(b, dict) else getattr(b, "close", getattr(b, "price", None))
                if px:
                    closes.append(float(px))
            closes.reverse()
    except Exception as e:
        logger.warning(f"Could not fetch price history for {ticker} overreaction audit: {e}", exc_info=True)

    z_score, daily_std = calculate_return_shock_zscore(change_pct, closes)

    # 3. Calculate RVOL
    rvol = round(today_vol / avg_vol, 2) if avg_vol > 0 and today_vol > 0 else 1.0

    # 4. Fetch options implied daily move cone
    options_rep = await get_options_vol_surface_report(ticker=ticker)
    cone_pct = float(options_rep.get("implied_daily_move_pct") or 2.0)
    cone_mult = round(abs(change_pct) / (cone_pct if cone_pct > 0 else 2.0), 2)

    # 5. Fetch consensus target adjustments vs revisions
    target_revision_pct: float | None = None
    target_upside_pct: float | None = None
    try:
        targets_data = await fetch_analyst_targets(ticker)
        if targets_data and isinstance(targets_data, list):
            tgt = targets_data[0]
            consensus_target = float(tgt.get("consensusTarget") or tgt.get("targetConsensus") or 0.0)
            if consensus_target > 0 and spot_price > 0:
                target_upside_pct = round(((consensus_target - spot_price) / spot_price) * 100.0, 1)

            prior_target = float(
                tgt.get("targetPrior") or tgt.get("consensusTargetPrior") or tgt.get("targetConsensusPrior") or 0.0
            )
            if consensus_target > 0 and prior_target > 0:
                target_revision_pct = round(((consensus_target - prior_target) / prior_target) * 100.0, 1)
    except Exception as e:
        logger.warning(f"Error checking analyst targets for {ticker}: {e}", exc_info=True)

    verdict = classify_overreaction(change_pct, z_score, rvol, cone_mult, target_revision_pct)

    data = {
        "status": "OK",
        "ticker": ticker,
        "verdict": verdict,
        "spot_price": spot_price,
        "change_pct": change_pct,
        "z_score": z_score,
        "daily_std_pct": daily_std,
        "rvol": rvol,
        "options_cone_pct": cone_pct,
        "cone_multiplier": cone_mult,
        "consensus_target_change_pct": target_revision_pct,
        "consensus_upside_pct": target_upside_pct,
    }
    data["markdown"] = format_overreaction_report_markdown(data)
    return data
