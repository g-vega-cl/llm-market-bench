import json
import argparse
from datetime import datetime
from ingest.newsletter import ingest_newsletters
from core.db import get_supabase_client, upsert_newsletter_snapshot
from core.config import COMMAND_INGEST, logger

def main():
    parser = argparse.ArgumentParser(description="AI Wall Street Engine")
    parser.add_argument("command", choices=[COMMAND_INGEST], help="Action to perform")
    
    args = parser.parse_args()
    
    if args.command == COMMAND_INGEST:
        logger.info("Starting Newsletter Ingestion...")
        data = ingest_newsletters()
        logger.info(f"Successfully ingested {len(data)} newsletters.")
        
        if data:
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
            
            # --- Parallel LLM Analysis ---
            logger.info("Starting Parallel LLM Analysis...")
            import asyncio
            from analyze import analyze_chunks
            
            try:
                decisions = asyncio.run(analyze_chunks(data))
                logger.info(f"Analysis complete. Generated {len(decisions)} decisions.")
                for d in decisions:
                    logger.info(f"[{d.ticker}] {d.signal} (Conf: {d.confidence}%): {d.reasoning[:50]}...")
            except Exception as e:
                logger.error(f"Analysis failed: {e}")

if __name__ == "__main__":
    main()
