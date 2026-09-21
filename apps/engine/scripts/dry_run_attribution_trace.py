"""Dry run verification script for hard execution trace attribution.

Validates the complete end-to-end attribution lifecycle:
1. Batch newsletter ingest simulation with multiple sources.
2. Multi-turn tool invocation history parsing.
3. Execution trace compilation and decision attachment.
4. Supabase live database roundtrip verification (insert, verify JSONB metadata, cleanup).
5. Frontend data contract validation for ExecutionTraceView.
"""

import json
import os
import sys
from datetime import UTC, datetime

# Ensure engine path is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from attribution.service import save_decision
from attribution.trace import (
    attach_trace_to_decisions,
    build_execution_trace,
    extract_tool_trace_from_messages,
)
from core.db import get_supabase_client
from core.models import DecisionObject


def run_dry_run():
    print("=" * 80)
    print("HARD EXECUTION TRACE ATTRIBUTION: DRY RUN")
    print(f"Timestamp: {datetime.now(UTC).isoformat()}")
    print("=" * 80)

    # -------------------------------------------------------------------------
    # STEP 1: Simulate Multi-Newsletter Ingest Batch
    # -------------------------------------------------------------------------
    print("\n[Step 1] Preparing simulated multi-newsletter batch context...")
    simulated_chunks = [
        {
            "source_id": "news_bloomberg_tech_9812",
            "sender": "Bloomberg Technology <tech@bloomberg.com>",
            "subject": "Hyperscaler Cloud Capex Surges 45% in Q3",
            "content": "Microsoft, Alphabet, and Meta report accelerating data center investment...",
        },
        {
            "source_id": "news_reuters_semis_4311",
            "sender": "Reuters Markets <markets@reuters.com>",
            "subject": "Taiwan Foundry Supply Chain Clears Bottlenecks",
            "content": "Advanced packaging lead times drop from 8 months to 4 months...",
        },
        {
            "source_id": "news_morning_brew_7721",
            "sender": "Morning Brew <daily@morningbrew.com>",
            "subject": "Tech Opens Strong Ahead of PPI Print",
            "content": "Semiconductor stocks lead pre-market momentum as bond yields hold steady...",
        },
    ]
    print(f"  • Batch contains {len(simulated_chunks)} newsletter chunks:")
    for c in simulated_chunks:
        print(f'    - [{c["source_id"]}] {c["sender"]} :: "{c["subject"]}"')

    # -------------------------------------------------------------------------
    # STEP 2: Simulate Multi-Turn Tool Invocations
    # -------------------------------------------------------------------------
    print("\n[Step 2] Simulating LLM multi-turn tool execution loop...")
    simulated_messages = [
        {"role": "system", "content": "You are an autonomous hedge fund trading agent."},
        {
            "role": "user",
            "content": "Analyze the active newsletter batch and make portfolio decisions.",
        },
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_quote_1",
                    "function": {
                        "name": "get_stock_quote",
                        "arguments": json.dumps({"ticker": "NVDA"}),
                    },
                },
                {
                    "id": "call_history_1",
                    "function": {
                        "name": "get_price_history",
                        "arguments": json.dumps({"ticker": "NVDA", "days": 14}),
                    },
                },
            ],
        },
        {
            "role": "tool",
            "tool_call_id": "call_quote_1",
            "content": json.dumps({"price": 118.50, "volume": 42000000}),
        },
        {
            "role": "tool",
            "tool_call_id": "call_history_1",
            "content": json.dumps({"status": "uptrend", "14d_return": "+6.8%"}),
        },
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_calc_1",
                    "function": {
                        "name": "calculate_buy_quantity",
                        "arguments": json.dumps({"ticker": "NVDA", "percentage": 15}),
                    },
                }
            ],
        },
        {
            "role": "tool",
            "tool_call_id": "call_calc_1",
            "content": json.dumps({"shares": 45, "estimated_cost": 5332.50}),
        },
    ]

    extracted_tools = extract_tool_trace_from_messages(simulated_messages)
    print(f"  • Extracted {len(extracted_tools)} executed tool calls:")
    for t in extracted_tools:
        print(f"    - Tool: {t['tool']} | Ticker: {t['ticker']} | Args: {t['args']}")

    # -------------------------------------------------------------------------
    # STEP 3: Compile Execution Trace and Attach to Decisions
    # -------------------------------------------------------------------------
    print("\n[Step 3] Compiling ExecutionTrace and attaching to DecisionObject...")
    trace = build_execution_trace(simulated_chunks, simulated_messages)

    decision = DecisionObject(
        signal="BUY",
        confidence=92,
        reasoning="Synthesis of hyperscaler capex acceleration and packaging capacity normalization.",
        ticker="NVDA",
        source_id="news_bloomberg_tech_9812",  # Nominal trigger
        model_provider="anthropic",
        model_name="claude-3-5-sonnet",
        allocation_percentage=15,
    )

    attach_trace_to_decisions([decision], trace)

    print("  • Trace successfully compiled:")
    print(f"    - Active chunk IDs: {trace['active_source_ids']}")
    print(f"    - Newsletters tracked: {len(trace['newsletters'])}")
    print(f"    - Tools tracked: {len(trace['tools_called'])}")
    print(f"    - Captured at: {trace['captured_at']}")
    print(f"  • Decision metadata populated: {'execution_trace' in (decision.metadata or {})}")

    # -------------------------------------------------------------------------
    # STEP 4: Live Supabase Database Persistence Roundtrip
    # -------------------------------------------------------------------------
    print("\n[Step 4] Executing live database persistence roundtrip in Supabase...")
    sb_client = get_supabase_client()
    dry_run_source_id = f"dry_run_trace_test_{int(datetime.now(UTC).timestamp())}"
    decision.source_id = dry_run_source_id

    saved_id = None
    try:
        saved_row = save_decision(
            sb_client,
            decision,
            status="DRY_RUN_VERIFIED",
            metadata={"dry_run": True},
        )
        saved_id = saved_row.get("id")
        print(f"  ✓ Row successfully upserted to 'decisions' table with ID: {saved_id}")

        # Fetch back from database to verify JSONB roundtrip
        fetch_res = (
            sb_client.table("decisions")
            .select("id, ticker, signal, source_id, status, metadata")
            .eq("id", saved_id)
            .execute()
        )

        assert fetch_res.data, "Failed to retrieve saved decision from database"
        retrieved_row = fetch_res.data[0]
        retrieved_meta = retrieved_row.get("metadata") or {}
        retrieved_trace = retrieved_meta.get("execution_trace") or {}

        print("  ✓ Retrieved row verified from PostgreSQL:")
        print(f"    - Ticker: {retrieved_row['ticker']}")
        print(f"    - Status: {retrieved_row['status']}")
        print(f"    - Nominal source_id: {retrieved_row['source_id']}")
        print(f"    - Active source IDs in trace: {retrieved_trace.get('active_source_ids')}")
        print(f"    - Tools in trace: {[t['tool'] for t in retrieved_trace.get('tools_called', [])]}")

        # Assert full integrity
        assert retrieved_trace["active_source_ids"] == trace["active_source_ids"]
        assert len(retrieved_trace["newsletters"]) == 3
        assert len(retrieved_trace["tools_called"]) == 3
        print("  ✓ Full structural parity between Python trace and Postgres JSONB confirmed!")

    finally:
        if saved_id:
            print("\n[Step 5] Cleaning up dry-run record from database...")
            sb_client.table("decisions").delete().eq("id", saved_id).execute()
            print(f"  ✓ Test record {saved_id} cleaned up. Database remains pristine.")

    # -------------------------------------------------------------------------
    # STEP 6: Frontend Interface Contract Verification
    # -------------------------------------------------------------------------
    print("\n[Step 6] Validating frontend contract for ExecutionTraceView...")
    frontend_payload = {
        "active_source_ids": retrieved_trace.get("active_source_ids"),
        "newsletters": retrieved_trace.get("newsletters"),
        "tools_called": retrieved_trace.get("tools_called"),
        "captured_at": retrieved_trace.get("captured_at"),
    }

    # Verify fields match ExecutionTraceData interface in ExecutionTraceView.tsx
    assert isinstance(frontend_payload["active_source_ids"], list)
    assert isinstance(frontend_payload["newsletters"], list)
    assert isinstance(frontend_payload["tools_called"], list)
    for n in frontend_payload["newsletters"]:
        assert "source_id" in n and "sender" in n and "subject" in n
    for t in frontend_payload["tools_called"]:
        assert "tool" in t and "ticker" in t and "args" in t

    print("  ✓ Frontend props validation passed: 100% compliant with ExecutionTraceData.")

    print("\n" + "=" * 80)
    print("🎉 ALL DRY RUN CHECKS PASSED: Hard execution trace attribution is fully operational.")
    print("=" * 80)


if __name__ == "__main__":
    run_dry_run()
