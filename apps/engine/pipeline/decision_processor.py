"""Single decision execution, margin guardrails, and decision batch orchestration."""

import asyncio
from collections import defaultdict

from analysis.consensus import process_consensus
from analysis.momentum import analyze_momentum, decay_stale_concepts
from attribution.service import save_decision
from core.config import logger
from core.llm.verification import verify_trading_decision
from execution.portfolio import Portfolio
from execution.validation import ValidationStatus, validate_decision, validate_semantic_overlap
from pipeline.resolver import resolve_dep


async def _execute_minimax_order(d, portfolio, validation, sb_client, record_fn, counters, dry_run: bool):
    """Execute trading decision via the specialized MiniMax execution path."""
    from execution.market_data import MarketDataManager

    mdm = MarketDataManager()
    log = resolve_dep("logger", logger)

    if d.signal.upper() == "SELL" and d.ticker not in portfolio.positions:
        log.warning(f"[MiniMax][{d.ticker}] REJECTED (Ownership): SELL for unheld ticker.")
        record_fn(
            sb_client,
            d,
            status="REJECTED_OWNERSHIP",
            metadata={"reason": "Ticker not held."},
        )
        async with counters["lock"]:
            counters["rejected"] += 1
        return False

    market_price = validation.market_price
    if not market_price or market_price <= 0:
        log.error(f"[MiniMax][{d.ticker}] No valid market price.")
        async with counters["lock"]:
            counters["rejected"] += 1
        return False

    exec_price = round(market_price * 1.005, 2) if d.signal.upper() == "BUY" else round(market_price * 0.995, 2)

    log.info(
        f"[MiniMax][{d.ticker}] Market order: {d.signal} @ ${exec_price:.2f} "
        f"(market: ${market_price:.2f}, buffer: 0.5%)"
    )

    await portfolio.initialize()

    all_pos_tickers = list(portfolio.positions.keys())
    if d.ticker not in all_pos_tickers:
        all_pos_tickers.append(d.ticker)
    fresh_quotes = await mdm.get_quotes(all_pos_tickers)
    fresh_p_map = {t: data.price for t, data in fresh_quotes.items()}
    portfolio.calculate_reg_t_metrics(fresh_p_map)

    if d.signal.upper() == "BUY":
        bp = portfolio.metrics.buying_power if portfolio.metrics else 0
        total_equity = portfolio.metrics.total_equity if portfolio.metrics else 0
        from core.config import MIN_TRADE_VALUE

        alloc_pct = d.allocation_percentage if d.allocation_percentage is not None else 20
        min_buy_threshold = max(MIN_TRADE_VALUE, 0.10 * total_equity)
        usd_to_spend = (alloc_pct / 100.0) * bp

        if usd_to_spend < min_buy_threshold and bp >= min_buy_threshold:
            usd_to_spend = min_buy_threshold

        qty = int(usd_to_spend / exec_price)
        if qty * exec_price < min_buy_threshold and (qty + 1) * exec_price <= bp:
            qty += 1
    else:
        if d.ticker not in portfolio.positions:
            record_fn(
                sb_client,
                d,
                status="REJECTED_OWNERSHIP",
                metadata={"reason": "Ticker sold by concurrent trade."},
            )
            async with counters["lock"]:
                counters["rejected"] += 1
            return False
        held_qty = portfolio.positions[d.ticker].quantity
        requested_qty = getattr(d, "quantity", None) or int(((d.allocation_percentage or 100) / 100.0) * held_qty)
        qty = min(requested_qty, held_qty)

    if qty <= 0:
        qty = getattr(d, "quantity", 0) or 1

    if qty <= 0:
        async with counters["lock"]:
            counters["rejected"] += 1
        return False

    validation_res = portfolio.validate_trade(d.ticker, qty, exec_price, d.signal, is_sell_tool_used=True)
    if not validation_res.passed:
        log.warning(f"[MiniMax][{d.ticker}] REJECTED (Margin): {validation_res.reason}")
        record_fn(
            sb_client,
            d,
            status="REJECTED_MARGIN",
            metadata={"reason": validation_res.reason},
        )
        async with counters["lock"]:
            counters["rejected"] += 1
        return False

    if dry_run:
        trade_id = None
        status = "EXECUTED_DRY_RUN"
        decision_id = "dry_run_decision_id"
        meta = {
            "trade_id": "dry_run",
            "info": f"[DRY RUN][MiniMax] Market order {d.signal} {qty} @ ${exec_price:.2f}",
        }
        log.info(f"[DRY RUN][MiniMax][{d.ticker}] Would execute market order: {d.signal} {qty} @ ${exec_price:.2f}")
    else:
        decision_row = record_fn(sb_client, d, status="VALIDATED", metadata={"info": "MiniMax market order"})
        decision_id = decision_row.get("id")
        if not decision_id:
            log.error(f"[MiniMax][{d.ticker}] Pre-save returned no decision ID — aborting trade")
            return False

        trade_id = await portfolio.execute_trade(
            d.ticker,
            qty,
            exec_price,
            d.signal,
            decision_id=decision_id,
            current_prices=fresh_p_map,
            skip_alpaca_mirror=True,
        )

        if trade_id:
            status = "EXECUTED"
            meta = {
                "trade_id": str(trade_id),
                "info": f"[MiniMax] Market order {d.signal} {qty} @ ${exec_price:.2f}",
            }
            alpaca_limit = exec_price
            import asyncio as _asyncio

            from execution.alpaca_broker import AlpacaBroker

            _asyncio.create_task(
                AlpacaBroker().submit_limit_order(
                    trade_id=trade_id,
                    ticker=d.ticker,
                    quantity=qty,
                    signal=d.signal,
                    limit_price=alpaca_limit,
                    agent_id=d.model_name,
                )
            )
        else:
            status = "ERROR_EXECUTION"
            meta = {"info": "MiniMax execution failed"}

    record_fn(
        sb_client,
        d,
        status=status,
        metadata=meta,
        trade_id=str(trade_id) if trade_id else None,
        decision_id=decision_id,
    )
    log.info(f"[MiniMax][{d.ticker}] {d.signal}: Attribution saved (Status: {status}).")
    async with counters["lock"]:
        counters["saved"] += 1
    return status in ("EXECUTED", "EXECUTED_DRY_RUN")


