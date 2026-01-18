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
from core.db import get_supabase_client, upsert_newsletter_snapshot
from execution.validation import validate_decision, ValidationStatus
from execution.portfolio import Portfolio
from ingest.newsletter import ingest_newsletters


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

        # --- Decision Attribution & Validation ---
        saved_decisions = 0
        rejected_decisions = 0
        
        for d in decisions:
            try:
                # --- Pre-Market Validation (Guardrails) ---
                validation = await validate_decision(d.ticker, getattr(d, "price", None))
                
                if validation.status != ValidationStatus.PASSED:
                    logger.warning(
                        f"[{d.ticker}] REJECTED (Market Guardrails): {validation.reason} "
                        f"({d.model_provider}/{d.model_name})"
                    )
                    rejected_decisions += 1
                    continue

                # --- Phase 3: Reg T Validation & Execution ---
                # Only proceed if signal is actionable (BUY/SELL)
                # HOLD decisions just get saved as attribution
                
                execution_info = "Validation Passed (No Trade)"
                
                if d.signal.upper() in ["BUY", "SELL"]:
                    portfolio = Portfolio(owner_id=d.model_name)
                    # We need to initialize to get ID/Balance
                    await portfolio.initialize()
                    
                    # For a SELL, we might want to check ownership, but execute_trade handles that logic (allows short).
                    # For a BUY, we must check Reg T Buying Power.
                    
                    qty = getattr(d, "quantity", 0) or 10 # Default to 10 if not spec (should be spec)
                    # If using allocation %, logic would calculate qty here. 
                    # Assuming for now decision has explicit quantity or we default.
                    
                    # Use validation result price (real-time) if available, else d.price (LLM guess), else fail
                    exec_price = validation.market_price if validation.market_price else d.price
                    
                    if not exec_price or exec_price <= 0:
                         logger.error(f"Cannot execute {d.ticker}: No valid price available.")
                         rejected_decisions += 1
                         continue

                    # Validate
                    if d.signal.upper() == "BUY":
                        reg_t_check = portfolio.validate_trade(d.ticker, qty, exec_price)
                        if not reg_t_check.passed:
                            logger.warning(
                                f"[{d.ticker}] REJECTED (Reg T): {reg_t_check.reason} "
                                f"({d.model_provider}/{d.model_name})"
                            )
                            rejected_decisions += 1
                            continue
                            
                    # Execute
                    await portfolio.execute_trade(d.ticker, qty, exec_price, d.signal)
                    execution_info = f"Executed {d.signal} {qty} @ ${exec_price:.2f}"

                # --- Save Attribution ---
                # We save the decision regardless of whether it traded (it was a valid idea),
                # but maybe we should flag it if it failed Reg T? 
                # Current flow rejects loop continue on Reg T fail, so we don't save attribution for failed trades?
                # "Decision Attribution" is "What did the AI decide?". Even if rejected, it decided it.
                # Ideally we save it with a status 'REJECTED'. 
                # For now, we only save successful ones as per original loop structure.
                
                d.execution_metadata = {"info": execution_info}
                save_decision(sb_client, d)
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
    except Exception as e:
        logger.error(f"Analysis or Consensus failed: {e}")


def main():
    """Main entry point for the AI Wall Street Engine CLI."""
    parser = argparse.ArgumentParser(description="AI Wall Street Engine")
    parser.add_argument(
        "command",
        choices=[COMMAND_INGEST],
        help="Action to perform"
    )

    args = parser.parse_args()

    if args.command == COMMAND_INGEST:
        asyncio.run(run_ingest())


if __name__ == "__main__":
    main()
