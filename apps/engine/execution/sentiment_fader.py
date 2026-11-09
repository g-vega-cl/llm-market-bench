"""Contrarian Options Sentiment Fader systematic portfolio execution logic.

Trades mean-reversion on extreme options market sentiment:
1. Signal: Fades retail crowd panic when Put/Call volume ratio >= 1.30 on liquid index ETFs (SPY, QQQ).
2. Exit: Takes profit on extreme call complacency (Put/Call <= 0.60), cuts loss on 1.5% adverse move,
   or liquidates at max 3-day holding horizon.
3. Sizing & Friction: Equal-weighted allocation across qualified candidates with 1 bps slippage.
"""

from typing import Any

from core.config import logger

SYS_SENTIMENT_FADER_OWNER_ID = "sys-sentiment-fader"
DEFAULT_SENTIMENT_UNIVERSE = ["SPY", "QQQ"]
DEFAULT_PANIC_THRESHOLD_PC = 1.30
DEFAULT_EUPHORIA_THRESHOLD_PC = 0.60
DEFAULT_FADER_STOP_LOSS_PCT = 1.5  # 1.5% adverse stop loss
DEFAULT_FADER_MAX_HOLDING_DAYS = 3  # 3-day max swing horizon
DEFAULT_FADER_SLIPPAGE_BPS = 1.0  # 1 bps = 0.01%


def evaluate_sentiment_signal(
    metrics: dict[str, Any],
    panic_threshold: float = DEFAULT_PANIC_THRESHOLD_PC,
    euphoria_threshold: float = DEFAULT_EUPHORIA_THRESHOLD_PC,
) -> tuple[str, str]:
    """Evaluate Put/Call volume ratio for contrarian sentiment extremes.

    Returns:
        tuple[str, str]: (signal, reason) where signal is 'BUY', 'SELL', or 'HOLD'.
    """
    if not metrics:
        return "HOLD", "Data insufficient (missing options sentiment metrics)"

    raw_pv = metrics.get("put_call_volume_ratio")
    if raw_pv is None:
        raw_pv = metrics.get("pv_ratio")

    if raw_pv is None:
        return "HOLD", "Data insufficient (missing options sentiment metrics)"

    try:
        pv_ratio = float(raw_pv)
    except (ValueError, TypeError):
        return "HOLD", "Data insufficient (invalid pv_ratio)"

    ticker = metrics.get("ticker", "UNKNOWN")

    # Extreme panic: crowd buying massive puts -> fade panic with oversold bounce buy
    if pv_ratio >= panic_threshold:
        return (
            "BUY",
            f"Extreme put panic exhaustion on {ticker} (P/C Vol: {pv_ratio:.2f} >= {panic_threshold:.2f})",
        )

    # Extreme euphoria: crowd buying massive calls -> complacency top, exit long
    if pv_ratio <= euphoria_threshold:
        return (
            "SELL",
            f"Extreme call complacency / euphoria on {ticker} (P/C Vol: {pv_ratio:.2f} <= {euphoria_threshold:.2f})",
        )

    return "HOLD", f"Neutral sentiment on {ticker} (P/C Vol: {pv_ratio:.2f})"


def evaluate_sentiment_holding_exit(
    holding_info: dict[str, Any],
    current_price: float,
    current_sentiment: dict[str, Any] | None = None,
    days_held: int = 0,
    stop_loss_pct: float = DEFAULT_FADER_STOP_LOSS_PCT,
    max_holding_days: int = DEFAULT_FADER_MAX_HOLDING_DAYS,
    euphoria_threshold: float = DEFAULT_EUPHORIA_THRESHOLD_PC,
) -> tuple[bool, str]:
    """Evaluate exit conditions for an existing sentiment fader position.

    Exit Triggers:
    1. Adverse Stop Loss: Price drops >= stop_loss_pct below entry price.
    2. Max Holding Horizon: Position held >= max_holding_days.
    3. Sentiment Euphoria: Options Put/Call ratio drops <= euphoria_threshold (take profit).
    """
    ticker = holding_info.get("ticker", "UNKNOWN")
    entry_price = float(holding_info.get("entry_price", 0.0) or holding_info.get("cost_basis", 0.0))

    # 1. Adverse Stop Loss
    if entry_price > 0 and current_price > 0:
        drawdown_pct = ((entry_price - current_price) / entry_price) * 100.0
        if drawdown_pct >= stop_loss_pct:
            return (
                True,
                f"Adverse stop loss triggered for {ticker} (-{drawdown_pct:.2f}% below entry ${entry_price:.2f})",
            )

    # 2. Max Holding Horizon
    if days_held >= max_holding_days:
        return True, f"Max holding horizon reached ({days_held} days >= {max_holding_days} days) for {ticker}"

    # 3. Euphoria Take Profit
    if current_sentiment:
        raw_pv = current_sentiment.get("put_call_volume_ratio")
        if raw_pv is None:
            raw_pv = current_sentiment.get("pv_ratio")
        if raw_pv is not None:
            try:
                pv_ratio = float(raw_pv)
                if pv_ratio <= euphoria_threshold:
                    return (
                        True,
                        f"Extreme call euphoria detected on {ticker} (P/C Vol: {pv_ratio:.2f} <= {euphoria_threshold:.2f})",
                    )
            except (ValueError, TypeError):
                pass

    return False, f"Holding criteria healthy for {ticker}"


