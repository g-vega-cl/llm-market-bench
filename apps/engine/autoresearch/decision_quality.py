"""Decision quality analysis for auto-research evaluation.

Computes conviction calibration, regime awareness, and mistake pattern
detection from decision logs and realized trade outcomes.

Concordance is computed externally in the evaluator from equity change
(experiment vs control total_return_pct), not from BUY-SELL pairs here.
"""

import logging
from collections import Counter
from datetime import date

from core.db import get_async_supabase_client

logger = logging.getLogger("engine")


async def _fetch_decisions(sb_client, owner_ids: frozenset | set, week_start: date, week_end: date) -> list[dict]:
    owner_list = list(owner_ids)
    res = (
        sb_client.table("decisions")
        .select("ticker, signal, confidence, reasoning, status, model_name, metadata, created_at")
        .in_("model_name", owner_list)
        .gte("created_at", week_start.isoformat())
        .lte("created_at", f"{week_end.isoformat()}T23:59:59")
        .order("created_at")
        .execute()
    )
    return (await res).data or []


async def _fetch_trades(sb_client, owner_ids: frozenset | set, week_start: date, week_end: date) -> list[dict]:
    owner_list = list(owner_ids)
    res = (
        sb_client.table("trades")
        .select("ticker, signal, price, realized_pnl, executed_at, portfolios!inner(owner_id)")
        .in_("portfolios.owner_id", owner_list)
        .gte("executed_at", week_start.isoformat())
        .lte("executed_at", f"{week_end.isoformat()}T23:59:59")
        .order("executed_at")
        .execute()
    )
    return (await res).data or []


async def _compute_vixy_trend(sb_client, week_start: date, week_end: date) -> float:
    """Compute VIXY trend: 1.0 if VIXY went up (fear), 0.0 if down (calm).

    Compares week's average VIXY to the price just before the week started.
    Returns 0.5 (neutral) if VIXY data is unavailable or flat within 2%."""
    pre_res = (
        sb_client.table("price_history")
        .select("price")
        .eq("ticker", "VIXY")
        .lt("fetched_at", week_start.isoformat())
        .order("fetched_at", desc=True)
        .limit(1)
        .execute()
    )
    week_res = (
        sb_client.table("price_history")
        .select("price")
        .eq("ticker", "VIXY")
        .gte("fetched_at", week_start.isoformat())
        .lte("fetched_at", f"{week_end.isoformat()}T23:59:59")
        .order("fetched_at")
        .execute()
    )
    pre_rows = (await pre_res).data or []
    week_rows = (await week_res).data or []
    if not pre_rows or not week_rows:
        return 0.5

    pre_vixy = float(pre_rows[0].get("price") or 0)
    week_avg = sum(float(r.get("price") or 0) for r in week_rows) / len(week_rows)
    if pre_vixy <= 0 or week_avg <= 0:
        return 0.5

    change_pct = (week_avg - pre_vixy) / pre_vixy
    if change_pct > 0.02:
        return 1.0  # Fear — VIXY rose
    elif change_pct < -0.02:
        return 0.0  # Calm — VIXY fell
    return 0.5  # Flat


def _compute_regime_awareness(decisions: list[dict], vixy_trend: float) -> float:
    """Score 0-1: how well agent's BUY/SELL mix matches VIXY regime.

    VIXY up (fear, trend 1.0): agent should SELL more → high sell_ratio is good.
    VIXY down (calm, trend 0.0): agent should BUY more → low sell_ratio is good.

    Formula: 1.0 - abs(vixy_trend - sell_ratio)"""
    buys = [d for d in decisions if (d.get("signal") or "").upper() == "BUY"]
    sells = [d for d in decisions if (d.get("signal") or "").upper() == "SELL"]
    total = len(buys) + len(sells)
    if total == 0:
        return 0.5

    sell_ratio = len(sells) / total
    return round(1.0 - abs(vixy_trend - sell_ratio), 4)