async def _execute_standard_order(
    d, portfolio, validation, aggregated_context, uncrowded_context, sb_client, record_fn, counters, dry_run: bool
):
    """Execute trading decision via the standard multi-provider execution path."""
    log = resolve_dep("logger", logger)
    verify_fn = resolve_dep("verify_trading_decision", verify_trading_decision)
    validate_overlap_fn = resolve_dep("validate_semantic_overlap", validate_semantic_overlap)

    if d.signal.upper() == "SELL":
        if d.ticker not in portfolio.positions:
            log.warning(f"[{d.ticker}] REJECTED (Ownership): SELL signal for unheld ticker.")
            record_fn(sb_client, d, status="REJECTED_OWNERSHIP", metadata={"reason": "Ticker not held."})
            async with counters["lock"]:
                counters["rejected"] += 1
            return False
        if not getattr(d, "sell_tool_called", False):
            log.warning(f"[{d.ticker}] REJECTED (Tool Usage): SELL without sell tool.")
            record_fn(
                sb_client,
                d,
                status="REJECTED_TOOL_USAGE",
                metadata={"reason": "Sell tool must be called."},
            )
            async with counters["lock"]:
                counters["rejected"] += 1
            return False

    exec_price = validation.market_price
    if not exec_price or exec_price <= 0:
        log.error(f"[{d.ticker}] No valid price.")
        async with counters["lock"]:
            counters["rejected"] += 1
        return False

    from execution.market_data import MarketDataManager

    mdm = MarketDataManager()
    all_pos_tickers = list(portfolio.positions.keys())
    if d.ticker not in all_pos_tickers:
        all_pos_tickers.append(d.ticker)

    quotes = await mdm.get_quotes(all_pos_tickers)
    p_map = {t: data.price for t, data in quotes.items()}

    verification = None
    meta = {"info": "Validation Passed (No Trade)"}
    qty = 0

    if d.signal.upper() == "BUY":
        if not portfolio.metrics:
            portfolio.calculate_reg_t_metrics(p_map)

        from core.config import is_verifier_enabled_for_owner
        from core.models import VerificationResult

        if not is_verifier_enabled_for_owner(d.model_name):
            log.info(
                f"[{d.ticker}] Skipping verification for model {d.model_name} per verifier portfolio configuration."
            )
            verification = VerificationResult(
                status="APPROVED",
                verification_reasoning="Skipped per verifier portfolio configuration",
                confidence_score=100,
            )
        else:
            log.info(f"[{d.ticker}] Verifying...")
            verification = await verify_fn(
                decision=d,
                portfolio_context=await portfolio.get_portfolio_summary(p_map),
                aggregated_context=aggregated_context,
                uncrowded_context=uncrowded_context,
            )

        if verification.status == "REJECTED_VERIFICATION":
            log.warning(f"[{d.ticker}] REJECTED (Verification): {verification.verification_reasoning}")
            record_fn(
                sb_client,
                d,
                status="REJECTED_VERIFICATION",
                metadata={"reason": verification.verification_reasoning},
            )
            async with counters["lock"]:
                counters["rejected"] += 1
            return False

        meta.update(
            {
                "verification_reasoning": verification.verification_reasoning,
                "verification_confidence": verification.confidence_score,
                "suggested_alternative": verification.alternative_ticker,
            }
        )

    overlap_reason = await validate_overlap_fn(d.ticker, d.reasoning, model_name=d.model_name)
    if overlap_reason:
        log.warning(f"[{d.ticker}] REJECTED (Redundancy): {overlap_reason}")
        record_fn(
            sb_client,
            d,
            status=ValidationStatus.REJECTED_REDUNDANCY.value,
            metadata={"reason": overlap_reason},
        )
        async with counters["lock"]:
            counters["rejected"] += 1
        return False

    await portfolio.initialize()

    final_quote = await mdm.get_quote(d.ticker)
    if final_quote and final_quote.exists:
        if final_quote.price != exec_price:
            log.info(f"[{d.ticker}] Price moved during verification: ${exec_price:.2f} -> ${final_quote.price:.2f}")
            exec_price = final_quote.price

        injected_price = getattr(d, "injected_market_price", None)
        if injected_price and injected_price > 0:
            drift = abs(exec_price - injected_price) / injected_price
            if drift > 0.02:
                reason = f"Stale quote: market moved {drift:.1%} since analysis (analysis: ${injected_price:.2f}, current: ${exec_price:.2f})"
                log.warning(f"[{d.ticker}] REJECTED (Stale Quote): {reason}")
                record_fn(sb_client, d, status="REJECTED_STALE_QUOTE", metadata={"reason": reason})
                async with counters["lock"]:
                    counters["rejected"] += 1
                return False

    all_pos_tickers = list(portfolio.positions.keys())
    if d.ticker not in all_pos_tickers:
        all_pos_tickers.append(d.ticker)
    fresh_quotes = await mdm.get_quotes(all_pos_tickers)
    fresh_p_map = {t: data.price for t, data in fresh_quotes.items()}
    portfolio.calculate_reg_t_metrics(fresh_p_map)

    if d.signal.upper() == "BUY":
        bp = portfolio.metrics.buying_power if portfolio.metrics else 0
        total_equity = portfolio.metrics.total_equity if portfolio.metrics else 0
        from core.config import MIN_TRADE_VALUE

        alloc_pct = d.allocation_percentage if d.allocation_percentage is not None else 20
        min_buy_threshold = max(MIN_TRADE_VALUE, 0.10 * total_equity)
        usd_to_spend = (alloc_pct / 100.0) * bp

        if usd_to_spend < min_buy_threshold and bp >= min_buy_threshold:
            usd_to_spend = min_buy_threshold

        qty = int(usd_to_spend / exec_price)
        if qty * exec_price < min_buy_threshold and (qty + 1) * exec_price <= bp:
            qty += 1
    elif d.signal.upper() == "SELL":
        if d.ticker not in portfolio.positions:
            record_fn(
                sb_client,
                d,
                status="REJECTED_OWNERSHIP",
                metadata={"reason": "Ticker sold by concurrent trade."},
            )
            async with counters["lock"]:
                counters["rejected"] += 1
            return False
        qty = getattr(d, "quantity", None) or int(
            ((d.allocation_percentage or 0) / 100.0) * portfolio.positions.get(d.ticker).quantity
        )

    if qty <= 0:
        qty = getattr(d, "quantity", 0) or 1

    if verification and verification.status == "ADJUSTED_ALLOCATION":
        if verification.adjusted_quantity and verification.adjusted_quantity > 0:
            qty = verification.adjusted_quantity
        else:
            log.warning(
                f"[{d.ticker}] REJECTED (Verification): Status is ADJUSTED_ALLOCATION "
                f"but adjusted_quantity is invalid ({verification.adjusted_quantity})."
            )
            record_fn(
                sb_client,
                d,
                status="REJECTED_VERIFICATION",
                metadata={
                    "reason": (
                        f"Verifier specified ADJUSTED_ALLOCATION but provided invalid adjusted_quantity: "
                        f"{verification.adjusted_quantity}"
                    )
                },
            )
            async with counters["lock"]:
                counters["rejected"] += 1
            return False

    if qty <= 0:
        async with counters["lock"]:
            counters["rejected"] += 1
        return False

    validation_res = portfolio.validate_trade(
        d.ticker, qty, exec_price, d.signal, is_sell_tool_used=getattr(d, "sell_tool_called", False)
    )
    if not validation_res.passed:
        log.warning(f"[{d.ticker}] REJECTED (Margin JIT): {validation_res.reason}")
        record_fn(sb_client, d, status="REJECTED_MARGIN", metadata={"reason": validation_res.reason})
        async with counters["lock"]:
            counters["rejected"] += 1
        return False

    if dry_run:
        trade_id = None
        status = "EXECUTED_DRY_RUN"
        decision_id = "dry_run_decision_id"
        meta.update(
            {
                "trade_id": "dry_run",
                "info": f"[DRY RUN] Executed {d.signal} {qty} @ ${exec_price:.2f}",
            }
        )
        log.info(f"[DRY RUN][{d.ticker}] Would execute: {d.signal} {qty} @ ${exec_price:.2f} for {d.model_name}")
    else:
        decision_row = record_fn(sb_client, d, status="VALIDATED", metadata=meta)
        decision_id = decision_row.get("id")
        if not decision_id:
            log.error(f"[{d.ticker}] Pre-save returned no decision ID — aborting trade")
            return False

        trade_id = await portfolio.execute_trade(
            d.ticker, qty, exec_price, d.signal, decision_id=decision_id, current_prices=fresh_p_map
        )

        if trade_id:
            status = "EXECUTED"
            meta.update(
                {
                    "trade_id": str(trade_id),
                    "info": f"Executed {d.signal} {qty} @ ${exec_price:.2f}",
                }
            )
        else:
            status = "ERROR_EXECUTION"
            meta.update({"info": "Execution Failed"})

    record_fn(
        sb_client,
        d,
        status=status,
        metadata=meta,
        trade_id=str(trade_id) if trade_id else None,
        decision_id=decision_id,
    )
    log.info(f"[{d.ticker}] {d.signal}: Saved attribution (Status: {status}).")
    async with counters["lock"]:
        counters["saved"] += 1
    return status in ("EXECUTED", "EXECUTED_DRY_RUN")


