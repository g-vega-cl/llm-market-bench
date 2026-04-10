"""Entry point for the AI Wall Street Engine.

This module provides the CLI interface for running the daily pipeline,
including newsletter ingestion, database snapshotting, and LLM analysis.
"""

import argparse
import asyncio
from collections import defaultdict

from analyze import analyze_chunks, analyze_chunks_streaming
from consensus import process_consensus
from analysis.momentum import analyze_momentum, decay_stale_concepts
from analysis.contrarian import run_contrarian_analysis
from core.llm.verification import verify_trading_decision
from attribution.service import save_decision
from core.config import COMMAND_INGEST, COMMAND_POST_ANALYSIS, COMMAND_GOVERNMENT, COMMAND_CALENDAR, COMMAND_CAUSE_AND_EFFECT, COMMAND_AUDIT, logger
from core.db import get_supabase_client, upsert_newsletter_snapshot
from execution.validation import validate_decision, validate_semantic_overlap, ValidationStatus
from execution.portfolio import Portfolio
from ingest.newsletter import ingest_newsletters
from ingest.government import run_government_pipeline
from ingest.calendar import run_calendar_pipeline
from memory.store import add_memory
from analysis.post_analysis import perform_post_analysis
from analysis.pca_utils import update_pca_coordinates
from analysis.cause_and_effect_analysis import perform_cause_and_effect_analysis
from core.audit import run_audit


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
    for item in data:
        try:
            upsert_newsletter_snapshot(sb_client, item)
            saved_count += 1
        except Exception as e:
            logger.error(f"Error saving snapshot for {item.get('source_id', 'unknown')}: {e}")

    logger.info(f"Successfully saved {saved_count} snapshots to Supabase.")
    return data, sb_client


