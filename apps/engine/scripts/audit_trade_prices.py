"""Recurring trade-price audit against canonical OHLC bars.

Compares recent trades with the `price_history` bar for the same session, using
the same rule as the one-off audit in wiki/concepts/trade-price-audit.md. Rows
already carrying an audit_flag are treated as annotated, not as new violations.

Piggybacked on .github/workflows/audit.yml; exits 1 when it finds an unannotated
impossible price or a fill on a non-trading day.

    ./apps/engine/.venv/bin/python3 apps/engine/scripts/audit_trade_prices.py --since-days 7
"""

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.db import get_supabase_client  # noqa: E402
from trading.market_calendar import is_us_trading_day  # noqa: E402

# 5 bps model slippage on each side plus rounding headroom. A fill further than
# this outside the session range cannot be explained by the execution model.
OUT_OF_RANGE_PCT = 0.6
BLOCKING_FLAGS = {"NON_TRADING_DAY", "PRICE_OUTSIDE_DAY_RANGE"}
ET = ZoneInfo("America/New_York")
PAGE_SIZE = 1000


def _session_date(timestamp: str) -> str:
    """US equity session in ET. A 02:36 UTC fill is still the prior ET session."""
    return datetime.fromisoformat(timestamp).astimezone(ET).date().isoformat()


@dataclass(frozen=True)
class Violation:
    trade_id: str
    ticker: str
    executed_at: str
    flag: str
    detail: str


@dataclass(frozen=True)
class AuditReport:
    new_violations: list[Violation]
    counts: dict[str, int]


def classify_trade(trade: dict, bar: dict | None, out_of_range_pct: float = OUT_OF_RANGE_PCT) -> str | None:
    """Return a flag for an unannotated trade, or None when no new action is needed."""
    if trade.get("audit_flag"):
        return None

    session_date = _session_date(str(trade["executed_at"]))
    if bar is None:
        return "NO_BAR" if is_us_trading_day(date.fromisoformat(session_date)) else "NON_TRADING_DAY"

    price = float(trade["price"])
    close = float(bar.get("close") or bar.get("price") or 0)
    if close <= 0:
        return "NO_BAR"
    low = float(bar.get("low") if bar.get("low") is not None else min(price, close))
    high = float(bar.get("high") if bar.get("high") is not None else max(price, close))
    excess_pct = max(low - price, price - high, 0.0) / close * 100
    return "PRICE_OUTSIDE_DAY_RANGE" if excess_pct > out_of_range_pct else None


def audit_trades(trades: list[dict], bars: dict[tuple[str, str], dict]) -> AuditReport:
    """Classify every trade and keep only unannotated blocking violations."""
    violations: list[Violation] = []
    counts = {"audited": len(trades), "clean": 0, "no_bar": 0, "already_annotated": 0, "new_violations": 0}

    for trade in trades:
        if trade.get("audit_flag"):
            counts["already_annotated"] += 1
            continue
        ticker = str(trade.get("ticker", "")).upper()
        key = (ticker, _session_date(str(trade["executed_at"])))
        flag = classify_trade(trade, bars.get(key))
        if flag in BLOCKING_FLAGS:
            violations.append(
                Violation(
                    trade_id=str(trade.get("id", "")),
                    ticker=ticker,
                    executed_at=str(trade["executed_at"]),
                    flag=flag,
                    detail=f"recorded_price={trade['price']} bar={bars.get(key)}",
                )
            )
            counts["new_violations"] += 1
        elif flag == "NO_BAR":
            counts["no_bar"] += 1
        else:
            counts["clean"] += 1

    return AuditReport(new_violations=violations, counts=counts)


def _select_all(
    client, table: str, columns: str, since: str, timestamp_column: str, tickers: list[str] | None
) -> list[dict]:
    rows: list[dict] = []
    offset = 0
    while True:
        query = (
            client.table(table)
            .select(columns)
            .gte(timestamp_column, since)
            .order(timestamp_column, desc=False)
            .limit(PAGE_SIZE)
            .offset(offset)
        )
        if tickers:
            query = query.in_("ticker", tickers)
        batch = query.execute().data or []
        rows.extend(batch)
        if len(batch) < PAGE_SIZE:
            return rows
        offset += PAGE_SIZE


def _fetch_recent(client, since: str) -> tuple[list[dict], dict[tuple[str, str], dict]]:
    trades = _select_all(client, "trades", "id,ticker,executed_at,price,audit_flag", since, "executed_at", None)
    tickers = sorted({str(t.get("ticker", "")).upper() for t in trades if t.get("ticker")})
    if not tickers:
        return trades, {}

    rows = _select_all(
        client, "price_history", "ticker,fetched_at,open,high,low,close,price", since, "fetched_at", tickers
    )
    bars: dict[tuple[str, str], dict] = {}
    for row in rows:
        key = (str(row.get("ticker", "")).upper(), str(row.get("fetched_at", ""))[:10])
        bars.setdefault(key, row)
    return trades, bars


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--since-days", type=int, default=7, help="Lookback window in days")
    args = parser.parse_args(argv)

    since = (datetime.now(UTC) - timedelta(days=args.since_days)).isoformat()
    trades, bars = _fetch_recent(get_supabase_client(), since)
    report = audit_trades(trades, bars)
    print(json.dumps({"counts": report.counts, "violations": [v.__dict__ for v in report.new_violations]}, indent=2))
    return 1 if report.new_violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
