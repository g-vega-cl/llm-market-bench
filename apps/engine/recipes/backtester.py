"""Timeline backtester for Voxel Strategy Recipe DAGs."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

from recipes.backtest_models import (
    CompletedTrade,
    Position,
    SkippedTrade,
    build_backtest_summary,
    close_position,
)
from recipes.indicators import Bar, compute_bar_indicators, evaluate_technical_gate
from recipes.schema import ConditionRule, RecipeGraph


def _extract_nodes(
    recipe: RecipeGraph,
) -> tuple[dict[str, Any] | None, list[ConditionRule], dict[str, Any] | None, dict[str, Any]]:
    """Extract node configs from recipe graph."""
    news_cfg = None
    tech_conditions: list[ConditionRule] = []
    class_cfg = None
    risk_cfg: dict[str, Any] = {
        "action": "BUY",
        "stop_loss_pct": 1.5,
        "target_profit_pct": 3.0,
        "max_hold_bars": 12,
        "exit_on_session_close": True,
    }

    for n in recipe.nodes:
        if n.type == "news_source":
            news_cfg = n.config
        elif n.type == "technical_gate":
            raw_conds = n.config.get("conditions", [])
            for c in raw_conds:
                if isinstance(c, dict):
                    tech_conditions.append(ConditionRule(**c))
                elif isinstance(c, ConditionRule):
                    tech_conditions.append(c)
        elif n.type in ("classification", "generative_analyst"):
            class_cfg = n.config
        elif n.type == "risk_output":
            risk_cfg.update(n.config)

    return news_cfg, tech_conditions, class_cfg, risk_cfg


def _check_position_exit(pos: Position, bar: Bar, idx: int, is_last_bar: bool) -> str | None:
    """Determine if an open position meets an exit condition on the given bar."""
    if pos.action == "BUY":
        # Conservative fill: if both breach on same bar, assume stop loss hit first
        if bar.low <= pos.stop_loss_price:
            return "STOP_LOSS"
        if bar.high >= pos.target_price:
            return "TARGET_PROFIT"
    else:  # SELL / SHORT
        # Conservative fill: if both breach on same bar, assume stop loss hit first
        if bar.high >= pos.stop_loss_price:
            return "STOP_LOSS"
        if bar.low <= pos.target_price:
            return "TARGET_PROFIT"

    if (idx - pos.entry_bar_idx) >= pos.max_hold_bars:
        return "MAX_HOLD"

    if pos.exit_on_session_close and is_last_bar:
        return "SESSION_CLOSE"

    return None


def _find_qualifying_article(
    news_list: list[dict[str, Any]],
    bar_time: datetime,
    lookback_hours: int,
    bucket: str | None = None,
    tickers: list[str] | None = None,
) -> dict[str, Any] | None:
    """Find the latest news article published within lookback_hours matching bucket/ticker filters."""
    for art in news_list:
        art_date = art.get("date_published")
        if isinstance(art_date, str):
            art_date = datetime.fromisoformat(art_date.replace("Z", "+00:00"))
        if art_date and art_date <= bar_time:
            diff_hours = (bar_time - art_date).total_seconds() / 3600.0
            if 0 <= diff_hours <= lookback_hours:
                if bucket:
                    art_buckets = [str(b).lower() for b in art.get("buckets", [])]
                    if bucket.lower() not in art_buckets:
                        continue
                if tickers:
                    clean_tickers = [str(t).upper().strip() for t in tickers if str(t).strip()]
                    art_tickers = [str(t).upper().strip() for t in art.get("tickers", [])]
                    if clean_tickers and not any(t in art_tickers for t in clean_tickers):
                        continue
                return art
    return None


def _evaluate_llm_gate(
    class_cfg: dict[str, Any],
    article: dict[str, Any],
    bar: Bar,
    llm_cache: dict[str, tuple[str, float]],
    llm_call_count: int,
    max_llm_calls: int,
    llm_evaluator: Callable[[dict[str, Any], dict[str, Any]], tuple[str, float]] | None,
) -> tuple[bool, float, int, SkippedTrade | None]:
    """Check LLM classification for catalyst. Returns (passed, confidence, new_call_count, skipped_trade)."""
    art_id = article.get("article_id") or article.get("title", "")
    catalyst_headline = article.get("title", "")

    if art_id in llm_cache:
        choice, conf = llm_cache[art_id]
        new_count = llm_call_count
    else:
        if llm_call_count >= max_llm_calls:
            skipped = SkippedTrade(
                time=bar.time_utc.isoformat(),
                reason=f"Max LLM calls ({max_llm_calls}) reached for backtest",
                skip_type="BUDGET_EXCEEDED",
                headline=catalyst_headline,
            )
            return False, 0.0, llm_call_count, skipped

        if llm_evaluator:
            choice, conf = llm_evaluator(class_cfg, article)
        else:
            choice = class_cfg.get("target_choice", "BULLISH")
            conf = 90.0

        new_count = llm_call_count + 1
        llm_cache[art_id] = (choice, conf)

    target_choice = class_cfg.get("target_choice", "BULLISH")
    min_conf = float(class_cfg.get("min_confidence", 70.0))

    if choice != target_choice or conf < min_conf:
        skipped = SkippedTrade(
            time=bar.time_utc.isoformat(),
            reason=f"LLM decision '{choice}' ({conf}%) did not meet '{target_choice}' (>= {min_conf}%)",
            skip_type="LLM_REJECTED",
            headline=catalyst_headline,
        )
        return False, conf, new_count, skipped

    return True, conf, new_count, None


def _create_position(
    ticker: str,
    bar: Bar,
    idx: int,
    equity: float,
    max_equity_pct: float,
    risk_cfg: dict[str, Any],
    catalyst_headline: str,
    confidence: float,
) -> Position:
    """Calculate sizing, stops, targets, and return new Position."""
    trade_action = risk_cfg.get("action", "BUY")
    stop_pct = float(risk_cfg.get("stop_loss_pct", 1.5)) / 100.0
    target_pct = float(risk_cfg.get("target_profit_pct", 3.0)) / 100.0
    max_hold = int(risk_cfg.get("max_hold_bars", 12))
    exit_session = bool(risk_cfg.get("exit_on_session_close", True))

    allocated_cash = equity * max_equity_pct
    shares = max(1, int(allocated_cash / bar.close))

    if trade_action == "BUY":
        sl_price = round(bar.close * (1.0 - stop_pct), 4)
        tp_price = round(bar.close * (1.0 + target_pct), 4)
    else:  # SELL / SHORT
        sl_price = round(bar.close * (1.0 + stop_pct), 4)
        tp_price = round(bar.close * (1.0 - target_pct), 4)

    return Position(
        ticker=ticker,
        entry_time=bar.time_utc,
        entry_price=bar.close,
        entry_bar_idx=idx,
        action=trade_action,
        shares=shares,
        stop_loss_price=sl_price,
        target_price=tp_price,
        max_hold_bars=max_hold,
        exit_on_session_close=exit_session,
        catalyst_headline=catalyst_headline,
        confidence=confidence,
    )


def run_recipe_backtest(
    recipe: RecipeGraph,
    bars_by_week: dict[str, list[Bar]],
    news_articles: list[dict[str, Any]] | None = None,
    llm_evaluator: Callable[[dict[str, Any], dict[str, Any]], tuple[str, float]] | None = None,
    max_llm_calls: int = 40,
    slippage_bps: float = 5.0,
    starting_capital: float = 10000.0,
) -> dict[str, Any]:
    """Execute timeline backtest across non-contiguous ISO weeks."""
    slippage_rate = slippage_bps / 10000.0
    news_cfg, tech_conds, class_cfg, risk_cfg = _extract_nodes(recipe)
    concurrency = recipe.concurrency or {}
    max_open_trades = int(concurrency.get("max_open_trades", 3))
    max_equity_pct = float(concurrency.get("max_equity_pct_per_trade", 33.3)) / 100.0

    all_trades: list[CompletedTrade] = []
    skipped_trades: list[SkippedTrade] = []
    equity_mid = starting_capital
    equity_net = starting_capital
    equity_curve: list[dict[str, Any]] = [{"time": "START", "equity_midpoint": equity_mid, "equity_net": equity_net}]

    llm_cache: dict[str, tuple[str, float]] = {}
    llm_call_count = 0
    news_list = news_articles or []
    weeks_breakdown: list[dict[str, Any]] = []

    for week_key in sorted(bars_by_week.keys()):
        bars = compute_bar_indicators(bars_by_week[week_key])
        if not bars:
            continue
        open_pos: list[Position] = []
        week_trades: list[CompletedTrade] = []

        for idx, bar in enumerate(bars):
            # 1. Evaluate open positions for exit
            remaining_pos: list[Position] = []
            is_last_bar = idx == len(bars) - 1

            for pos in open_pos:
                exit_reason = _check_position_exit(pos, bar, idx, is_last_bar)
                if exit_reason:
                    trade = close_position(pos, bar, exit_reason, slippage_rate)
                    week_trades.append(trade)
                    all_trades.append(trade)
                    equity_mid += trade.pnl_midpoint
                    equity_net += trade.pnl_net
                    equity_curve.append(
                        {
                            "time": trade.exit_time,
                            "equity_midpoint": round(equity_mid, 2),
                            "equity_net": round(equity_net, 2),
                        }
                    )
                else:
                    remaining_pos.append(pos)
            open_pos = remaining_pos

            # 2. Check if we can open new positions
            if len(open_pos) >= max_open_trades:
                continue

            # 3. Technical Indicator Gate
            if tech_conds:
                tech_passed, _ = evaluate_technical_gate(tech_conds, bar)
                if not tech_passed:
                    skipped_trades.append(
                        SkippedTrade(
                            time=bar.time_utc.isoformat(),
                            reason="Technical conditions not met",
                            skip_type="TECHNICAL_BLOCKED",
                        )
                    )
                    continue

            # 4. News Catalyst Gate
            catalyst_headline = ""
            active_article = None
            if news_cfg:
                lookback = int(news_cfg.get("lookback_hours", 72))
                bucket = news_cfg.get("bucket")
                tickers = news_cfg.get("tickers")
                active_article = _find_qualifying_article(
                    news_list, bar.time_utc, lookback, bucket=bucket, tickers=tickers
                )
                if not active_article:
                    skipped_trades.append(
                        SkippedTrade(
                            time=bar.time_utc.isoformat(),
                            reason=f"No matching news within {lookback}h lookback",
                            skip_type="NO_CATALYST",
                        )
                    )
                    continue
                catalyst_headline = active_article.get("title", "")

            # 5. LLM Classification Gate
            confidence = 100.0
            if class_cfg and active_article:
                passed, conf, llm_call_count, skipped = _evaluate_llm_gate(
                    class_cfg,
                    active_article,
                    bar,
                    llm_cache,
                    llm_call_count,
                    max_llm_calls,
                    llm_evaluator,
                )
                if not passed:
                    if skipped:
                        skipped_trades.append(skipped)
                    continue
                confidence = conf

            # 6. Enter Position
            ticker = getattr(bar, "ticker", None) or "SPY"
            new_pos = _create_position(
                ticker=ticker,
                bar=bar,
                idx=idx,
                equity=equity_net,
                max_equity_pct=max_equity_pct,
                risk_cfg=risk_cfg,
                catalyst_headline=catalyst_headline,
                confidence=confidence,
            )
            open_pos.append(new_pos)

        # Weekly summary
        week_pnl_mid = sum(t.pnl_midpoint for t in week_trades)
        week_pnl_net = sum(t.pnl_net for t in week_trades)
        weeks_breakdown.append(
            {
                "week": week_key,
                "trades": len(week_trades),
                "trades_count": len(week_trades),
                "week_pnl_midpoint": round(week_pnl_mid, 2),
                "week_pnl_net": round(week_pnl_net, 2),
                "pnl_net": round(week_pnl_net, 2),
                "ending_equity": round(equity_net, 2),
            }
        )

    return build_backtest_summary(
        starting_capital=starting_capital,
        equity_midpoint=equity_mid,
        equity_net=equity_net,
        all_trades=all_trades,
        skipped_trades=skipped_trades,
        equity_curve=equity_curve,
        weeks_breakdown=weeks_breakdown,
        llm_call_count=llm_call_count,
    )