def _compute_conviction_calibration(decisions: list[dict], trades: list[dict]) -> float:
    """1.0 when higher-confidence trades realize higher average PnL.

    Buckets executed SELL decisions by confidence (low/med/high) and checks
    whether average realized PnL increases monotonically with confidence.
    """
    sell_decisions = [
        d for d in decisions
        if (d.get("signal") or "").upper() == "SELL" and d.get("status") == "EXECUTED"
    ]
    pnl_by_ticker: dict[str, float] = {}
    for t in trades:
        if t.get("signal") == "SELL":
            ticker = (t.get("ticker") or "").upper()
            pnl_by_ticker[ticker] = pnl_by_ticker.get(ticker, 0.0) + float(t.get("realized_pnl") or 0)

    buckets: dict[str, list[float]] = {"low": [], "med": [], "high": []}
    for d in sell_decisions:
        ticker = (d.get("ticker") or "").upper()
        if ticker not in pnl_by_ticker:
            continue
        conf = d.get("confidence")
        if conf is None:
            conf = 50
        bucket = "low" if conf <= 33 else ("med" if conf <= 66 else "high")
        buckets[bucket].append(pnl_by_ticker[ticker])

    means = []
    for label in ("low", "med", "high"):
        if buckets[label]:
            means.append((label, sum(buckets[label]) / len(buckets[label])))

    if len(means) < 2:
        return 0.5

    is_monotonic = all(means[i][1] <= means[i + 1][1] for i in range(len(means) - 1))
    if is_monotonic:
        # Reward strict separation: high - low gap relative to absolute scale.
        spread = means[-1][1] - means[0][1]
        return 1.0 if spread > 0 else 0.7
    return 0.3


async def compute_decision_quality(
    owner_ids: frozenset | set,
    week_start: date,
    week_end: date,
) -> dict:
    """Compute decision quality metrics for the given agents and week.

    Returns a dict with: concordance, mistake_patterns, conviction_calibration,
    rejection_rate, regime_awareness, and raw sample data for the LLM report.
    """
    sb_client = await get_async_supabase_client()
    decisions = await _fetch_decisions(sb_client, owner_ids, week_start, week_end)
    trades = await _fetch_trades(sb_client, owner_ids, week_start, week_end)

    vixy_trend = await _compute_vixy_trend(sb_client, week_start, week_end)
    regime_awareness = _compute_regime_awareness(decisions, vixy_trend)

    result = {
        "concordance": 0.0,
        "conviction_calibration": 0.0,
        "regime_awareness": regime_awareness,
        "mistake_patterns": [],
        "rejection_rate": 0.0,
        "total_decisions": len(decisions),
        "total_trades": len(trades),
        "sample_wins": [],
        "sample_losses": [],
        "sample_rejections": [],
    }

    if not decisions:
        return result

    rejected = [d for d in decisions if (d.get("status") or "").startswith("REJECTED")]
    result["rejection_rate"] = len(rejected) / len(decisions)

    rejection_reasons = Counter()
    for d in rejected:
        reason = d.get("status") or "UNKNOWN"
        rejection_reasons[reason] += 1
    result["mistake_patterns"] = rejection_reasons.most_common(5)

    result["conviction_calibration"] = _compute_conviction_calibration(decisions, trades)

    win_trades = sorted(
        [t for t in trades if (t.get("realized_pnl") or 0) > 0],
        key=lambda t: abs(t.get("realized_pnl") or 0), reverse=True,
    )
    for t in win_trades[:2]:
        ticker = t["ticker"]
        decision = next(
            (d for d in decisions if (d.get("ticker") or "").upper() == ticker.upper() and d.get("signal") == "SELL"),
            None,
        )
        result["sample_wins"].append({
            "ticker": ticker,
            "pnl": float(t.get("realized_pnl") or 0),
            "reasoning": (decision.get("reasoning", "")[:500] if decision else "N/A"),
        })

    loss_trades = sorted(
        [t for t in trades if (t.get("realized_pnl") or 0) < 0],
        key=lambda t: abs(t.get("realized_pnl") or 0), reverse=True,
    )
    for t in loss_trades[:2]:
        ticker = t["ticker"]
        decision = next(
            (d for d in decisions if (d.get("ticker") or "").upper() == ticker.upper() and d.get("signal") == "SELL"),
            None,
        )
        result["sample_losses"].append({
            "ticker": ticker,
            "pnl": float(t.get("realized_pnl") or 0),
            "reasoning": (decision.get("reasoning", "")[:500] if decision else "N/A"),
        })

    for d in rejected[:2]:
        result["sample_rejections"].append({
            "ticker": d.get("ticker") or "",
            "signal": d.get("signal", ""),
            "status": d.get("status", ""),
            "reasoning": (d.get("reasoning", "")[:500]),
        })

    return result
