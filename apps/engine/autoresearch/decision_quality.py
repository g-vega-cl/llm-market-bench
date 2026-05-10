"""Decision quality analysis for auto-research evaluation.

Computes signal concordance, mistake pattern detection, and conviction
calibration from decision logs and realized trade outcomes.

Both `concordance` and `conviction_calibration` are tied to realized PnL —
the previous heuristic versions (reasoning-keyword scan and SELL-frequency
monotonicity) had no relationship to trading outcomes and have been replaced.
"""

import logging
from collections import Counter
from datetime import date

from core.db import get_supabase_client

logger = logging.getLogger("engine")


def _fetch_decisions(sb_client, owner_ids: frozenset | set, week_start: date, week_end: date) -> list[dict]:
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
    return res.data or []


def _fetch_trades(sb_client, owner_ids: frozenset | set, week_start: date, week_end: date) -> list[dict]:
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
    return res.data or []


def _compute_concordance(decisions: list[dict], trades: list[dict]) -> float:
    """Fraction of BUY decisions whose follow-on SELL realized positive PnL.

    A BUY is "concordant" when the position was eventually closed for a
    profit during the same evaluation window. BUYs that never closed are
    excluded from the denominator (unresolved).
    """
    sell_pnl_by_ticker: dict[str, float] = {}
    for t in trades:
        if t.get("signal") == "SELL":
            ticker = (t.get("ticker") or "").upper()
            sell_pnl_by_ticker[ticker] = sell_pnl_by_ticker.get(ticker, 0.0) + float(t.get("realized_pnl") or 0)

    buys = [d for d in decisions if (d.get("signal") or "").upper() == "BUY" and d.get("status") == "EXECUTED"]
    resolved_buys = [d for d in buys if (d.get("ticker") or "").upper() in sell_pnl_by_ticker]
    if not resolved_buys:
        return 0.5  # No closed positions to score against — neutral.

    winners = sum(1 for d in resolved_buys if sell_pnl_by_ticker[(d.get("ticker") or "").upper()] > 0)
    return winners / len(resolved_buys)


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


def compute_decision_quality(
    owner_ids: frozenset | set,
    week_start: date,
    week_end: date,
) -> dict:
    """Compute decision quality metrics for the given agents and week.

    Returns a dict with: concordance, mistake_patterns, conviction_calibration,
    rejection_rate, and raw sample data for the LLM report.
    """
    sb_client = get_supabase_client()
    decisions = _fetch_decisions(sb_client, owner_ids, week_start, week_end)
    trades = _fetch_trades(sb_client, owner_ids, week_start, week_end)

    result = {
        "concordance": 0.0,
        "conviction_calibration": 0.0,
        "regime_awareness": 0.0,
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

    result["concordance"] = _compute_concordance(decisions, trades)
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
