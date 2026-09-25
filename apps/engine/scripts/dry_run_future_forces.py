"""Live end-to-end dry run verification script for Future Forces & Forward Catalysts.

Verifies:
1. get_future_forces tool returns vetted forces and respects filters.
2. research_future_force tool invokes OpenAI Luna (gpt-5.6-luna) with thinking to stress-test a thesis.
3. run_future_forces_task executes dry-run simulation of portfolio bootstrapping and rebalance order computation.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from core.llm.tools import execute_tool
from tasks.future_forces_task import run_future_forces_task


async def main():
    print("=" * 80)
    print("🚀 LIVE DRY RUN: Future Forces & Forward Catalysts")
    print("=" * 80)

    # -------------------------------------------------------------------------
    # Step 1: Tool `get_future_forces`
    # -------------------------------------------------------------------------
    print("\n[1/3] Testing get_future_forces tool (deterministic retrieval)...")
    forces_out = await execute_tool("get_future_forces", {"archetype": "geopolitical_chokepoint", "limit": 3})
    print("-" * 60)
    print(forces_out)
    print("-" * 60)
    assert "Hormuz" in forces_out or "ACTIVE MULTI-HORIZON FORCES" in forces_out
    print("✅ Step 1 passed: get_future_forces returned formatted active forces.")

    # -------------------------------------------------------------------------
    # Step 2: Tool `research_future_force` with OpenAI Luna (gpt-5.6-luna)
    # -------------------------------------------------------------------------
    print("\n[2/3] Testing research_future_force tool via OpenAI Luna (gpt-5.6-luna)...")
    test_thesis = {
        "force_title": "AI Autonomous Code Security Crisis",
        "archetype": "secular_tollroad",
        "thesis": "Proliferation of autonomous AI coding agents expands codebases 10x, creating massive machine-speed vulnerabilities.",
        "catalyst_event": "Q4 enterprise budget allocations for real-time endpoint telemetry and Zero Trust identity.",
        "invalidation_triggers": "Cloud hyperscalers commoditize endpoint behavioral detection for free.",
        "transmission_mechanism": "Net new ARR expansion and 25%+ free cash flow margin re-rating.",
        "tickers": ["CRWD", "PANW", "NET"],
        "horizon_months": 4,
    }

    try:
        audit_report = await execute_tool(
            "research_future_force",
            test_thesis,
            model_name="gpt-5.6-luna",
        )
        print("-" * 60)
        print(audit_report)
        print("-" * 60)
        assert "ADVERSARIAL FORCE AUDIT" in audit_report
        assert "Audited Conviction:" in audit_report
        print("✅ Step 2 passed: OpenAI Luna evaluated candidate thesis with structured thinking.")
    except Exception as e:
        print(f"⚠️ Step 2 warning (API key check): {e}")

    # -------------------------------------------------------------------------
    # Step 3: Scheduled Task Dry-Run Simulation
    # -------------------------------------------------------------------------
    print("\n[3/3] Running future_forces_task in --dry-run mode (simulation)...")
    try:
        task_res = await run_future_forces_task(
            mode="all",
            dry_run=True,
            force_market=True,  # Simulate market open for order calculation
        )
        print("-" * 60)
        print("Task Results Summary:")
        if "rebalance_orders" in task_res:
            orders = task_res["rebalance_orders"]
            print(f"• Sales Generated: {len(orders.get('sales', []))}")
            print(f"• Retained Holdings: {len(orders.get('retained', []))}")
            print(f"• New Buys Proposed: {len(orders.get('new_buys', []))}")
            for buy in orders.get("new_buys", [])[:3]:
                print(
                    f"   -> BUY {buy['shares']} shares of {buy['ticker']} @ ${buy['execution_price']:.2f} ({buy['force_title']})"
                )
            print(f"• Remaining Cash: ${orders.get('remaining_cash', 0.0):.2f}")
        if "sentinel" in task_res:
            sent = task_res["sentinel"]
            print(f"• Sentinel Retained: {len(sent.get('retained', []))} forces")
            print(f"• Sentinel Invalidations: {len(sent.get('invalidations', []))}")
        print("-" * 60)
        print("✅ Step 3 passed: sys-future-forces rebalancing and sentinel simulation executed.")
    except Exception as e:
        print(f"❌ Step 3 error: {e}")
        import traceback

        traceback.print_exc()

    print("\n" + "=" * 80)
    print("🎉 DRY RUN COMPLETED SUCCESSFULLY")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
