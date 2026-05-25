import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.db import get_supabase_client


def main():
    client = get_supabase_client()

    print("=== DATABASE CLEANUP / BACKFILL START ===")

    # 1. Backfill metrics for v20260519-221104 (the baseline prompt that actually ran during the week 2026-05-18 to 2026-05-24)
    v1_tag = "v20260519-221104"
    v1_metrics = {
        "score": -2.8643,
        "portfolio_return_pct": -0.6245,
        "spy_return_pct": 1.1467,
        "excess_return": -1.7712,
        "max_drawdown": 1.2771408345508484,
        "volatility": 8.927428469287786,
        "bond_return_pct": 0.0855,
        "dollar_return_pct": 0.2527,
        "opportunity_cost_penalty": 0.71,
        "drawdown_penalty": 0.3831,
    }

    print(f"Updating metrics for {v1_tag}...")
    res = client.table("prompt_experiments").update({"metrics": v1_metrics}).eq("variant_tag", v1_tag).execute()

    if res and res.data:
        print(f"Successfully updated {v1_tag}.")
    else:
        print(f"Failed to update {v1_tag} or variant not found.")

    # 2. Reset metrics and update week range for v20260524-221848 (the newly generated active prompt, scheduled for 2026-05-25 to 2026-05-31)
    v2_tag = "v20260524-221848"
    print(f"Updating metrics and week range for {v2_tag}...")
    res2 = (
        client.table("prompt_experiments")
        .update({"metrics": {}, "week_start": "2026-05-25", "week_end": "2026-05-31"})
        .eq("variant_tag", v2_tag)
        .execute()
    )

    if res2 and res2.data:
        print(f"Successfully updated {v2_tag}.")
    else:
        print(f"Failed to update {v2_tag} or variant not found.")

    print("=== DATABASE CLEANUP / BACKFILL COMPLETE ===")


if __name__ == "__main__":
    main()