async def _stage_analysis_and_consensus(data, sb_client):
    """Stage 2: Run parallel LLM analysis and event consensus.
    
    Note: Consensus and momentum now run as background tasks in _stage_decision_processing
    to allow decision execution to start sooner.
    """
    logger.info("Starting Parallel LLM Analysis...")
    try:
        decisions, macro_events, aggregated_context, uncrowded_context = await analyze_chunks(data)
        logger.info(f"Analysis complete. Generated {len(decisions)} decisions and {len(macro_events)} raw macro events.")

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
            validation = await validate_decision(d.ticker, getattr(d, "price", None))
            
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

                    # --- SELL Guardrails ---
                    if d.signal.upper() == "SELL":
                        if d.ticker not in portfolio.positions:
                            logger.warning(f"[{d.ticker}] REJECTED (Ownership): SELL signal for unheld ticker.")
                            save_decision(sb_client, d, status="REJECTED_OWNERSHIP", metadata={"reason": "Ticker not held."})
                            async with counters["lock"]:
                                counters["rejected"] += 1
                            return False
                        if not getattr(d, "sell_tool_called", False):
                            logger.warning(f"[{d.ticker}] REJECTED (Tool Usage): SELL without sell tool.")
                            save_decision(sb_client, d, status="REJECTED_TOOL_USAGE", metadata={"reason": "Sell tool must be called."})
                            async with counters["lock"]:
                                counters["rejected"] += 1
                            return False

                    exec_price = validation.market_price or d.price
                    if not exec_price or exec_price <= 0:
                        logger.error(f"[{d.ticker}] No valid price.")
                        async with counters["lock"]:
                            counters["rejected"] += 1
                        return False

                    # --- Limit Price Check ---
                    limit_price = getattr(d, "limit_price", None)
                    if limit_price:
                        if d.signal.upper() == "BUY" and exec_price > limit_price:
                            reason = f"Limit price not met: Market (${exec_price:.2f}) > Limit (${limit_price:.2f})"
                            logger.warning(f"[{d.ticker}] REJECTED (Limit Price): {reason}")
                            save_decision(sb_client, d, status=ValidationStatus.REJECTED_LIMIT_PRICE.value, metadata={"reason": reason})
                            async with counters["lock"]:
                                counters["rejected"] += 1
                            return False
                        elif d.signal.upper() == "SELL" and exec_price < limit_price:
                            reason = f"Limit price not met: Market (${exec_price:.2f}) < Limit (${limit_price:.2f})"
                            logger.warning(f"[{d.ticker}] REJECTED (Limit Price): {reason}")
                            save_decision(sb_client, d, status=ValidationStatus.REJECTED_LIMIT_PRICE.value, metadata={"reason": reason})
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

                        # --- Skeptical Verification ---
                        logger.info(f"[{d.ticker}] Verifying...")
                        # Search for contrarian thoughts on this ticker
                        contrarian_text = "\n".join([f"- {c.model_name}: {c.reasoning}" for c in contrarian_decisions if c.ticker == d.ticker])

                        verification = await verify_trading_decision(
                            decision=d,
                            portfolio_context=await portfolio.get_portfolio_summary(p_map),
                            aggregated_context=aggregated_context,
                            contrarian_context=contrarian_text,
                            uncrowded_context=uncrowded_context
                        )

                        if verification.status == "REJECTED_VERIFICATION":
                            logger.warning(f"[{d.ticker}] REJECTED (Verification): {verification.verification_reasoning}")
                            save_decision(sb_client, d, status="REJECTED_VERIFICATION", metadata={"reason": verification.verification_reasoning})
                            async with counters["lock"]:
                                counters["rejected"] += 1
                            return False

                        meta.update({
                            "verification_reasoning": verification.verification_reasoning,
                            "verification_confidence": verification.confidence_score,
                            "suggested_alternative": verification.alternative_ticker
                        })

                    # 1. Semantic Overlap (Inside Lock to prevent race between concurrent same-agent trades)
                    overlap_reason = await validate_semantic_overlap(d.ticker, d.reasoning, model_name=d.model_name)
                    if overlap_reason:
                        logger.warning(f"[{d.ticker}] REJECTED (Redundancy): {overlap_reason}")
                        save_decision(sb_client, d, status=ValidationStatus.REJECTED_REDUNDANCY.value, metadata={"reason": overlap_reason})
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
                            logger.info(f"[{d.ticker}] Price moved during verification: ${exec_price:.2f} -> ${final_quote.price:.2f}")
                            exec_price = final_quote.price
                            
                        # Re-verify limit price with the absolute latest market data
                        if limit_price:
                            if d.signal.upper() == "BUY" and exec_price > limit_price:
                                reason = f"Limit price exceeded after JIT refresh: Market (${exec_price:.2f}) > Limit (${limit_price:.2f})"
                                logger.warning(f"[{d.ticker}] REJECTED (Limit Price JIT): {reason}")
                                save_decision(sb_client, d, status=ValidationStatus.REJECTED_LIMIT_PRICE.value, metadata={"reason": reason})
                                async with counters["lock"]:
                                    counters["rejected"] += 1
                                return False
                            elif d.signal.upper() == "SELL" and exec_price < limit_price:
                                reason = f"Limit price not met after JIT refresh: Market (${exec_price:.2f}) < Limit (${limit_price:.2f})"
                                logger.warning(f"[{d.ticker}] REJECTED (Limit Price JIT): {reason}")
                                save_decision(sb_client, d, status=ValidationStatus.REJECTED_LIMIT_PRICE.value, metadata={"reason": reason})
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

                        alloc_pct = d.allocation_percentage or 5
                        min_buy_threshold = max(MIN_TRADE_VALUE, 0.10 * max(bp, total_equity))
                        usd_to_spend = (alloc_pct / 100.0) * bp

                        if usd_to_spend < min_buy_threshold and bp >= min_buy_threshold:
                            usd_to_spend = min_buy_threshold

                        qty = int(usd_to_spend / exec_price)
                        if qty * exec_price < min_buy_threshold and (qty + 1) * exec_price <= bp:
                            qty += 1

                    elif d.signal.upper() == "SELL":
                        if d.ticker not in portfolio.positions:
                             save_decision(sb_client, d, status="REJECTED_OWNERSHIP", metadata={"reason": "Ticker sold by concurrent trade."})
                             async with counters["lock"]:
                                 counters["rejected"] += 1
                             return False
                        qty = getattr(d, "quantity", None) or int(((d.allocation_percentage or 0) / 100.0) * portfolio.positions.get(d.ticker).quantity)

                    if qty <= 0:
                        qty = getattr(d, "quantity", 0) or 1
                    
                    if verification and verification.status == "ADJUSTED_ALLOCATION" and verification.adjusted_quantity:
                        qty = verification.adjusted_quantity

                    if qty <= 0:
                        async with counters["lock"]:
                            counters["rejected"] += 1
                        return False

                    # Final Margin Validation
                    validation_res = portfolio.validate_trade(d.ticker, qty, exec_price, d.signal, is_sell_tool_used=getattr(d, "sell_tool_called", False))
                    if not validation_res.passed:
                        logger.warning(f"[{d.ticker}] REJECTED (Margin JIT): {validation_res.reason}")
                        save_decision(sb_client, d, status="REJECTED_MARGIN", metadata={"reason": validation_res.reason})
                        async with counters["lock"]:
                            counters["rejected"] += 1
                        return False
                
                    # 5. Atomic EXECUTE
                    # Attribution Locking (Step 13 PRE-STEP)
                    # We pre-save to get the ID for the trade link
                    decision_row = save_decision(sb_client, d, status="VALIDATED", metadata=meta)
                    decision_id = decision_row.get("id")

                    trade_id = await portfolio.execute_trade(d.ticker, qty, exec_price, d.signal, decision_id=decision_id, current_prices=fresh_p_map)

                    if trade_id:
                        status = "EXECUTED"
                        meta.update({"trade_id": str(trade_id), "info": f"Executed {d.signal} {qty} @ ${exec_price:.2f}"})
                    else:
                        status = "ERROR_EXECUTION"
                        meta.update({"info": "Execution Failed"})

                    # IMPORTANT: save_decision is idempotent based on (source_id, ticker, signal, model_provider, model_name)
                    # We call this INSIDE the lock to ensure attribution record is final before next trade starts
                    save_decision(sb_client, d, status=status, metadata=meta, trade_id=str(trade_id) if trade_id else None)
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
        except Exception as e:
            logger.error(f"Failed to process decision for {d.ticker}: {e}")
            return False


