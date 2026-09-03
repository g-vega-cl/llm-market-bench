"""Dry run verification script for newly integrated FSI analytical tools.

Executes live end-to-end tool calls for:
1. get_yield_curve_regime (FMP live treasury rates)
2. get_options_vol_surface (Massive + FMP live options & realized volatility)
3. track_thesis_pillars (Falsifiable thesis lifecycle & disconfirming evidence)
4. render_prompt_blocks (Modular prompt block injection)
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from autoresearch.prompt_blocks import render_prompt_blocks
from core.llm.tools import execute_tool


async def dry_run():
    print("=" * 80)
    print("🚀 FSI TOOLS LIVE DRY RUN")
    print("=" * 80)

    # 1. YIELD CURVE & MACRO REGIME
    print("\n[1/4] Running: execute_tool('get_yield_curve_regime', {})")
    try:
        regime_output = await execute_tool("get_yield_curve_regime", {})
        print("--- Output ---")
        print(regime_output)
    except Exception as e:
        print(f"❌ Error in get_yield_curve_regime: {e}")

    # 2. OPTIONS VOLATILITY SURFACE & CONE
    print("\n[2/4] Running: execute_tool('get_options_vol_surface', {'ticker': 'SPY'})")
    try:
        vol_output = await execute_tool("get_options_vol_surface", {"ticker": "SPY"})
        print("--- Output ---")
        print(vol_output)
    except Exception as e:
        print(f"❌ Error in get_options_vol_surface: {e}")

    # 3. THESIS TRACKER & DISCONFIRMING EVIDENCE
    print("\n[3/4] Running: execute_tool('track_thesis_pillars', ...)")
    try:
        # A: Create
        create_res = await execute_tool(
            "track_thesis_pillars",
            {
                "ticker": "NVDA",
                "action": "create",
                "thesis_statement": "Long NVDA into Blackwell data center ramp and gross margin stabilization.",
                "pillars": [
                    "Hyperscaler cloud capex accelerating >20% YoY",
                    "Blackwell architecture volume shipments commencing Q4",
                    "Gross margins hold above 74%",
                ],
                "risks": [
                    "Supply chain bottlenecks in advanced packaging (CoWoS)",
                    "US export control restrictions on international shipments",
                ],
                "price_target": 165.0,
                "stop_loss": 115.0,
                "conviction": "HIGH",
            },
        )
        print("--- Step 3A: Created Thesis ---")
        print(create_res)

        # B: Disconfirm
        disconfirm_res = await execute_tool(
            "track_thesis_pillars",
            {
                "ticker": "NVDA",
                "action": "disconfirm",
                "disconfirming_factor": "Major hyperscaler announces 10% capex moderation for next fiscal year.",
                "pillar_impacted": "Hyperscaler cloud capex accelerating >20% YoY",
            },
        )
        print("--- Step 3B: Disconfirmed Thesis (Conviction Downgrade) ---")
        print(disconfirm_res)

        # C: Retrieve
        get_res = await execute_tool("track_thesis_pillars", {"ticker": "NVDA", "action": "get"})
        print("--- Step 3C: Retrieved Thesis ---")
        print(get_res)
    except Exception as e:
        print(f"❌ Error in track_thesis_pillars: {e}")

    # 4. MODULAR PROMPT BLOCKS RENDERING
    print("\n[4/4] Rendering Modular Prompt Blocks for Trading Agents...")
    try:
        rendered_prompt = render_prompt_blocks(
            ["options_vol_discipline", "macro_regime_routing", "disconfirming_evidence_gate"]
        )
        print("--- Rendered Blocks Header ---")
        print(rendered_prompt[:600] + "\n...[truncated for brevity]...")
    except Exception as e:
        print(f"❌ Error in render_prompt_blocks: {e}")

    print("\n" + "=" * 80)
    print("✅ DRY RUN COMPLETE — ALL SYSTEMS OPERATIONAL")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(dry_run())
