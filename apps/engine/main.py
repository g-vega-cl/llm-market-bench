import sys
import json
import argparse
from datetime import datetime
from ingest.newsletter import ingest_newsletters

def main():
    parser = argparse.ArgumentParser(description="AI Wall Street Engine")
    parser.add_argument("command", choices=["ingest"], help="Action to perform")
    
    args = parser.parse_args()
    
    if args.command == "ingest":
        print(f"[{datetime.now().isoformat()}] Starting Newsletter Ingestion...")
        data = ingest_newsletters()
        print(f"Successfully ingested {len(data)} newsletters.")
        
        # For now, just print the count. Later steps will handle database snapshotting.
        # We could also save to a temporary JSON for verification.
        if data:
            output_file = f"ingest_output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(output_file, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"Sample data saved to {output_file}")

if __name__ == "__main__":
    main()
