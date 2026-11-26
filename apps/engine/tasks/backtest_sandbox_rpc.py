"""Offline SQLite RPC handlers for backtest_autoresearch sandbox execution.

Each helper is kept small (C901 <= 6) and enforces parity with the PostgreSQL
`execute_portfolio_trade` RPC, including idempotency verification and Reg-T/equity updates.
"""

from __future__ import annotations

import math
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

ALLOWED_TEMPORAL_RPCS = frozenset({"match_memories", "match_decisions"})


@dataclass
class _RPCResult:
    data: Any


def _build_rpc_result(payload: dict[str, Any]) -> _RPCResult:
    return _RPCResult(data=payload)


def _replay_sqlite_trade(
    cur: sqlite3.Cursor,
    *,
    portfolio_id: str,
    ticker: str,
    cash: float,
    sma: float,
    total_equity: float | None,
    idem_key: str,
) -> dict[str, Any] | None:
    """Return existing trade payload if idempotency_key was already committed."""
    existing = cur.execute("SELECT * FROM trades WHERE idempotency_key = ?", (idem_key,)).fetchone()
    if not existing:
        return None
    if existing["portfolio_id"] != portfolio_id or str(existing["ticker"]).upper() != ticker:
        raise ValueError(f"Idempotency key {idem_key} already used by another trade")

    pos = cur.execute(
        "SELECT quantity, average_cost_basis FROM portfolio_positions WHERE portfolio_id = ? AND ticker = ?",
        (portfolio_id, ticker),
    ).fetchone()
    return {
        "trade_id": existing["id"],
        "cash_balance": cash,
        "sma": sma,
        "total_equity": total_equity,
        "quantity": existing["quantity"],
        "total_cost": existing["total_cost"],
        "realized_pnl": existing["realized_pnl"],
        "realized_pnl_pct": existing["realized_pnl_pct"],
        "position_quantity": int(pos["quantity"]) if pos else 0,
        "position_avg_cost": float(pos["average_cost_basis"]) if pos else 0.0,
        "idempotent_replay": True,
    }


def _apply_sqlite_buy(
    cur: sqlite3.Cursor,
    *,
    portfolio_id: str,
    ticker: str,
    qty: int,
    price: float,
    cash: float,
    pos: sqlite3.Row | None,
    now_str: str,
) -> dict[str, Any]:
    total_cost = price * qty
    if total_cost > cash:
        raise RuntimeError(f"Insufficient cash balance: need {total_cost}, available {cash}")
    new_cash = cash - total_cost
    if pos:
        new_qty = int(pos["quantity"]) + qty
        new_avg = ((float(pos["average_cost_basis"]) * int(pos["quantity"])) + total_cost) / new_qty
        cur.execute(
            "UPDATE portfolio_positions SET quantity = ?, average_cost_basis = ?, last_updated_at = ? WHERE id = ?",
            (new_qty, new_avg, now_str, pos["id"]),
        )
    else:
        new_qty = qty
        new_avg = price
        cur.execute(
            "INSERT INTO portfolio_positions (id, portfolio_id, ticker, quantity, average_cost_basis, last_updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), portfolio_id, ticker, new_qty, new_avg, now_str),
        )
    return {
        "exec_qty": qty,
        "total_cost": total_cost,
        "new_cash": new_cash,
        "new_qty": new_qty,
        "new_avg": new_avg,
        "realized_pnl": None,
        "realized_pnl_pct": None,
    }


def _apply_sqlite_sell(
    cur: sqlite3.Cursor,
    *,
    portfolio_id: str,
    ticker: str,
    qty: int,
    price: float,
    cash: float,
    pos: sqlite3.Row | None,
    now_str: str,
) -> dict[str, Any]:
    if not pos or int(pos["quantity"]) <= 0:
        raise RuntimeError(f"Position {ticker} not held in portfolio {portfolio_id}")
    held_qty = int(pos["quantity"])
    avg_cost = float(pos["average_cost_basis"])
    exec_qty = min(qty, held_qty)
    total_cost = price * exec_qty
    new_cash = cash + total_cost
    realized_pnl = (price - avg_cost) * exec_qty
    realized_pnl_pct = ((price / avg_cost) - 1) * 100 if avg_cost > 0 else 0.0
    new_qty = held_qty - exec_qty
    if new_qty == 0:
        cur.execute("DELETE FROM portfolio_positions WHERE id = ?", (pos["id"],))
        new_avg = 0.0
    else:
        new_avg = avg_cost
        cur.execute(
            "UPDATE portfolio_positions SET quantity = ?, last_updated_at = ? WHERE id = ?",
            (new_qty, now_str, pos["id"]),
        )
    return {
        "exec_qty": exec_qty,
        "total_cost": total_cost,
        "new_cash": new_cash,
        "new_qty": new_qty,
        "new_avg": new_avg,
        "realized_pnl": realized_pnl,
        "realized_pnl_pct": realized_pnl_pct,
    }


def _compute_sqlite_equity(
    cur: sqlite3.Cursor,
    *,
    portfolio_id: str,
    ticker: str,
    price: float,
    new_cash: float,
    mark_prices: dict[str, Any] | None,
) -> tuple[float, float]:
    rows = cur.execute(
        "SELECT ticker, quantity, average_cost_basis FROM portfolio_positions WHERE portfolio_id = ?",
        (portfolio_id,),
    ).fetchall()
    pos_cost = 0.0
    pos_mv = 0.0
    for row in rows:
        sym = str(row["ticker"]).upper()
        q = int(row["quantity"])
        avg_c = float(row["average_cost_basis"])
        pos_cost += q * avg_c
        mark = float(mark_prices.get(sym) or 0.0) if isinstance(mark_prices, dict) else 0.0
        if mark <= 0:
            mark = price if sym == ticker else avg_c
        pos_mv += q * mark
    return new_cash + pos_cost, new_cash + pos_mv


