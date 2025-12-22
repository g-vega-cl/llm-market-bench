import sys
import json
import argparse
from datetime import datetime
from ingest.newsletter import ingest_newsletters
from core.db import get_supabase_client, upsert_newsletter_snapshot

def main():
    parser = argparse.ArgumentParser(description="AI Wall Street Engine")
    parser.add_argument("command", choices=["ingest"], help="Action to perform")
    
    args = parser.parse_args()
    
    if args.command == "ingest":
        print(f"[{datetime.now().isoformat()}] Starting Newsletter Ingestion...")
        data = ingest_newsletters()
        print(f"Successfully ingested {len(data)} newsletters.")
        
        if data:
            print(f"[{datetime.now().isoformat()}] Starting Database Snapshotting...")
            sb_client = get_supabase_client()
            
            saved_count = 0
            for item in data:
                try:
                    upsert_newsletter_snapshot(sb_client, item)
                    saved_count += 1
                except Exception as e:
                    print(f"Error saving snapshot for {item.get('source_id', 'unknown')}: {e}")
            
            print(f"Successfully saved {saved_count} snapshots to Supabase.")
            
            # For local verification, still save to a JSON file
            output_file = f"ingest_output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(output_file, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"Verification data saved to {output_file}")

if __name__ == "__main__":
    main()
