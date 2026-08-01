"""Entry point for the AI Wall Street Engine.

This module provides the CLI interface for running the daily pipeline,
including newsletter ingestion, database snapshotting, and LLM analysis.
"""

import argparse
import asyncio
from collections import defaultdict
from datetime import UTC

from analysis.analyze import analyze_chunks
from analysis.cause_and_effect_analysis import perform_cause_and_effect_analysis
from analysis.consensus import process_consensus
from analysis.contrarian import run_contrarian_analysis
from analysis.market_feeling import analyze_market_feeling
from analysis.momentum import analyze_momentum, decay_stale_concepts
from analysis.pca_utils import update_pca_coordinates
from analysis.post_analysis import perform_post_analysis
from attribution.service import save_decision
from core.audit import run_audit
from core.config import (
    COMMAND_AUDIT,
    COMMAND_AUTORESEARCH,
    COMMAND_BOOTSTRAP_AUTORESEARCH,
    COMMAND_CALENDAR,
    COMMAND_CAUSE_AND_EFFECT,
    COMMAND_CLEANUP,
    COMMAND_GOVERNMENT,
    COMMAND_INGEST,
    COMMAND_POST_ANALYSIS,
    COMMAND_WEEKEND_INGEST,
    logger,
)
from core.db import bulk_upsert_newsletter_snapshots, get_supabase_client, upsert_newsletter_snapshot
from core.llm.verification import verify_trading_decision
from execution.portfolio import Portfolio
from execution.validation import ValidationStatus, validate_decision, validate_semantic_overlap
from ingest.calendar import run_calendar_pipeline
from ingest.government import run_government_pipeline
from ingest.newsletter import ingest_newsletters


async def _stage_ingest_and_snapshot():
    """Stage 1: Ingest newsletters and save snapshots."""
    logger.info("Starting Newsletter Ingestion...")
    data = await ingest_newsletters()

    if not data:
        logger.warning("No new newsletters found to ingest. Skipping snapshotting and analysis.")
        return None, None

    logger.info(f"Successfully ingested {len(data)} newsletters.")
    logger.info("Starting Database Snapshotting...")

    sb_client = get_supabase_client()
    saved_count = 0

    try:
        bulk_upsert_newsletter_snapshots(sb_client, data)
        saved_count = len(data)
    except Exception:
        logger.warning("Bulk upsert failed, falling back to individual upserts.")
        for item in data:
            try:
                upsert_newsletter_snapshot(sb_client, item)
                saved_count += 1
            except Exception:
                logger.exception(f"Error saving snapshot for {item.get('source_id', 'unknown')}")

    logger.info(f"Successfully saved {saved_count}/{len(data)} snapshots to Supabase.")
    return data, sb_client


async def _stage_dust_cleanup(sb_client):
    """Stage 1.5: Clean dust positions from all active portfolios BEFORE LLM analysis.

    This ensures LLMs never see "dust" positions (<10% of portfolio equity)
    when making allocation decisions. Runs regardless of whether newsletter data exists,
    as it's a safety net for accumulated dust from any source.
    """
    from analysis.analyze import MODELS
    from execution.market_data import MarketDataManager

    logger.info("Starting Pre-Analysis Dust Cleanup...")
    mdm = MarketDataManager()
    total_cleaned = 0
    cleaned_tickers = []

    for config in MODELS:
        model = config["model"]
        try:
            portfolio = Portfolio(owner_id=model)
            await portfolio.initialize()

            if not portfolio.positions:
                logger.info(f"[{model}] No positions to check.")
                continue

            logger.info(f"[{model}] Checking {len(portfolio.positions)} positions for dust...")

            # Get current prices for all positions
            quotes = await mdm.get_quotes(list(portfolio.positions.keys()))
            price_map = {ticker: data.price for ticker, data in quotes.items()}

            # Calculate threshold for logging
            if portfolio.metrics:
                threshold = portfolio.metrics.total_equity * 0.10
                logger.info(
                    f"[{model}] 10% dust threshold: ${threshold:,.2f} (total equity: ${portfolio.metrics.total_equity:,.2f})"
                )

            # Track positions before cleanup to detect which were removed/sold
            before_positions = list(portfolio.positions.keys())

            # Run dust cleanup (modifies portfolio state in-place)
            await portfolio._check_and_sell_dust_positions(price_map)

            # Count cleaned positions
            for ticker in before_positions:
                if ticker not in portfolio.positions:
                    cleaned_tickers.append((model, ticker))
                    total_cleaned += 1

        except Exception:
            logger.exception(f"Dust cleanup failed for {model}")

    logger.info(f"Pre-Analysis Dust Cleanup complete. Cleaned {total_cleaned} dust positions: {cleaned_tickers}")


