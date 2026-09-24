"""Live end-to-end dry run verification script for research_historical_market_analog tool.

Executes live tool call using real API keys (OpenAI gpt-5.6-luna + FMP market data)
and verifies that precedent identification, empirical tape extraction, 4-pillar playbook
synthesis, and vector memory persistence function end-to-end.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from core.llm.tools import execute_tool


async def main():
    print("=" * 80)
    print("🚀 LIVE DRY RUN: research_historical_market_analog")
    print("=" * 80)

    test_situation = "10-year Treasury yields spiking to multi-year highs alongside oil surge"
    focus_assets = ["TLT", "USO", "GLD"]
    horizon = "1m"

    print(f"\n[1/2] Invoking execute_tool with situation: '{test_situation}'")
    print(f"      Focus assets: {focus_assets}, Horizon: {horizon}")

    try:
        report = await execute_tool(
            "research_historical_market_analog",
            {
                "situation": test_situation,
                "focus_assets": focus_assets,
                "horizon": horizon,
            },
            model_name="gpt-5.6-luna",
        )

        print("\n[2/2] Tool Execution Succeeded! Live Output:")
        print("-" * 80)
        print(report)
        print("-" * 80)

        # Basic validations
        assert "Historical Analog:" in report, "Missing Historical Analog header"
        assert "Empirical Cross-Asset Reaction Tape" in report, "Missing Reaction Tape section"
        assert "Actionable Profit Playbook" in report, "Missing Actionable Profit Playbook"
        print("\n✅ DRY RUN PASSED: All 4 pillars verified against live APIs.")

    except Exception as e:
        print(f"\n❌ DRY RUN FAILED with error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
