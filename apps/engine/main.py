"""Entry point for the AI Wall Street Engine.

This module provides the CLI interface for running the daily pipeline,
including newsletter ingestion, database snapshotting, and LLM analysis.
"""

import argparse
import asyncio

from analyze import analyze_chunks
from consensus import process_consensus
from analysis.momentum import analyze_momentum, decay_stale_concepts
from attribution.service import save_decision
from core.config import COMMAND_INGEST, logger
COMMAND_POST_MORTEM = "post-mortem"
from core.db import get_supabase_client, upsert_newsletter_snapshot
from execution.validation import validate_decision, ValidationStatus
from execution.portfolio import Portfolio
from ingest.newsletter import ingest_newsletters
from memory.store import add_memory
from analysis.post_mortem import perform_post_mortems


async def run_ingest():
    """Runs the full ingestion and analysis pipeline."""
    logger.info("Starting Newsletter Ingestion...")
    data = ingest_newsletters()

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
        decisions, macro_events = await analyze_chunks(data)
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

        # --- Decision Attribution & Validation ---
        saved_decisions = 0
        rejected_decisions = 0
        
        for d in decisions:
            try:
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

                    # --- Quantity Calculation (Allocation % or Default) ---
                    exec_price = validation.market_price if validation.market_price else d.price
                    
                    if not exec_price or exec_price <= 0:
                         logger.error(f"Cannot execute {d.ticker}: No valid price available.")
                         rejected_decisions += 1
                         continue

                    qty = 0
                    alloc_pct = d.allocation_percentage if d.allocation_percentage and d.allocation_percentage > 0 else 5 # Fallback to 5%
                    
                    if d.signal.upper() == "BUY":
                        # Use current buying power if metrics are available, else initialize
                        if not portfolio.metrics:
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
                            portfolio.calculate_reg_t_metrics(p_map)
                        
                        bp = portfolio.metrics.buying_power if portfolio.metrics else 0
                        usd_to_spend = (alloc_pct / 100.0) * bp
                        qty = int(usd_to_spend / exec_price)
                    elif d.signal.upper() == "SELL":
                        pos = portfolio.positions.get(d.ticker)
                        if pos:
                            qty = int((alloc_pct / 100.0) * pos.quantity)
                    
                    # Last line of defense: if allocation (1st choice or 5% fallback) is 0, default to 1 share
                    if qty <= 0:
                        qty = getattr(d, "quantity", 0) or 1

                    # Final check for qty still being 0 (e.g. allocation % of empty position)
                    if qty <= 0:
                         logger.warning(f"[{d.ticker}] Skipping {d.signal}: Calculated quantity is 0.")
                         rejected_decisions += 1
                         continue

                    # --- Reg T Validation (BUY ONLY) ---
                    if d.signal.upper() == "BUY":
                        reg_t_check = portfolio.validate_trade(d.ticker, qty, exec_price)
                        if not reg_t_check.passed:
                            logger.warning(
                                f"[{d.ticker}] REJECTED (Reg T): {reg_t_check.reason} "
                                f"({d.model_provider}/{d.model_name})"
                            )
                            save_decision(
                                sb_client,
                                d,
                                status="REJECTED_MARGIN",
                                metadata={
                                    "reason": reg_t_check.reason,
                                    "max_shares": reg_t_check.max_affordable_shares
                                }
                            )
                            rejected_decisions += 1
                            continue
                            
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
                
                # --- Step 15: Long-term Memory Embedding ---
                if d.reasoning:
                    memory_content = (
                        f"DECISION REASONING: {d.ticker} {d.signal} | "
                        f"REASONING: {d.reasoning}"
                    )
                    add_memory(
                        content=memory_content,
                        metadata={
                            "type": "decision_reasoning",
                            "ticker": d.ticker,
                            "signal": d.signal,
                            "model_provider": d.model_provider,
                            "model_name": d.model_name,
                            "source_id": d.source_id,
                            "trade_id": str(trade_id) if trade_id else None
                        }
                    )

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

    except Exception as e:
        logger.error(f"Analysis or Consensus failed: {e}")


async def run_post_mortem():
    """Runs the post-mortem analysis for historical trades."""
    await perform_post_mortems(days_back=5)


def main():
    """Main entry point for the AI Wall Street Engine CLI."""
    parser = argparse.ArgumentParser(description="AI Wall Street Engine")
    parser.add_argument(
        "command",
        choices=[COMMAND_INGEST, COMMAND_POST_MORTEM],
        help="Action to perform"
    )

    args = parser.parse_args()

    if args.command == COMMAND_INGEST:
        asyncio.run(run_ingest())
    elif args.command == COMMAND_POST_MORTEM:
        asyncio.run(run_post_mortem())


if __name__ == "__main__":
    main()