async def _process_single_decision(
    d,
    aggregated_context,
    uncrowded_context,
    sb_client,
    semaphore,
    portfolio_locks,
    counters,
    dry_run: bool = False,
):
    """Processes a single trading decision with concurrency controls."""
    async with semaphore:
        log = resolve_dep("logger", logger)
        save_fn = resolve_dep("save_decision", save_decision)
        validate_fn = resolve_dep("validate_decision", validate_decision)
        portfolio_cls = resolve_dep("Portfolio", Portfolio)

        def _record_decision(client, decision, status, metadata=None, trade_id=None, decision_id=None):
            if dry_run:
                log.info(
                    f"[DRY RUN][{getattr(decision, 'model_name', 'unknown')}][{decision.ticker}] "
                    f"Simulated attribution (Status: {status})"
                )
                return {"id": "dry_run_decision_id"}
            return save_fn(
                client, decision, status=status, metadata=metadata, trade_id=trade_id, decision_id=decision_id
            )

        try:
            d.ticker = d.ticker.upper()
            validation = await validate_fn(d.ticker)

            if validation.status != ValidationStatus.PASSED:
                log.warning(f"[{d.ticker}] REJECTED (Market Guardrails): {validation.reason}")
                _record_decision(sb_client, d, status=validation.status.value, metadata={"reason": validation.reason})
                async with counters["lock"]:
                    counters["rejected"] += 1
                return False

            status = "VALIDATED"
            meta = {"info": "Validation Passed (No Trade)"}
            lock = portfolio_locks[d.model_name]

            async with lock:
                if d.signal.upper() in ["BUY", "SELL"]:
                    portfolio = portfolio_cls(owner_id=d.model_name)
                    await portfolio.initialize()

                    if d.model_provider == "minimax":
                        return await _execute_minimax_order(
                            d, portfolio, validation, sb_client, _record_decision, counters, dry_run
                        )
                    else:
                        return await _execute_standard_order(
                            d,
                            portfolio,
                            validation,
                            aggregated_context,
                            uncrowded_context,
                            sb_client,
                            _record_decision,
                            counters,
                            dry_run,
                        )
                else:
                    _record_decision(sb_client, d, status=status, metadata=meta)
                    log.info(f"[{d.ticker}] {d.signal}: Saved attribution (Status: {status}).")
                    async with counters["lock"]:
                        counters["saved"] += 1

            return status in ("EXECUTED", "VALIDATED", "EXECUTED_DRY_RUN")
        except Exception:
            log.exception(f"Failed to process decision for {d.ticker}")
            return False


