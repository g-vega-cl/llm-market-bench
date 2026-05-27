import os
import sys
from collections import Counter

# Set up path to import from apps/engine
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.db import get_supabase_client


def run():
    client = get_supabase_client()
    print("Successfully connected to Supabase.")

    # 1. Fetch recent decisions
    print("\n--- QUERYING RECENT DECISIONS ---")
    response = client.table("decisions").select("*").order("created_at", desc=True).limit(500).execute()
    decisions = response.data or []
    print(f"Retrieved {len(decisions)} recent decisions.")

    if not decisions:
        print("No decisions found in the database.")
        return

    # Total stats
    status_counter = Counter()
    signal_counter = Counter()
    provider_model_counter = Counter()
    rejection_reasons = Counter()

    # Grouped stats: (model, signal) -> status
    grouped = {}

    for d in decisions:
        status = d.get("status", "UNKNOWN")
        signal = d.get("signal", "UNKNOWN")
        model = d.get("model_name", "UNKNOWN")
        provider = d.get("model_provider", "UNKNOWN")
        metadata = d.get("metadata", {})

        status_counter[status] += 1
        signal_counter[signal] += 1
        provider_model_counter[f"{provider}/{model}"] += 1

        key = (f"{provider}/{model}", signal)
        if key not in grouped:
            grouped[key] = Counter()
        grouped[key][status] += 1

        if status.startswith("REJECTED"):
            # Check metadata or reasoning for reasons
            reason = metadata.get("rejection_reason") or metadata.get("error") or "Unknown Rejection"
            # If not explicitly in metadata, check if hard enforcement was mentioned
            if (
                "without executing" in str(d.get("reasoning", "")).lower()
                or "hard enforcement" in str(metadata).lower()
            ):
                reason = "Hard Enforcement (Missing Tool Call)"
            rejection_reasons[reason] += 1

    print("\n--- OVERALL DECISION STATUSES ---")
    for status, count in status_counter.most_common():
        print(f"  {status}: {count}")

    print("\n--- OVERALL SIGNALS ---")
    for signal, count in signal_counter.most_common():
        print(f"  {signal}: {count}")

    print("\n--- REJECTION REASONS ---")
    if not rejection_reasons:
        print("  No rejected decisions found in this batch.")
    for reason, count in rejection_reasons.most_common():
        print(f"  {reason}: {count}")

    print("\n--- DETAILED BREAKDOWN BY MODEL ---")
    for (model, signal), statuses in sorted(grouped.items()):
        status_str = ", ".join(f"{st}={count}" for st, count in statuses.items())
        print(f"  {model} | {signal:4s} -> {status_str}")


if __name__ == "__main__":
    run()