def execute_sqlite_portfolio_trade(params: dict[str, Any], t_sim: datetime | None, db_path: str) -> _RPCResult:
    """Execute `execute_portfolio_trade` atomically against the local SQLite backtest DB."""
    portfolio_id = params["p_portfolio_id"]
    ticker = str(params["p_ticker"]).upper().strip()
    signal = str(params["p_signal"]).upper().strip()
    qty = int(params["p_quantity"])
    price = float(params["p_price"])
    idem_key = params.get("p_idempotency_key")
    now_str = t_sim.isoformat() if t_sim else datetime.now(UTC).isoformat()

    if not ticker or signal not in ("BUY", "SELL") or qty <= 0 or not math.isfinite(price) or price <= 0:
        raise ValueError(f"Invalid trade params: ticker={ticker}, signal={signal}, qty={qty}, price={price}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("BEGIN IMMEDIATE")
        cur = conn.cursor()
        port = cur.execute(
            "SELECT cash_balance, sma, total_equity FROM portfolios WHERE id = ?",
            (portfolio_id,),
        ).fetchone()
        if not port:
            raise RuntimeError(f"Portfolio {portfolio_id} not found")

        cash = float(port["cash_balance"])
        sma = float(port["sma"] or 0.0)
        if idem_key:
            replay = _replay_sqlite_trade(
                cur,
                portfolio_id=portfolio_id,
                ticker=ticker,
                cash=cash,
                sma=sma,
                total_equity=port["total_equity"],
                idem_key=idem_key,
            )
            if replay is not None:
                conn.commit()
                return _build_rpc_result(replay)

        pos = cur.execute(
            "SELECT id, quantity, average_cost_basis FROM portfolio_positions WHERE portfolio_id = ? AND ticker = ?",
            (portfolio_id, ticker),
        ).fetchone()
        handler = _apply_sqlite_buy if signal == "BUY" else _apply_sqlite_sell
        res = handler(
            cur,
            portfolio_id=portfolio_id,
            ticker=ticker,
            qty=qty,
            price=price,
            cash=cash,
            pos=pos,
            now_str=now_str,
        )

        trade_id = str(uuid.uuid4())
        cur.execute(
            """
            INSERT INTO trades (
                id, portfolio_id, ticker, signal, quantity, price, total_cost,
                executed_at, decision_id, reasoning, realized_pnl, realized_pnl_pct, idempotency_key, alpaca_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                trade_id,
                portfolio_id,
                ticker,
                signal,
                res["exec_qty"],
                price,
                res["total_cost"],
                now_str,
                params.get("p_decision_id"),
                params.get("p_reason"),
                res["realized_pnl"],
                res["realized_pnl_pct"],
                idem_key,
                params.get("p_alpaca_status"),
            ),
        )
        new_realized, new_equity = _compute_sqlite_equity(
            cur,
            portfolio_id=portfolio_id,
            ticker=ticker,
            price=price,
            new_cash=res["new_cash"],
            mark_prices=params.get("p_mark_prices"),
        )
        new_sma = max(0.0, res["new_cash"])
        cur.execute(
            """
            UPDATE portfolios
            SET cash_balance = ?, sma = ?, total_equity = ?, buying_power = ?,
                excess_liquidity = ?, maintenance_margin = 0, realized = ?, last_updated_at = ?
            WHERE id = ?
            """,
            (res["new_cash"], new_sma, new_equity, new_sma, new_sma, new_realized, now_str, portfolio_id),
        )
        conn.commit()
        return _build_rpc_result(
            {
                "trade_id": trade_id,
                "cash_balance": res["new_cash"],
                "sma": new_sma,
                "total_equity": new_equity,
                "quantity": res["exec_qty"],
                "total_cost": res["total_cost"],
                "realized_pnl": res["realized_pnl"],
                "realized_pnl_pct": res["realized_pnl_pct"],
                "position_quantity": res["new_qty"],
                "position_avg_cost": res["new_avg"],
                "idempotent_replay": False,
            }
        )
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _filter_temporal_rpc_rows(
    real_client: Any, fn_name: str, t_sim: datetime, rows: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    row_ids = [r["id"] for r in rows if isinstance(r, dict) and "id" in r]
    if not row_ids:
        return rows

    target_table = "memories" if fn_name == "match_memories" else "decisions"
    meta_res = real_client.table(target_table).select("id, created_at").in_("id", row_ids).execute()
    created_at_map: dict[Any, datetime] = {}
    for row in meta_res.data or []:
        try:
            from dateutil import parser

            dt = parser.isoparse(row["created_at"])
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            created_at_map[row["id"]] = dt
        except Exception:
            continue

    return [r for r in rows if r.get("id") not in created_at_map or created_at_map[r["id"]] <= t_sim]


def build_temporal_rpc_wrapper(real_client: Any, fn_name: str, params: dict[str, Any], t_sim: datetime) -> Any:
    """Wrap allowlisted read-only RPCs with point-in-time `t_sim` filtering; fail closed otherwise."""
    if fn_name not in ALLOWED_TEMPORAL_RPCS:
        raise ValueError(f"RPC '{fn_name}' is not allowlisted in offline backtest sandbox")

    real_rpc = real_client.rpc(fn_name, params)

    class _TemporalRPCWrapper:
        def execute(self):
            res = real_rpc.execute()
            if res.data:
                res.data = _filter_temporal_rpc_rows(real_client, fn_name, t_sim, res.data)
            return res

    return _TemporalRPCWrapper()