async def _stage_decision_processing(
    decisions,
    macro_events,
    data,
    aggregated_context,
    uncrowded_context,
    sb_client,
    consensus_events: list | None = None,
    dry_run: bool = False,
):
    """Stage 3: Decision attribution, validation, and execution with concurrency."""
    log = resolve_dep("logger", logger)
    process_consensus_fn = resolve_dep("process_consensus", process_consensus)
    analyze_momentum_fn = resolve_dep("analyze_momentum", analyze_momentum)
    decay_stale_fn = resolve_dep("decay_stale_concepts", decay_stale_concepts)
    process_single_fn = resolve_dep("_process_single_decision", _process_single_decision)

    async def run_consensus_background():
        try:
            nonlocal consensus_events
            if consensus_events is None:
                log.info("Running Event Consensus Protocol (background)...")
                consensus_events = await process_consensus_fn(macro_events)
                log.info(f"Background consensus finished. Promoted {len(consensus_events)} events.")
            else:
                log.info("Using pre-computed consensus events for momentum analysis.")

            log.info("Starting Trend & Concept Momentum Analysis (background)...")
            await analyze_momentum_fn(sb_client, consensus_events)
            log.info("Background momentum finished.")

            await decay_stale_fn(sb_client)
            from memory.store import decay_memories

            decay_memories(sb_client)

            try:
                from analysis.catalyst_radar import compute_and_store_catalyst_radar

                compute_and_store_catalyst_radar(sb_client)
            except Exception as radar_err:
                log.warning(f"Could not auto-update catalyst radar in background: {radar_err}")

            return consensus_events
        except Exception as e:
            log.error(f"Background consensus/momentum failed: {e}")
            return []

    consensus_bg_task = asyncio.create_task(run_consensus_background())

    decisions.sort(key=lambda d: (d.model_name or "", getattr(d, "original_index", 0)))

    semaphore = asyncio.Semaphore(3)
    portfolio_locks = defaultdict(asyncio.Lock)
    counters = {"saved": 0, "rejected": 0, "lock": asyncio.Lock()}

    log.info(f"Executing {len(decisions)} primary decisions (dry_run={dry_run})...")
    primary_tasks = [
        process_single_fn(
            d,
            aggregated_context,
            uncrowded_context,
            sb_client,
            semaphore,
            portfolio_locks,
            counters,
            dry_run=dry_run,
        )
        for d in decisions
    ]

    await asyncio.gather(*primary_tasks)

    log.info("Awaiting background consensus and momentum tasks to complete...")
    await consensus_bg_task

    log.info(f"Processing complete: {counters['saved']} saved, {counters['rejected']} rejected.")