async def _stage_decision_processing(
    decisions, macro_events, data, aggregated_context, uncrowded_context, sb_client
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
            logger.info("Running Event Consensus Protocol (background)...")
            consensus_events = await process_consensus(macro_events)
            logger.info(f"Background consensus finished. Promoted {len(consensus_events)} events.")
            
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
            retrieve_context_fn=None
        )
    )
    
    # --- DETERMINISTIC SORTING ---
    decisions.sort(key=lambda d: (d.model_name or "", getattr(d, "original_index", 0)))

    semaphore = asyncio.Semaphore(3)
    portfolio_locks = defaultdict(asyncio.Lock)

    counters = {
        "saved": 0,
        "rejected": 0,
        "lock": asyncio.Lock()
    }

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
                d, contrarian_decisions, aggregated_context, uncrowded_context, sb_client, contrarian_semaphore, portfolio_locks, counters
            )
            for d in contrarian_decisions
        ]
        await asyncio.gather(*contrarian_tasks)
    
    # Don't await consensus_bg_task - let it run in background
    
    logger.info(f"Processing complete: {counters['saved']} saved, {counters['rejected']} rejected.")


async def _stage_snapshots_and_pca(sb_client):
    """Stage 4: Performance snapshots and PCA updates."""
    logger.info("Starting Daily Performance Snapshot...")
    port_res = sb_client.table("portfolios").select("owner_id").execute()
    owners = [p["owner_id"] for p in port_res.data] if port_res.data else []
    
    if owners:
        from execution.market_data import MarketDataManager
        mdm = MarketDataManager()
        all_tickers = set()
        portfolios = []
        for owner in owners:
            p = Portfolio(owner_id=owner)
            await p.initialize()
            all_tickers.update(p.positions.keys())
            portfolios.append(p)
        
        price_map = {t: (await mdm.get_quote(t)).price for t in all_tickers if await mdm.get_quote(t)}
        for p in portfolios:
            await p.record_performance_snapshot(price_map)
            await p.save_metrics()

    logger.info("Updating PCA coordinates...")
    update_pca_coordinates(sb_client)