def compute_sentiment_fader_rebalance_orders(
    current_holdings: list[dict[str, Any]],
    holding_evaluations: dict[str, dict[str, Any]],
    qualified_candidates: list[dict[str, Any]],
    available_cash: float,
    max_holdings: int = len(DEFAULT_SENTIMENT_UNIVERSE),
    slippage_bps: float = DEFAULT_FADER_SLIPPAGE_BPS,
) -> dict[str, Any]:
    """Computes liquidations and equal-weighted entries for the Sentiment Fader portfolio."""
    slip_factor = slippage_bps / 10000.0
    sales: list[dict[str, Any]] = []
    retained: list[dict[str, Any]] = []
    freed_cash = 0.0

    # 1. Process exits
    for h in current_holdings:
        ticker = h["ticker"]
        eval_res = holding_evaluations.get(ticker, {})
        if eval_res.get("should_exit", False):
            shares = int(h.get("shares", 0))
            raw_price = float(h.get("current_price", 0.0) or h.get("cost_basis", 0.0))
            reason_str = str(eval_res.get("reason", "Exit rule satisfied"))
            exec_price = round(raw_price * (1.0 - slip_factor), 4)
            proceeds = round(shares * exec_price, 2)
            freed_cash += proceeds
            sales.append(
                {
                    "ticker": ticker,
                    "shares": shares,
                    "execution_price": exec_price,
                    "proceeds": proceeds,
                    "reason": reason_str,
                }
            )
        else:
            retained.append(h)

    # 2. Open slots & candidate allocation
    open_slots = max(0, max_holdings - len(retained))
    retained_tickers = {h["ticker"].upper() for h in retained}

    eligible_candidates = [c for c in qualified_candidates if c.get("ticker", "").upper() not in retained_tickers]
    # Sort eligible candidates by highest Put/Call volume ratio descending (most extreme panic first)
    eligible_candidates.sort(
        key=lambda c: float(c.get("pv_ratio", 0.0)),
        reverse=True,
    )
    selected_buys = eligible_candidates[:open_slots]

    buys: list[dict[str, Any]] = []
    total_deployable_cash = available_cash + freed_cash
    remaining_cash = total_deployable_cash

    if selected_buys and total_deployable_cash > 0:
        alloc_per_buy = total_deployable_cash / len(selected_buys)
        for cand in selected_buys:
            ticker = cand["ticker"].upper()
            raw_price = float(cand.get("price", 0.0))
            if raw_price <= 0:
                continue

            exec_price = round(raw_price * (1.0 + slip_factor), 2)
            shares = int(alloc_per_buy // exec_price)
            if shares <= 0:
                continue

            cost = round(shares * exec_price, 2)
            remaining_cash -= cost
            buys.append(
                {
                    "ticker": ticker,
                    "shares": shares,
                    "execution_price": exec_price,
                    "total_cost": cost,
                    "pv_ratio": cand.get("pv_ratio"),
                }
            )

    logger.info(
        f"Sentiment Fader rebalance computed: {len(sales)} sales (${freed_cash:.2f}), "
        f"{len(buys)} buys, remaining cash: ${remaining_cash:.2f}"
    )

    return {
        "sales": sales,
        "buys": buys,
        "retained": retained,
        "remaining_cash": round(remaining_cash, 2),
        "total_deployable_cash": round(total_deployable_cash, 2),
    }
