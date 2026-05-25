import json
import os
import sys

# Add parent directory to sys.path so we can import core modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.db import get_supabase_client


def main():
    client = get_supabase_client()
    res = client.table("prompt_experiments").select("*").order("created_at", desc=True).execute()
    data = res.data or []

    print(f"Found {len(data)} prompt experiments:")
    print(f"{'tag':<18} | {'status':<8} | {'type':<12} | {'week':<23} | {'score':<8}")
    print("-" * 80)
    for row in data:
        metrics = row.get("metrics") or {}
        if isinstance(metrics, str):
            try:
                metrics = json.loads(metrics)
            except Exception:
                metrics = {}
        score = metrics.get("score")
        score_str = f"{score:.4f}" if score is not None else "N/A"
        week_str = f"{row.get('week_start')} - {row.get('week_end')}"
        print(
            f"{row.get('variant_tag'):<18} | {row.get('status'):<8} | {row.get('experiment_type'):<12} | {week_str:<23} | {score_str:<8}"
        )


if __name__ == "__main__":
    main()