async def run_ingest(force: bool = False):
    """Runs the full ingestion and analysis pipeline."""
    import io
    import logging
    from datetime import datetime, timezone

    log_capture = io.StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s")
    handler.setFormatter(formatter)
    logger = logging.getLogger("engine")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)

    now = datetime.now(timezone.utc)
    run_id = now.strftime("%Y-%m-%d_%H-%M-%S")
    run_date = now.date()
    current_hour = now.hour
    run_number = 1 if current_hour < 12 else (2 if current_hour < 15 else 3)

    log_blob = ""
    sb_client = None

    try:
        from core.utils import is_market_open_with_logging
        if not await is_market_open_with_logging(force):
            log_blob = log_capture.getvalue()
            if log_blob:
                try:
                    sb_client = get_supabase_client()
                    sb_client.table("ingestion_logs").insert({
                        "run_id": run_id,
                        "run_date": str(run_date),
                        "run_number": run_number,
                        "log_blob": log_blob[:1000000]
                    }).execute()
                except Exception as e:
                    logger.error(f"Failed to save ingestion log: {e}")
            return

        data, sb_client = await _stage_ingest_and_snapshot()
        if not data:
            log_blob = log_capture.getvalue()
            if log_blob:
                try:
                    sb_client.table("ingestion_logs").insert({
                        "run_id": run_id,
                        "run_date": str(run_date),
                        "run_number": run_number,
                        "log_blob": log_blob[:1000000]
                    }).execute()
                except Exception as e:
                    logger.error(f"Failed to save ingestion log: {e}")
            return

        try:
            decisions, macro_events, agg_ctx, uncrowded_ctx = await _stage_analysis_and_consensus(data, sb_client)
            await _stage_decision_processing(decisions, macro_events, data, agg_ctx, uncrowded_ctx, sb_client)
            await _stage_snapshots_and_pca(sb_client)
        finally:
            from execution.providers.factory import get_active_provider_class
            await get_active_provider_class().disconnect_all()

        log_blob = log_capture.getvalue()
        try:
            sb_client.table("ingestion_logs").insert({
                "run_id": run_id,
                "run_date": str(run_date),
                "run_number": run_number,
                "log_blob": log_blob[:1000000]
            }).execute()
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
        choices=[COMMAND_INGEST, COMMAND_POST_ANALYSIS, COMMAND_GOVERNMENT, COMMAND_CALENDAR, COMMAND_CAUSE_AND_EFFECT, COMMAND_AUDIT],
        help="Action to perform"
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Force ingestion even outside market hours"
    )

    args = parser.parse_args()

    if args.command == COMMAND_INGEST:
        asyncio.run(run_ingest(force=args.force))
    elif args.command == COMMAND_POST_ANALYSIS:
        asyncio.run(run_post_analysis())
    elif args.command == COMMAND_GOVERNMENT:
        asyncio.run(run_government_pipeline())
    elif args.command == COMMAND_CALENDAR:
        asyncio.run(run_calendar_pipeline())
    elif args.command == COMMAND_CAUSE_AND_EFFECT:
        asyncio.run(run_cause_and_effect())
    elif args.command == COMMAND_AUDIT:
        from core.audit.runner import configure as configure_audit
        from core.audit.analyzer import configure as configure_analyzer
        from core.config import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, DEEPSEEK_API_KEY
        configure_audit(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
        configure_analyzer(DEEPSEEK_API_KEY)
        asyncio.run(run_audit())


if __name__ == "__main__":
    main()