async def _stage_analysis_and_consensus(data, sb_client):
    """Stage 2: Run parallel LLM analysis and event consensus.

    Note: Consensus and momentum now run as background tasks in _stage_decision_processing
    to allow decision execution to start sooner.
    """
    logger.info("Starting Parallel LLM Analysis...")
    try:
        decisions, macro_events, aggregated_context, uncrowded_context = await analyze_chunks(data)
        logger.info(
            f"Analysis complete. Generated {len(decisions)} decisions and {len(macro_events)} raw macro events."
        )

        if not decisions and not macro_events:
            logger.warning("No decisions or events generated from analysis. Check LLM provider connectivity.")

        return decisions, macro_events, aggregated_context, uncrowded_context
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        return [], [], "", ""


async def _process_single_decision(
    d, contrarian_decisions, aggregated_context, uncrowded_context, sb_client, semaphore, portfolio_locks, counters
):
    """Processes a single trading decision with concurrency controls."""
    async with semaphore:
        try:
            # --- Pre-Market Validation ---
            d.ticker = d.ticker.upper()
            validation = await validate_decision(d.ticker)

            if validation.status != ValidationStatus.PASSED:
                logger.warning(f"[{d.ticker}] REJECTED (Market Guardrails): {validation.reason}")
                save_decision(sb_client, d, status=validation.status.value, metadata={"reason": validation.reason})
                async with counters["lock"]:
                    counters["rejected"] += 1
                return False

            # --- Execution Logic ---
            status = "VALIDATED"
            meta = {"info": "Validation Passed (No Trade)"}
            trade_id = None

            # --- PROTECTED EXECUTION BLOCK ---
            # We use a per-portfolio lock to ensure atomic refreshes and executions
            lock = portfolio_locks[d.model_name]

            async with lock:
                if d.signal.upper() in ["BUY", "SELL"]:
                    portfolio = Portfolio(owner_id=d.model_name)
                    # Note: we initialize inside the lock to ensure we have the most current DB state
                    await portfolio.initialize()

                    # ---------------------------------------------------------------
                    # MINIMAX EXECUTION PATH
                    # Skips: verificator, tool-call enforcement, semantic overlap,
                    #        stale-quote staleness rejection.
                    # Keeps: Reg T / SMA / margin validation, ownership check.
                    # Uses market orders with ±0.1% fill buffer.
                    # ---------------------------------------------------------------
                    if d.model_provider == "minimax":
                        from execution.market_data import MarketDataManager

                        mdm = MarketDataManager()

                        # Hard ownership stop for SELL
                        if d.signal.upper() == "SELL" and d.ticker not in portfolio.positions:
                            logger.warning(f"[MiniMax][{d.ticker}] REJECTED (Ownership): SELL for unheld ticker.")
                            save_decision(
                                sb_client,
                                d,
                                status="REJECTED_OWNERSHIP",
                                metadata={"reason": "Ticker not held."},
                            )
                            async with counters["lock"]:
                                counters["rejected"] += 1
                            return False

                        # Market price with ±0.5% fill buffer
                        market_price = validation.market_price
                        if not market_price or market_price <= 0:
                            logger.error(f"[MiniMax][{d.ticker}] No valid market price.")
                            async with counters["lock"]:
                                counters["rejected"] += 1
                            return False

                        if d.signal.upper() == "BUY":
                            exec_price = round(market_price * 1.005, 2)
                        else:
                            exec_price = round(market_price * 0.995, 2)

                        logger.info(
                            f"[MiniMax][{d.ticker}] Market order: {d.signal} @ ${exec_price:.2f} "
                            f"(market: ${market_price:.2f}, buffer: 0.5%)"
                        )

                        # JIT refresh to capture any concurrent trades
                        await portfolio.initialize()

                        # Fetch fresh prices for Reg T calculation
                        all_pos_tickers = list(portfolio.positions.keys())
                        if d.ticker not in all_pos_tickers:
                            all_pos_tickers.append(d.ticker)
                        fresh_quotes = await mdm.get_quotes(all_pos_tickers)
                        fresh_p_map = {t: data.price for t, data in fresh_quotes.items()}
                        portfolio.calculate_reg_t_metrics(fresh_p_map)

                        # Quantity sizing
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

                        else:  # SELL
                            if d.ticker not in portfolio.positions:
                                save_decision(
                                    sb_client,
                                    d,
                                    status="REJECTED_OWNERSHIP",
                                    metadata={"reason": "Ticker sold by concurrent trade."},
                                )
                                async with counters["lock"]:
                                    counters["rejected"] += 1
                                return False
                            held_qty = portfolio.positions[d.ticker].quantity
                            requested_qty = getattr(d, "quantity", None) or int(
                                ((d.allocation_percentage or 100) / 100.0) * held_qty
                            )
                            qty = min(requested_qty, held_qty)

                        if qty <= 0:
                            qty = getattr(d, "quantity", 0) or 1

                        if qty <= 0:
                            async with counters["lock"]:
                                counters["rejected"] += 1
                            return False

                        # Full Reg T margin validation (kept for MiniMax)
                        validation_res = portfolio.validate_trade(
                            d.ticker, qty, exec_price, d.signal, is_sell_tool_used=True
                        )
                        if not validation_res.passed:
                            logger.warning(f"[MiniMax][{d.ticker}] REJECTED (Margin): {validation_res.reason}")
                            save_decision(
                                sb_client,
                                d,
                                status="REJECTED_MARGIN",
                                metadata={"reason": validation_res.reason},
                            )
                            async with counters["lock"]:
                                counters["rejected"] += 1
                            return False

                        # Atomic EXECUTE
                        decision_row = save_decision(
                            sb_client, d, status="VALIDATED", metadata={"info": "MiniMax market order"}
                        )
                        decision_id = decision_row.get("id")
                        if not decision_id:
                            logger.error(f"[MiniMax][{d.ticker}] Pre-save returned no decision ID — aborting trade")
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
                            # Alpaca mirror limit matches the executed buffered price
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

                        save_decision(
                            sb_client,
                            d,
                            status=status,
                            metadata=meta,
                            trade_id=str(trade_id) if trade_id else None,
                            decision_id=decision_id,
                        )
                        logger.info(f"[MiniMax][{d.ticker}] {d.signal}: Attribution saved (Status: {status}).")
                        async with counters["lock"]:
                            counters["saved"] += 1

                    # ---------------------------------------------------------------
                    # STANDARD EXECUTION PATH (all other providers)
                    # ---------------------------------------------------------------
                    else:
                        # --- SELL Guardrails ---
                        if d.signal.upper() == "SELL":
                            if d.ticker not in portfolio.positions:
                                logger.warning(f"[{d.ticker}] REJECTED (Ownership): SELL signal for unheld ticker.")
                                save_decision(
                                    sb_client, d, status="REJECTED_OWNERSHIP", metadata={"reason": "Ticker not held."}
                                )
                                async with counters["lock"]:
                                    counters["rejected"] += 1
                                return False
                            if not getattr(d, "sell_tool_called", False):
                                logger.warning(f"[{d.ticker}] REJECTED (Tool Usage): SELL without sell tool.")
                                save_decision(
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
                            logger.error(f"[{d.ticker}] No valid price.")
                            async with counters["lock"]:
                                counters["rejected"] += 1
                            return False

                        # Fetch market data for verification
                        from execution.market_data import MarketDataManager

                        mdm = MarketDataManager()
                        all_pos_tickers = list(portfolio.positions.keys())
                        if d.ticker not in all_pos_tickers:
                            all_pos_tickers.append(d.ticker)

                        quotes = await mdm.get_quotes(all_pos_tickers)
                        p_map = {t: data.price for t, data in quotes.items()}

                        verification = None
                        qty = 0

                        if d.signal.upper() == "BUY":
                            if not portfolio.metrics:
                                portfolio.calculate_reg_t_metrics(p_map)

                            from core.config import SKIP_VERIFIER_OWNER_IDS

                            if d.model_name in SKIP_VERIFIER_OWNER_IDS:
                                logger.info(
                                    f"[{d.ticker}] Skipping verification for model {d.model_name} per SKIP_VERIFIER_OWNER_IDS configuration."
                                )
                                verification = type(
                                    "VerificationResult",
                                    (),
                                    {"status": "APPROVED", "verification_reasoning": "Skipped per model config"},
                                )()
                            else:
                                # --- Skeptical Verification ---
                                logger.info(f"[{d.ticker}] Verifying...")
                                # Search for contrarian thoughts on this ticker
                                contrarian_text = "\n".join(
                                    [
                                        f"- {c.model_name}: {c.reasoning}"
                                        for c in contrarian_decisions
                                        if c.ticker == d.ticker
                                    ]
                                )

                                verification = await verify_trading_decision(
                                    decision=d,
                                    portfolio_context=await portfolio.get_portfolio_summary(p_map),
                                    aggregated_context=aggregated_context,
                                    contrarian_context=contrarian_text,
                                    uncrowded_context=uncrowded_context,
                                )

                            if verification.status == "REJECTED_VERIFICATION":
                                logger.warning(
                                    f"[{d.ticker}] REJECTED (Verification): {verification.verification_reasoning}"
                                )
                                save_decision(
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

                        # 1. Semantic Overlap (Inside Lock to prevent race between concurrent same-agent trades)
                        overlap_reason = await validate_semantic_overlap(d.ticker, d.reasoning, model_name=d.model_name)
                        if overlap_reason:
                            logger.warning(f"[{d.ticker}] REJECTED (Redundancy): {overlap_reason}")
                            save_decision(
                                sb_client,
                                d,
                                status=ValidationStatus.REJECTED_REDUNDANCY.value,
                                metadata={"reason": overlap_reason},
                            )
                            async with counters["lock"]:
                                counters["rejected"] += 1
                            return False

                        # 2. JUST-IN-TIME (JIT) Refresh
                        # Refresh entire portfolio state from DB to account for previous parallel trades
                        await portfolio.initialize()

                        # 3. Final Price Refresh (using default 2s cache)
                        final_quote = await mdm.get_quote(d.ticker)
                        if final_quote and final_quote.exists:
                            if final_quote.price != exec_price:
                                logger.info(
                                    f"[{d.ticker}] Price moved during verification: ${exec_price:.2f} -> ${final_quote.price:.2f}"
                                )
                                exec_price = final_quote.price

                            # Staleness check: compare JIT price against the price injected into the prompt
                            injected_price = getattr(d, "injected_market_price", None)
                            if injected_price and injected_price > 0:
                                drift = abs(exec_price - injected_price) / injected_price
                                if drift > 0.02:
                                    reason = f"Stale quote: market moved {drift:.1%} since analysis (analysis: ${injected_price:.2f}, current: ${exec_price:.2f})"
                                    logger.warning(f"[{d.ticker}] REJECTED (Stale Quote): {reason}")
                                    save_decision(
                                        sb_client, d, status="REJECTED_STALE_QUOTE", metadata={"reason": reason}
                                    )
                                    async with counters["lock"]:
                                        counters["rejected"] += 1
                                    return False

                        # 4. Recalculate Metrics for current trade
                        # Fetch fresh prices for ALL holdings for accurate margin check
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
                            # Use equity only (not max of equity/buying power) for minimum trade size
                            min_buy_threshold = max(MIN_TRADE_VALUE, 0.10 * total_equity)
                            usd_to_spend = (alloc_pct / 100.0) * bp

                            if usd_to_spend < min_buy_threshold and bp >= min_buy_threshold:
                                usd_to_spend = min_buy_threshold

                            qty = int(usd_to_spend / exec_price)
                            if qty * exec_price < min_buy_threshold and (qty + 1) * exec_price <= bp:
                                qty += 1

                        elif d.signal.upper() == "SELL":
                            if d.ticker not in portfolio.positions:
                                save_decision(
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
                                # Fail-safe: Reject if verifier wanted to adjust allocation but failed to provide a valid quantity
                                logger.warning(
                                    f"[{d.ticker}] REJECTED (Verification): Status is ADJUSTED_ALLOCATION "
                                    f"but adjusted_quantity is invalid ({verification.adjusted_quantity})."
                                )
                                save_decision(
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

                        # Final Margin Validation
                        validation_res = portfolio.validate_trade(
                            d.ticker, qty, exec_price, d.signal, is_sell_tool_used=getattr(d, "sell_tool_called", False)
                        )
                        if not validation_res.passed:
                            logger.warning(f"[{d.ticker}] REJECTED (Margin JIT): {validation_res.reason}")
                            save_decision(
                                sb_client, d, status="REJECTED_MARGIN", metadata={"reason": validation_res.reason}
                            )
                            async with counters["lock"]:
                                counters["rejected"] += 1
                            return False

                        # 5. Atomic EXECUTE
                        # Attribution Locking (Step 13 PRE-STEP)
                        # We pre-save to get the ID for the trade link
                        decision_row = save_decision(sb_client, d, status="VALIDATED", metadata=meta)
                        decision_id = decision_row.get("id")
                        if not decision_id:
                            logger.error(f"[{d.ticker}] Pre-save returned no decision ID — aborting trade")
                            return False

                        trade_id = await portfolio.execute_trade(
                            d.ticker, qty, exec_price, d.signal, decision_id=decision_id, current_prices=fresh_p_map
                        )

                        if trade_id:
                            status = "EXECUTED"
                            meta.update(
                                {"trade_id": str(trade_id), "info": f"Executed {d.signal} {qty} @ ${exec_price:.2f}"}
                            )
                        else:
                            status = "ERROR_EXECUTION"
                            meta.update({"info": "Execution Failed"})

                        # IMPORTANT: save_decision is idempotent based on (source_id, ticker, signal, model_provider, model_name)
                        # We call this INSIDE the lock to ensure attribution record is final before next trade starts
                        save_decision(
                            sb_client,
                            d,
                            status=status,
                            metadata=meta,
                            trade_id=str(trade_id) if trade_id else None,
                            decision_id=decision_id,
                        )
                        logger.info(f"[{d.ticker}] {d.signal}: Saved attribution (Status: {status}).")
                        async with counters["lock"]:
                            counters["saved"] += 1
                else:
                    # Not a BUY/SELL (e.g. HOLD or non-actionable)
                    # We still save attribution but it doesn't need JIT refresh logic
                    save_decision(sb_client, d, status=status, metadata=meta)
                    logger.info(f"[{d.ticker}] {d.signal}: Saved attribution (Status: {status}).")
                    async with counters["lock"]:
                        counters["saved"] += 1

            return status == "EXECUTED" or status == "VALIDATED"
        except Exception:
            logger.exception(f"Failed to process decision for {d.ticker}")
            return False


async def _stage_decision_processing(
    decisions,
    macro_events,
    data,
    aggregated_context,
    uncrowded_context,
    sb_client,
    consensus_events: list | None = None,
):
    """Stage 3: Decision attribution, validation, and execution with concurrency.

    Now runs:
    - Contrarian analysis immediately (doesn't wait for consensus)
    - Primary decision execution in parallel with contrarian
    - Consensus/momentum as fire-and-forget background tasks
    """

    # --- Start Consensus/Momentum as background tasks (fire-and-forget) ---
    async def run_consensus_background():
        try:
            nonlocal consensus_events
            if consensus_events is None:
                logger.info("Running Event Consensus Protocol (background)...")
                consensus_events = await process_consensus(macro_events)
                logger.info(f"Background consensus finished. Promoted {len(consensus_events)} events.")
            else:
                logger.info("Using pre-computed consensus events for momentum analysis.")

            logger.info("Starting Trend & Concept Momentum Analysis (background)...")
            await analyze_momentum(sb_client, consensus_events)
            logger.info("Background momentum finished.")

            await decay_stale_concepts(sb_client)
            from memory.store import decay_memories

            decay_memories(sb_client)

            return consensus_events
        except Exception as e:
            logger.error(f"Background consensus/momentum failed: {e}")
            return []

    consensus_bg_task = asyncio.create_task(run_consensus_background())

    # --- Contrarian Analysis starts IMMEDIATELY (not after consensus) ---
    logger.info("Starting Contrarian Agent Analysis (in parallel with primary decisions)...")
    contrarian_task = asyncio.create_task(
        run_contrarian_analysis(
            data,
            decisions,
            context=aggregated_context,
            portfolio=None,
            market_data=None,
            llm_client=None,
            retrieve_context_fn=None,
        )
    )

    # --- DETERMINISTIC SORTING ---
    decisions.sort(key=lambda d: (d.model_name or "", getattr(d, "original_index", 0)))

    semaphore = asyncio.Semaphore(3)
    portfolio_locks = defaultdict(asyncio.Lock)

    counters = {"saved": 0, "rejected": 0, "lock": asyncio.Lock()}

    # --- Execute primary decisions while contrarian is running ---
    logger.info(f"Executing {len(decisions)} primary decisions in parallel with contrarian...")
    primary_tasks = [
        _process_single_decision(
            d, [], aggregated_context, uncrowded_context, sb_client, semaphore, portfolio_locks, counters
        )
        for d in decisions
    ]

    await asyncio.gather(*primary_tasks)

    # --- Wait for contrarian and execute its decisions ---
    contrarian_decisions, contrarian_events = await contrarian_task
    logger.info(f"Contrarian analysis complete. Generated {len(contrarian_decisions)} decisions.")

    if contrarian_decisions:
        # Give contrarian its own semaphore to avoid overwhelming the system
        contrarian_semaphore = asyncio.Semaphore(3)
        contrarian_tasks = [
            _process_single_decision(
                d,
                contrarian_decisions,
                aggregated_context,
                uncrowded_context,
                sb_client,
                contrarian_semaphore,
                portfolio_locks,
                counters,
            )
            for d in contrarian_decisions
        ]
        await asyncio.gather(*contrarian_tasks)

    # Await consensus_bg_task at the end of decision processing to ensure it completes before exit
    logger.info("Awaiting background consensus and momentum tasks to complete...")
    await consensus_bg_task

    logger.info(f"Processing complete: {counters['saved']} saved, {counters['rejected']} rejected.")


async def _stage_snapshots_and_pca(sb_client):
    """Stage 4: Performance snapshots and PCA updates.

    Only snapshots portfolios that hold actual positions — empty cash-only
    portfolios don't change between runs and don't need daily snapshots.
    Uses batch get_quotes() for efficient parallel market data fetching.
    """
    logger.info("Starting Daily Performance Snapshot...")
    port_res = sb_client.table("portfolios").select("owner_id").execute()
    owners = [p["owner_id"] for p in port_res.data] if port_res.data else []

    if owners:
        from execution.market_data import MarketDataManager

        mdm = MarketDataManager()
        all_tickers = set()
        active_portfolios = []
        for owner in owners:
            p = Portfolio(owner_id=owner)
            await p.initialize()
            if p.positions:
                all_tickers.update(p.positions.keys())
                active_portfolios.append(p)

        if all_tickers:
            quotes = await mdm.get_quotes(list(all_tickers))
            price_map = {t: data.price for t, data in quotes.items()}
            for p in active_portfolios:
                await p.record_performance_snapshot(price_map)
                await p.save_metrics()

    logger.info("Updating PCA coordinates...")
    update_pca_coordinates(sb_client)


async def run_ingest(force: bool = False):
    """Runs the full ingestion and analysis pipeline."""
    import io
    import logging
    from datetime import datetime

    log_capture = io.StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s")
    handler.setFormatter(formatter)
    logger = logging.getLogger("engine")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)

    from zoneinfo import ZoneInfo

    now = datetime.now(UTC)
    run_id = now.strftime("%Y-%m-%d_%H-%M-%S")
    run_date = now.date()
    current_hour_et = datetime.now(ZoneInfo("America/New_York")).hour
    run_number = 1 if current_hour_et < 10 else (2 if current_hour_et < 13 else 3)

    log_blob = ""
    sb_client = None

    try:
        from core.utils import is_market_open_with_logging

        if not await is_market_open_with_logging(force):
            log_blob = log_capture.getvalue()
            if log_blob:
                try:
                    sb_client = get_supabase_client()
                    sb_client.table("ingestion_logs").insert(
                        {
                            "run_id": run_id,
                            "run_date": str(run_date),
                            "run_number": run_number,
                            "log_blob": log_blob[:1000000],
                        }
                    ).execute()
                except Exception as e:
                    logger.error(f"Failed to save ingestion log: {e}")
            return

        # Initialize Supabase client for dust cleanup and subsequent stages
        sb_client = get_supabase_client()

        # Pre-Analysis Dust Cleanup: Ensure no dust positions exist before LLMs analyze
        await _stage_dust_cleanup(sb_client)

        data, sb_client = await _stage_ingest_and_snapshot()
        if not data:
            log_blob = log_capture.getvalue()
            if log_blob:
                try:
                    sb_client.table("ingestion_logs").insert(
                        {
                            "run_id": run_id,
                            "run_date": str(run_date),
                            "run_number": run_number,
                            "log_blob": log_blob[:1000000],
                        }
                    ).execute()
                except Exception as e:
                    logger.error(f"Failed to save ingestion log: {e}")
            return

        try:
            decisions, macro_events, agg_ctx, uncrowded_ctx = await _stage_analysis_and_consensus(data, sb_client)
            from analysis.consensus import get_last_consensus_events

            consensus_events = get_last_consensus_events()
            await _stage_decision_processing(
                decisions, macro_events, data, agg_ctx, uncrowded_ctx, sb_client, consensus_events
            )
            await _stage_snapshots_and_pca(sb_client)

            # Market Feeling Analysis: Generate LLM-driven sentiment (after execution to include trades)
            logger.info("Starting Market Feeling Analysis with MiniMax...")
            market_feeling = await analyze_market_feeling()
            if market_feeling:
                logger.info(
                    f"Market feeling: {market_feeling.get('sentiment_label')} {market_feeling.get('sentiment_emoji')}"
                )
            else:
                logger.warning("Market feeling analysis did not produce a result.")
        finally:
            from execution.providers.factory import get_active_provider_class

            await get_active_provider_class().disconnect_all()

        log_blob = log_capture.getvalue()
        try:
            sb_client.table("ingestion_logs").insert(
                {"run_id": run_id, "run_date": str(run_date), "run_number": run_number, "log_blob": log_blob[:1000000]}
            ).execute()
        except Exception as e:
            logger.error(f"Failed to save ingestion log: {e}")
    finally:
        logger.removeHandler(handler)


async def run_weekend_ingest():
    """Weekend read-only pipeline: news ingestion + market feeling update."""
    import io
    import logging
    from datetime import datetime

    log_capture = io.StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s")
    handler.setFormatter(formatter)
    logger = logging.getLogger("engine")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)

    now = datetime.now(UTC)
    run_id = now.strftime("%Y-%m-%d_%H-%M-%S")
    run_date = now.date()

    log_blob = ""
    sb_client = None

    try:
        sb_client = get_supabase_client()

        data, sb_client = await _stage_ingest_and_snapshot()
        if not data:
            log_blob = log_capture.getvalue()
            if log_blob:
                try:
                    sb_client.table("ingestion_logs").insert(
                        {"run_id": run_id, "run_date": str(run_date), "run_number": 1, "log_blob": log_blob[:1000000]}
                    ).execute()
                except Exception as e:
                    logger.error(f"Failed to save ingestion log: {e}")
            return

        logger.info("Starting Weekend Market Feeling Analysis...")
        market_feeling = await analyze_market_feeling(weekend_mode=True)
        if market_feeling:
            logger.info(
                f"Weekend market feeling: {market_feeling.get('sentiment_label')} {market_feeling.get('sentiment_emoji')}"
            )
        else:
            logger.warning("Weekend market feeling analysis did not produce a result.")

        log_blob = log_capture.getvalue()
        try:
            sb_client.table("ingestion_logs").insert(
                {"run_id": run_id, "run_date": str(run_date), "run_number": 1, "log_blob": log_blob[:1000000]}
            ).execute()
        except Exception as e:
            logger.error(f"Failed to save ingestion log: {e}")
    finally:
        logger.removeHandler(handler)


async def run_post_analysis():
    """Runs the post-analysis for historical trades."""
    try:
        await perform_post_analysis(windows=[5, 14, 30])
    finally:
        # --- Provider Cleanup ---
        from execution.providers.factory import get_active_provider_class

        provider_cls = get_active_provider_class()
        await provider_cls.disconnect_all()


async def run_cause_and_effect():
    """Runs the cause-and-effect analysis for market events."""
    try:
        await perform_cause_and_effect_analysis()
    finally:
        # --- Provider Cleanup ---
        from execution.providers.factory import get_active_provider_class

        provider_cls = get_active_provider_class()
        await provider_cls.disconnect_all()


def main():
    """Main entry point for the AI Wall Street Engine CLI."""
    parser = argparse.ArgumentParser(description="AI Wall Street Engine")
    parser.add_argument(
        "command",
        choices=[
            COMMAND_INGEST,
            COMMAND_WEEKEND_INGEST,
            COMMAND_POST_ANALYSIS,
            COMMAND_GOVERNMENT,
            COMMAND_CALENDAR,
            COMMAND_CAUSE_AND_EFFECT,
            COMMAND_AUDIT,
            COMMAND_AUTORESEARCH,
            COMMAND_BOOTSTRAP_AUTORESEARCH,
            COMMAND_CLEANUP,
        ],
        help="Action to perform",
    )

    parser.add_argument("--force", action="store_true", help="Force ingestion even outside market hours")
    parser.add_argument("--dry-run", action="store_true", help="Run auto-research without writing to database")
    parser.add_argument(
        "--track-id", "--track", type=str, default="all", help="Track ID for multi-track autoresearch ('all' to run all tracks)"
    )
    parser.add_argument("--cold-start", action="store_true", help="Trigger a cold-start reset for autoresearch")

    args = parser.parse_args()

    if args.command == COMMAND_INGEST:
        asyncio.run(run_ingest(force=args.force))
    elif args.command == COMMAND_WEEKEND_INGEST:
        asyncio.run(run_weekend_ingest())
    elif args.command == COMMAND_POST_ANALYSIS:
        asyncio.run(run_post_analysis())
    elif args.command == COMMAND_GOVERNMENT:
        asyncio.run(run_government_pipeline())
    elif args.command == COMMAND_CALENDAR:
        asyncio.run(run_calendar_pipeline())
    elif args.command == COMMAND_CAUSE_AND_EFFECT:
        asyncio.run(run_cause_and_effect())
    elif args.command == COMMAND_AUDIT:
        from core.audit.analyzer import configure as configure_analyzer
        from core.audit.runner import configure as configure_audit
        from core.config import DEEPSEEK_API_KEY, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_URL

        configure_audit(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
        configure_analyzer(DEEPSEEK_API_KEY)
        asyncio.run(run_audit())
    elif args.command == COMMAND_AUTORESEARCH:
        from autoresearch.runner import run
        from core.config import AUTORESEARCH_TRACKS

        if args.track_id == "all":
            track_ids = list(AUTORESEARCH_TRACKS.keys()) if AUTORESEARCH_TRACKS else ["track_default"]
            for t_id in track_ids:
                logger.info("Executing Auto-Research cycle for track: %s", t_id)
                asyncio.run(run(dry_run=args.dry_run, track_id=t_id, cold_start=args.cold_start))
        else:
            asyncio.run(run(dry_run=args.dry_run, track_id=args.track_id, cold_start=args.cold_start))
    elif args.command == COMMAND_BOOTSTRAP_AUTORESEARCH:
        from autoresearch.bootstrap import bootstrap

        asyncio.run(bootstrap())
    elif args.command == COMMAND_CLEANUP:
        from core.cleanup import run_cleanup

        asyncio.run(run_cleanup())


if __name__ == "__main__":
    main()
