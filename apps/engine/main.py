"""Entry point for the AI Wall Street Engine.

This module provides the CLI interface for running the daily pipeline,
including newsletter ingestion, database snapshotting, and LLM analysis.
"""

import argparse
import asyncio

from analyze import analyze_chunks
from consensus import process_consensus
from analysis.momentum import analyze_momentum, decay_stale_concepts
from analysis.contrarian import run_contrarian_analysis
from core.llm.verification import verify_trading_decision
from attribution.service import save_decision
from core.config import COMMAND_INGEST, COMMAND_POST_ANALYSIS, COMMAND_GOVERNMENT, COMMAND_CALENDAR, COMMAND_CAUSE_AND_EFFECT, logger
from core.db import get_supabase_client, upsert_newsletter_snapshot
from execution.validation import validate_decision, ValidationStatus
from execution.portfolio import Portfolio
from ingest.newsletter import ingest_newsletters
from ingest.government import run_government_pipeline
from ingest.calendar import run_calendar_pipeline
from memory.store import add_memory
from analysis.post_analysis import perform_post_analysis
from analysis.pca_utils import update_pca_coordinates
from analysis.cause_and_effect_analysis import perform_cause_and_effect_analysis


async def run_ingest():
    """Runs the full ingestion and analysis pipeline."""
    logger.info("Starting Newsletter Ingestion...")
    data = await ingest_newsletters()

    if not data:
        logger.warning(
            "No new newsletters found to ingest. "
            "Skipping snapshotting and analysis."
        )
        return

    logger.info(f"Successfully ingested {len(data)} newsletters.")

    logger.info("Starting Database Snapshotting...")
    sb_client = get_supabase_client()

    saved_count = 0
    for item in data:
        try:
            upsert_newsletter_snapshot(sb_client, item)
            saved_count += 1
        except Exception as e:
            logger.error(
                f"Error saving snapshot for "
                f"{item.get('source_id', 'unknown')}: {e}"
            )

    logger.info(f"Successfully saved {saved_count} snapshots to Supabase.")

    # --- Parallel LLM Analysis ---
    logger.info("Starting Parallel LLM Analysis...")

    try:
            # Note: analyze_chunks now handles fetching government and lesson context
        decisions, macro_events, aggregated_context = await analyze_chunks(data)
        logger.info(
            f"Analysis complete. Generated {len(decisions)} decisions "
            f"and {len(macro_events)} raw macro events."
        )

        if not decisions and not macro_events:
            logger.warning(
                "No decisions or events generated from analysis. "
                "Check LLM provider connectivity and API keys."
            )
        
        # --- Event Consensus Protocol ---
        logger.info("Running Event Consensus Protocol...")
        consensus_events = await process_consensus(macro_events)
        logger.info(f"Consensus protocol finished. Promoted {len(consensus_events)} events to memory.")

        # --- Trend & Concept Momentum Analysis ---
        logger.info("Starting Trend & Concept Momentum Analysis...")
        await analyze_momentum(sb_client, consensus_events)

        # --- Decay Stale Concepts ---
        logger.info("Applying decay to stale concepts...")
        await decay_stale_concepts(sb_client)

        # --- Decay Stale Memories ---
        logger.info("Applying decay to stale memories...")
        from memory.store import decay_memories
        decay_memories(sb_client)

        # --- Contrarian Analysis (Phase 2.5) ---
        logger.info("Starting Contrarian Agent Analysis...")
        # We pass the aggregated context to the contrarian agent for deeper analysis
        contrarian_decisions, contrarian_events = await run_contrarian_analysis(
            data, decisions, context=aggregated_context
        )
        decisions.extend(contrarian_decisions)
        macro_events.extend(contrarian_events)

        # --- Decision Attribution & Validation ---
        saved_decisions = 0
        rejected_decisions = 0
        
        # We collect all valid decisions to perform reasoning consensus later
        actionable_decisions = []
        
        for d in decisions:
            try:
                verification = None
                # --- Pre-Market Validation (Guardrails) ---
                d.ticker = d.ticker.upper()
                validation = await validate_decision(d.ticker, getattr(d, "price", None))
                
                if validation.status != ValidationStatus.PASSED:
                    logger.warning(
                        f"[{d.ticker}] REJECTED (Market Guardrails): {validation.reason} "
                        f"({d.model_provider}/{d.model_name})"
                    )
                    # Save with REJECTED status
                    save_decision(
                        sb_client, 
                        d, 
                        status=validation.status.value,  # e.g. REJECTED_LIQUIDITY
                        metadata={"reason": validation.reason}
                    )
                    rejected_decisions += 1
                    continue

                # --- Phase 3: Reg T Validation & Execution ---
                # Only proceed if signal is actionable (BUY/SELL)
                # HOLD decisions just get saved as attribution
                
                execution_info = "Validation Passed (No Trade)"
                status = "VALIDATED"
                meta = {"info": execution_info}
                trade_id = None
                
                if d.signal.upper() in ["BUY", "SELL"]:
                    portfolio = Portfolio(owner_id=d.model_name)
                    await portfolio.initialize()
                    
                    # --- SELL Ownership Guardrail ---
                    if d.signal.upper() == "SELL" and d.ticker not in portfolio.positions:
                        logger.warning(
                            f"[{d.ticker}] REJECTED (Ownership): SELL signal for unheld ticker. "
                            f"({d.model_provider}/{d.model_name})"
                        )
                        save_decision(
                            sb_client,
                            d,
                            status="REJECTED_OWNERSHIP",
                            metadata={"reason": "Ticker not held in portfolio."}
                        )
                        rejected_decisions += 1
                        continue

                    # --- SELL Tool Usage Guardrail ---
                    if d.signal.upper() == "SELL" and not getattr(d, "sell_tool_called", False):
                        logger.warning(
                            f"[{d.ticker}] REJECTED (Tool Usage): SELL signal without calling a sell percentage tool. "
                            f"({d.model_provider}/{d.model_name})"
                        )
                        save_decision(
                            sb_client,
                            d,
                            status="REJECTED_TOOL_USAGE",
                            metadata={"reason": "A sell percentage tool must be called for all SELL signals to ensure quantity accuracy."}
                        )
                        rejected_decisions += 1
                        continue

                    # --- Quantity Calculation (Allocation % or Default) ---
                    exec_price = validation.market_price if validation.market_price else d.price
                    
                    if not exec_price or exec_price <= 0:
                         logger.error(f"Cannot execute {d.ticker}: No valid price available.")
                         rejected_decisions += 1
                         continue

                    qty = 0
                    alloc_pct = d.allocation_percentage if d.allocation_percentage and d.allocation_percentage > 0 else 5 # Fallback to 5%
                    
                    # --- Market Data for Verification & Metrics ---
                    all_pos_tickers = list(portfolio.positions.keys())
                    if d.ticker not in all_pos_tickers:
                        all_pos_tickers.append(d.ticker)
                    
                    from execution.market_data import MarketDataManager
                    mdm = MarketDataManager()
                    p_map = {}
                    for t in all_pos_tickers:
                        q = await mdm.get_quote(t)
                        if q:
                            p_map[t] = q.price
                    
                    if d.signal.upper() == "BUY":
                        # Ensure metrics are calculated if not already
                        if not portfolio.metrics:
                            portfolio.calculate_reg_t_metrics(p_map)
                        
                        # --- Second Reasoning Step (Skeptical Verification) ---
                        logger.info(f"[{d.ticker}] Starting Second-Step Verification...")
                        
                        # Prepare context
                        # We use the existing aggregated_context (already handles lessons)
                        # and we can pass any contrarian thoughts if available
                        contrarian_text = ""
                        if 'contrarian_decisions' in locals():
                            # Find if contrarian agent has thoughts on this ticker
                            relevant_c = [cd for cd in contrarian_decisions if cd.ticker == d.ticker]
                            if relevant_c:
                                contrarian_text = "\n".join([f"- {c.model_name}: {c.reasoning}" for c in relevant_c])

                        verification = await verify_trading_decision(
                            decision=d,
                            portfolio_context=portfolio.get_portfolio_summary(p_map),
                            aggregated_context=aggregated_context,
                            contrarian_context=contrarian_text
                        )
                        
                        logger.info(f"[{d.ticker}] Verification Result: {verification.status} (Conf: {verification.confidence_score}%)")
                        
                        if verification.status == "REJECTED_VERIFICATION":
                            logger.warning(
                                f"[{d.ticker}] REJECTED (Second-Step Verification): {verification.verification_reasoning} "
                                f"({d.model_provider}/{d.model_name})"
                            )
                            save_decision(
                                sb_client,
                                d,
                                status="REJECTED_VERIFICATION",
                                metadata={
                                    "reason": verification.verification_reasoning,
                                    "confidence": verification.confidence_score
                                }
                            )
                            rejected_decisions += 1
                            continue
                        
                        # Add verification metadata for approved/adjusted trades
                        meta["verification_reasoning"] = verification.verification_reasoning
                        meta["verification_confidence"] = verification.confidence_score
                        if verification.alternative_ticker:
                            meta["suggested_alternative"] = verification.alternative_ticker

                        bp = portfolio.metrics.buying_power if portfolio.metrics else 0
                        total_equity = portfolio.metrics.total_equity if portfolio.metrics else 0
                        from core.config import MIN_TRADE_VALUE
                        
                        # Rule: Minimum Buy is 10% of BP or Equity (whichever is larger), but at least MIN_TRADE_VALUE
                        min_buy_threshold = max(MIN_TRADE_VALUE, 0.10 * max(bp, total_equity))
                        
                        usd_to_spend = (alloc_pct / 100.0) * bp
                        
                        # Bump to minimum if possible
                        if usd_to_spend < min_buy_threshold and bp >= min_buy_threshold:
                            logger.info(f"[{d.ticker}] Proposed spend ${usd_to_spend:.2f} is below dynamic minimum. Bumping to ${min_buy_threshold:.2f}.")
                            usd_to_spend = min_buy_threshold
                            
                        qty = int(usd_to_spend / exec_price)
                        
                        # If rounding down put us below minimum, add one share if affordable
                        if qty * exec_price < min_buy_threshold and (qty + 1) * exec_price <= bp:
                            qty += 1

                        # Validate Trade (Reg T & Floor)
                        validation_res = portfolio.validate_trade(ticker=d.ticker, quantity=qty, price=exec_price, signal=d.signal)
                        if not validation_res.passed:
                            logger.warning(
                                f"[{d.ticker}] REJECTED (Reg T/Guardrails): {validation_res.reason} "
                                f"({d.model_provider}/{d.model_name})"
                            )
                            save_decision(
                                sb_client,
                                d,
                                status="REJECTED_MARGIN",
                                metadata={
                                    "reason": validation_res.reason,
                                    "max_shares": getattr(validation_res, "max_affordable_shares", 0)
                                }
                            )
                            rejected_decisions += 1
                            continue

                    elif d.signal.upper() == "SELL":
                        # Prioritize the quantity returned by the tool
                        if getattr(d, "quantity", None) is not None:
                            qty = d.quantity
                        else:
                            # Fallback to percentage if tool provided quantity is somehow missing
                            pos = portfolio.positions.get(d.ticker)
                            if pos:
                                qty = int((alloc_pct / 100.0) * pos.quantity)
                        
                        # Ensure metrics are calculated for validation
                        if not portfolio.metrics:
                            portfolio.calculate_reg_t_metrics(p_map)
                            
                        # Validate Trade (Minimum Trade Value)
                        validation_res = portfolio.validate_trade(ticker=d.ticker, quantity=qty, price=exec_price, signal=d.signal)
                        if not validation_res.passed:
                            logger.warning(
                                f"[{d.ticker}] REJECTED (Guardrails): {validation_res.reason} "
                                f"({d.model_provider}/{d.model_name})"
                            )
                            save_decision(
                                sb_client,
                                d,
                                status="REJECTED_MARGIN",
                                metadata={"reason": validation_res.reason}
                            )
                            rejected_decisions += 1
                            continue
                    
                    # Last line of defense: if allocation (1st choice or 5% fallback) is 0, default to 1 share
                    if qty <= 0:
                        qty = getattr(d, "quantity", 0) or 1

                    # Final check for qty still being 0 (e.g. allocation % of empty position)
                    if qty <= 0:
                         logger.warning(f"[{d.ticker}] Skipping {d.signal}: Calculated quantity is 0.")
                         rejected_decisions += 1
                         continue

                    # --- Apply Verification Adjustment ---
                    if verification and verification.status == "ADJUSTED_ALLOCATION" and verification.adjusted_quantity:
                        logger.info(f"[{d.ticker}] Applying Verifier adjustment: {qty} -> {verification.adjusted_quantity}")
                        qty = verification.adjusted_quantity
                            
                    # Execute
                    trade_id = await portfolio.execute_trade(d.ticker, qty, exec_price, d.signal)
                    
                    if trade_id:
                        execution_info = f"Executed {d.signal} {qty} @ ${exec_price:.2f}"
                        status = "EXECUTED"
                        meta = {"trade_id": str(trade_id), "info": execution_info}
                    else:
                        execution_info = "Execution Failed (DB Error/Guardrail)"
                        status = "ERROR_EXECUTION"
                        meta = {"info": execution_info}


                # --- Save Attribution ---
                # Now we save with the specific status derived from execution
                # We pass trade_id explicitly to link the decision to the trade in the DB
                save_decision(
                    sb_client, 
                    d, 
                    status=status, 
                    metadata=meta,
                    trade_id=str(trade_id) if trade_id else None
                )
                
                # Collect for consensus reasoning if executed or validated
                if status in ["EXECUTED", "VALIDATED"]:
                    actionable_decisions.append(d)

                saved_decisions += 1
                logger.info(
                    f"[{d.ticker}] {d.signal} (Conf: {d.confidence}%): "
                    f"Saved attribution for {d.model_provider}/{d.model_name}. [{execution_info}]"
                )
            except Exception as e:
                logger.error(f"Failed to process/save decision for {d.ticker}: {e}")

        logger.info(
            f"Pipeline complete. Saved {saved_decisions} decisions, "
            f"Rejected {rejected_decisions} decisions."
        )

        # --- Phase 4: Ledger & Equity Curve Update (Step 14) ---
        logger.info("Starting Daily Performance Snapshot...")
        # Get all portfolios from DB to ensure we cover everyone even if no trades today
        # In a more robust system, this list could come from config
        port_res = sb_client.table("portfolios").select("owner_id").execute()
        owners = [p["owner_id"] for p in port_res.data] if port_res.data else []
        
        if not owners:
            logger.warning("No portfolios found to snapshot.")
        else:
            # We need current prices for all held positions across all portfolios
            # To be efficient, we'll collect all unique tickers first
            all_tickers = set()
            portfolios_to_snapshot = []
            for owner in owners:
                p = Portfolio(owner_id=owner)
                await p.initialize()
                all_tickers.update(p.positions.keys())
                portfolios_to_snapshot.append(p)
            
            # Fetch current prices for all tickers
            from execution.market_data import MarketDataManager
            mdm = MarketDataManager()
            price_map = {}
            for ticker in all_tickers:
                # Use get_quote which handles caching
                data = await mdm.get_quote(ticker)
                if data:
                    price_map[ticker] = data.price
            
            # Record snapshots
            for p in portfolios_to_snapshot:
                await p.record_performance_snapshot(price_map)
                # Persist final calculated metrics back to the main portfolios table
                await p.save_metrics()

        logger.info("Performance snapshots complete.")

        # --- PCA Coordinate Update (for Frontend Map) ---
        logger.info("Updating PCA coordinates for concept map...")
        update_pca_coordinates(sb_client)

    except Exception as e:
        logger.error(f"Analysis or Consensus failed: {e}")
    finally:
        # --- Provider Cleanup ---
        from execution.providers.factory import get_active_provider_class
        provider_cls = get_active_provider_class()
        await provider_cls.disconnect_all()


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
        choices=[COMMAND_INGEST, COMMAND_POST_ANALYSIS, COMMAND_GOVERNMENT, COMMAND_CALENDAR, COMMAND_CAUSE_AND_EFFECT],
        help="Action to perform"
    )

    args = parser.parse_args()

    if args.command == COMMAND_INGEST:
        asyncio.run(run_ingest())
    elif args.command == COMMAND_POST_ANALYSIS:
        asyncio.run(run_post_analysis())
    elif args.command == COMMAND_GOVERNMENT:
        asyncio.run(run_government_pipeline())
    elif args.command == COMMAND_CALENDAR:
        asyncio.run(run_calendar_pipeline())
    elif args.command == COMMAND_CAUSE_AND_EFFECT:
        asyncio.run(run_cause_and_effect())


if __name__ == "__main__":
    main()
