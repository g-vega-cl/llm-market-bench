"""Alpaca portfolio audit and reconciliation engine.

Reconciles a model's simulated portfolio performance (from Supabase)
against Alpaca brokerage execution, fill prices, slippage, and position state.
"""

import json
import logging
from collections import defaultdict
from datetime import UTC, datetime, timedelta

from alpaca.trading.client import TradingClient
from alpaca.trading.enums import QueryOrderStatus
from alpaca.trading.requests import GetOrdersRequest

from core.config import (
    ALPACA_API_KEY,
    ALPACA_PAPER_ENDPOINT,
    ALPACA_SECRET_KEY,
)
from core.db import get_supabase_client
from execution.market_data import MarketDataManager

logger = logging.getLogger("engine")


class AlpacaAuditReconciler:
    """Reconciles Supabase simulated trades and equity with Alpaca execution."""

    def __init__(
        self,
        supabase_client=None,
        alpaca_client: TradingClient | None = None,
        market_data_manager: MarketDataManager | None = None,
    ):
        self.supabase = supabase_client or get_supabase_client()
        self._alpaca = alpaca_client
        self._mdm = market_data_manager or MarketDataManager()

        if self._alpaca is None and ALPACA_API_KEY and ALPACA_SECRET_KEY:
            try:
                self._alpaca = TradingClient(
                    ALPACA_API_KEY,
                    ALPACA_SECRET_KEY,
                    paper=True,
                    url_override=ALPACA_PAPER_ENDPOINT,
                )
            except Exception as e:
                logger.warning(f"[AlpacaAudit] Could not initialize Alpaca client: {e}")

    async def audit_model_portfolio(self, model_name: str, days: int = 7) -> dict:
        """Run a full reconciliation audit for a specific model."""
        # 1. Fetch Portfolio
        res_p = self.supabase.table("portfolios").select("*").eq("owner_id", model_name).single().execute()
        portfolio = res_p.data
        if not portfolio:
            raise ValueError(f"Portfolio for model '{model_name}' not found in Supabase.")

        portfolio_id = portfolio["id"]
        supabase_equity = float(portfolio.get("total_equity", 10000.0))
        supabase_cash = float(portfolio.get("cash_balance", 10000.0))

        # 2. Fetch Supabase Positions
        res_pos = self.supabase.table("portfolio_positions").select("*").eq("portfolio_id", portfolio_id).execute()
        supabase_positions = res_pos.data or []

        # 3. Fetch Portfolio Performance History (last N days)
        cutoff_date = (datetime.now(UTC) - timedelta(days=days)).strftime("%Y-%m-%d")
        res_perf = (
            self.supabase.table("portfolio_performance")
            .select("*")
            .eq("portfolio_id", portfolio_id)
            .order("date", desc=False)
            .execute()
        )
        perf_history = res_perf.data or []

        chart_start_equity = 10000.0
        chart_end_equity = supabase_equity
        chart_pct_change = 0.0

        if perf_history:
            recent_perf = [p for p in perf_history if p["date"] >= cutoff_date]
            if recent_perf:
                chart_start_equity = float(recent_perf[0]["total_equity"])
                chart_end_equity = float(recent_perf[-1]["total_equity"])
            else:
                chart_start_equity = float(perf_history[0]["total_equity"])
                chart_end_equity = float(perf_history[-1]["total_equity"])

            if chart_start_equity > 0:
                chart_pct_change = ((chart_end_equity - chart_start_equity) / chart_start_equity) * 100

        # 4. Fetch Supabase Trades
        res_trades = (
            self.supabase.table("trades")
            .select("*")
            .eq("portfolio_id", portfolio_id)
            .order("executed_at", desc=False)
            .execute()
        )
        supabase_trades = res_trades.data or []

        # 5. Fetch Alpaca Orders
        alpaca_orders_by_id = {}
        alpaca_orders_by_trade_id = {}

        if self._alpaca:
            try:
                orders = self._alpaca.get_orders(GetOrdersRequest(status=QueryOrderStatus.ALL, limit=500))
                for ord_obj in orders:
                    oid = str(ord_obj.id)
                    alpaca_orders_by_id[oid] = ord_obj
                    cid = getattr(ord_obj, "client_order_id", "") or ""
                    # client_order_id format: {agent_id}__{ticker}__{signal}__{trade_id}
                    if f"{model_name}__" in cid:
                        parts = cid.split("__")
                        if len(parts) >= 4:
                            t_id = parts[3]
                            alpaca_orders_by_trade_id[t_id] = ord_obj
            except Exception as e:
                logger.warning(f"[AlpacaAudit] Error querying Alpaca orders: {e}")

        # 6. Reconcile Trades & Calculate Slippage
        matched_trades = []
        total_slippage_usd = 0.0
        filled_count = 0
        skipped_or_failed_count = 0
        anomalies = []

        # Reconstructed Alpaca state
        alpaca_reconstructed_cash = 10000.0
        alpaca_positions_map = defaultdict(lambda: {"quantity": 0, "total_cost": 0.0})

        for tr in supabase_trades:
            trade_id = str(tr["id"])
            ticker = tr["ticker"]
            signal = tr["signal"].upper()
            qty = int(tr["quantity"])
            sim_price = float(tr["price"])
            sb_status = tr.get("alpaca_status") or "UNKNOWN"

            alpaca_ord = alpaca_orders_by_id.get(tr.get("alpaca_order_id") or "") or alpaca_orders_by_trade_id.get(
                trade_id
            )

            fill_price = None
            order_status = sb_status
            filled_at = tr.get("alpaca_filled_at")

            if alpaca_ord:
                stat_val = (
                    alpaca_ord.status.value if hasattr(alpaca_ord.status, "value") else str(alpaca_ord.status).lower()
                )
                if stat_val == "filled":
                    order_status = "FILLED"
                    fill_price = (
                        float(alpaca_ord.filled_avg_price) if alpaca_ord.filled_avg_price is not None else sim_price
                    )
                    filled_at = getattr(alpaca_ord, "filled_at", filled_at)
                elif "cancel" in stat_val:
                    order_status = "CANCELED"
                elif "reject" in stat_val:
                    order_status = "REJECTED"
                elif "expired" in stat_val:
                    order_status = "EXPIRED"

            if order_status == "FILLED":
                filled_count += 1
                effective_price = fill_price if fill_price is not None else sim_price

                # Slippage = Actual Alpaca cost vs Sim cost
                if signal == "BUY":
                    slippage_usd = (effective_price - sim_price) * qty
                    alpaca_reconstructed_cash -= effective_price * qty
                    alpaca_positions_map[ticker]["quantity"] += qty
                    alpaca_positions_map[ticker]["total_cost"] += effective_price * qty
                else:  # SELL
                    slippage_usd = (sim_price - effective_price) * qty
                    alpaca_reconstructed_cash += effective_price * qty
                    alpaca_positions_map[ticker]["quantity"] -= qty
                    if alpaca_positions_map[ticker]["quantity"] <= 0:
                        alpaca_positions_map[ticker]["total_cost"] = 0.0

                total_slippage_usd += slippage_usd
                slippage_pct = ((effective_price - sim_price) / sim_price) * 100 if sim_price > 0 else 0.0
            else:
                skipped_or_failed_count += 1
                slippage_usd = 0.0
                slippage_pct = 0.0
                effective_price = 0.0
                anomalies.append(
                    {
                        "type": "UNFILLED_OR_SKIPPED_TRADE",
                        "trade_id": trade_id,
                        "ticker": ticker,
                        "signal": signal,
                        "status": order_status,
                        "message": f"Trade {trade_id[:8]} ({signal} {qty} {ticker}) had Alpaca status '{order_status}'",
                    }
                )

            matched_trades.append(
                {
                    "trade_id": trade_id,
                    "ticker": ticker,
                    "signal": signal,
                    "quantity": qty,
                    "sim_price": sim_price,
                    "alpaca_fill_price": effective_price,
                    "slippage_usd": round(slippage_usd, 4),
                    "slippage_pct": round(slippage_pct, 4),
                    "status": order_status,
                    "executed_at": tr.get("executed_at"),
                    "filled_at": str(filled_at) if filled_at else None,
                }
            )

        # 7. Reconcile Positions & Mark-to-Market
        all_tickers = set(alpaca_positions_map.keys()) | {p["ticker"] for p in supabase_positions}
        positions_reconciliation = []
        alpaca_holdings_val = 0.0
        supabase_holdings_val = 0.0

        for ticker in sorted(all_tickers):
            sb_pos = next((p for p in supabase_positions if p["ticker"] == ticker), None)
            sb_qty = int(sb_pos["quantity"]) if sb_pos else 0
            alpaca_qty = alpaca_positions_map[ticker]["quantity"]

            # Skip fully closed positions in both systems
            if sb_qty == 0 and alpaca_qty == 0:
                continue

            price = 0.0
            try:
                quote = await self._mdm.get_quote(ticker)
                if quote and hasattr(quote, "price") and quote.price:
                    price = float(quote.price)
                elif sb_pos and sb_pos.get("average_cost_basis"):
                    price = float(sb_pos["average_cost_basis"])
            except Exception as e:
                logger.warning(f"[AlpacaAudit] Could not fetch price for {ticker}: {e}")
                if sb_pos:
                    price = float(sb_pos.get("average_cost_basis", 0.0))

            sb_val = sb_qty * price
            alp_val = alpaca_qty * price
            supabase_holdings_val += sb_val
            alpaca_holdings_val += alp_val

            delta_qty = alpaca_qty - sb_qty
            if delta_qty != 0:
                anomalies.append(
                    {
                        "type": "POSITION_MISMATCH",
                        "ticker": ticker,
                        "supabase_qty": sb_qty,
                        "alpaca_qty": alpaca_qty,
                        "delta": delta_qty,
                        "message": f"Position mismatch for {ticker}: Supabase={sb_qty}, Alpaca={alpaca_qty} (Delta: {delta_qty})",
                    }
                )

            positions_reconciliation.append(
                {
                    "ticker": ticker,
                    "supabase_qty": sb_qty,
                    "alpaca_qty": alpaca_qty,
                    "delta_qty": delta_qty,
                    "current_price": round(price, 2),
                    "supabase_val": round(sb_val, 2),
                    "alpaca_val": round(alp_val, 2),
                }
            )

        alpaca_reconstructed_equity = alpaca_reconstructed_cash + alpaca_holdings_val
        equity_delta = alpaca_reconstructed_equity - supabase_equity
        equity_delta_pct = (equity_delta / supabase_equity) * 100 if supabase_equity > 0 else 0.0

        avg_slippage = (total_slippage_usd / filled_count) if filled_count > 0 else 0.0

        return {
            "model_name": model_name,
            "portfolio_id": portfolio_id,
            "supabase_equity": round(supabase_equity, 2),
            "supabase_cash": round(supabase_cash, 2),
            "alpaca_reconstructed_equity": round(alpaca_reconstructed_equity, 2),
            "alpaca_reconstructed_cash": round(alpaca_reconstructed_cash, 2),
            "equity_delta": round(equity_delta, 2),
            "equity_delta_pct": round(equity_delta_pct, 4),
            "total_trades": len(supabase_trades),
            "filled_trades": filled_count,
            "skipped_or_failed_trades": skipped_or_failed_count,
            "avg_slippage_usd": round(avg_slippage, 4),
            "total_slippage_usd": round(total_slippage_usd, 4),
            "chart_performance": {
                "start_equity": round(chart_start_equity, 2),
                "end_equity": round(chart_end_equity, 2),
                "pct_change": round(chart_pct_change, 2),
                "days": days,
            },
            "positions": positions_reconciliation,
            "trades": matched_trades,
            "anomalies": anomalies,
        }

    def render_terminal_report(self, audit_data: dict) -> str:
        """Render a clean terminal report with Unicode framing."""
        m = audit_data["model_name"]
        lines = []
        border = "═" * 86

        lines.append(f"╔{border}╗")
        lines.append(f"║ 🔍 ALPACA PORTFOLIO AUDIT REPORT: {m:<50} ║")
        lines.append(f"╠{border}╣")

        # 1. Executive Summary
        cp = audit_data["chart_performance"]
        sign = "+" if cp["pct_change"] >= 0 else ""
        lines.append("║ [1] EXECUTIVE SUMMARY & PERFORMANCE VERIFICATION                            ║")
        lines.append(
            f"║  Site Chart Performance ({cp['days']}d):  {sign}{cp['pct_change']:.2f}% (${cp['start_equity']:,.2f} ➔ ${cp['end_equity']:,.2f})".ljust(
                87
            )
            + "║"
        )
        lines.append("║                                                                              ║")
        lines.append("║  Metric                  Supabase (Sim)      Alpaca (Reconstructed)  Divergence ║")
        lines.append("║  ─────────────────────────────────────────────────────────────────────────── ║")

        eq_delta_sign = "+" if audit_data["equity_delta"] >= 0 else ""
        lines.append(
            f"║  Total Equity            ${audit_data['supabase_equity']:<18,.2f} ${audit_data['alpaca_reconstructed_equity']:<22,.2f} {eq_delta_sign}${audit_data['equity_delta']:,.2f} ({audit_data['equity_delta_pct']:.2f}%)".ljust(
                87
            )
            + "║"
        )
        lines.append(
            f"║  Cash Balance            ${audit_data['supabase_cash']:<18,.2f} ${audit_data['alpaca_reconstructed_cash']:<22,.2f} ${audit_data['alpaca_reconstructed_cash'] - audit_data['supabase_cash']:,.2f}".ljust(
                87
            )
            + "║"
        )
        lines.append(
            f"║  Trades Synced           {audit_data['total_trades']:<19} {audit_data['filled_trades']} Filled, {audit_data['skipped_or_failed_trades']} Non-Fill     Avg Slippage: ${audit_data['avg_slippage_usd']:.2f}/tr".ljust(
                87
            )
            + "║"
        )
        lines.append(f"╠{border}╣")

        # 2. Positions Reconciliation
        lines.append("║ [2] POSITIONS RECONCILIATION                                                ║")
        lines.append("║  Ticker  Supabase Qty  Alpaca Qty  Delta   Current Mkt Price  Supabase Val   Alpaca Val ║")
        lines.append("║  ─────────────────────────────────────────────────────────────────────────── ║")
        if not audit_data["positions"]:
            lines.append("║  (No active positions)                                                       ║")
        for pos in audit_data["positions"]:
            lines.append(
                f"║  {pos['ticker']:<7} {pos['supabase_qty']:<13} {pos['alpaca_qty']:<11} {pos['delta_qty']:<7} ${pos['current_price']:<17,.2f} ${pos['supabase_val']:<13,.2f} ${pos['alpaca_val']:<11,.2f}║"
            )
        lines.append(f"╠{border}╣")

        # 3. Trade Matching & Slippage (Recent 10)
        recent_trades = audit_data["trades"][-10:] if audit_data["trades"] else []
        lines.append("║ [3] RECENT TRADES & EXECUTION SLIPPAGE (Last 10)                             ║")
        lines.append("║  Executed At        Ticker  Side  Qty  Sim Price   Alpaca Fill  Slippage  Status ║")
        lines.append("║  ─────────────────────────────────────────────────────────────────────────── ║")
        if not recent_trades:
            lines.append("║  (No recent trades found)                                                    ║")
        for t in recent_trades:
            dt = t["executed_at"][:16] if t["executed_at"] else "N/A"
            slip_str = f"{'+' if t['slippage_usd'] >= 0 else ''}${t['slippage_usd']:.2f}"
            lines.append(
                f"║  {dt:<18} {t['ticker']:<7} {t['signal']:<5} {t['quantity']:<4} ${t['sim_price']:<10.2f} ${t['alpaca_fill_price']:<11.2f} {slip_str:<9} {t['status']:<7}║"
            )
        lines.append(f"╠{border}╣")

        # 4. Anomalies
        lines.append("║ [4] DISCREPANCIES & ROOT-CAUSE ANOMALIES                                     ║")
        if not audit_data["anomalies"]:
            lines.append("║  ✅ No position mismatches or rejected Alpaca trades detected. Clean audit!  ║")
        else:
            for an in audit_data["anomalies"]:
                lines.append(f"║  ⚠️  {an['message'][:78]:<78} ║")

        lines.append(f"╚{border}╝")
        return "\n".join(lines)


async def run_alpaca_audit(
    model_name: str | None = None,
    days: int = 7,
    json_output: bool = False,
) -> dict:
    """CLI Entry point for Alpaca audit."""
    target_model = model_name or "MiniMax-M3"
    reconciler = AlpacaAuditReconciler()
    result = await reconciler.audit_model_portfolio(model_name=target_model, days=days)

    if json_output:
        print(json.dumps(result, indent=2))
    else:
        report = reconciler.render_terminal_report(result)
        print(report)

    return result
