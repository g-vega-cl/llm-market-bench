import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.db import get_supabase_client


def inspect():
    client = get_supabase_client()
    print("Successfully connected to Supabase.")

    # Query for decisions with status = REJECTED_TOOL_USAGE
    response = (
        client.table("decisions")
        .select("*")
        .eq("status", "REJECTED_TOOL_USAGE")
        .order("created_at", desc=True)
        .limit(10)
        .execute()
    )

    decisions = response.data or []
    print(f"Found {len(decisions)} decisions with status = REJECTED_TOOL_USAGE.")

    for idx, d in enumerate(decisions):
        print(f"\n--- DECISION #{idx + 1} ---")
        print(f"ID: {d['id']}")
        print(f"Model: {d['model_provider']}/{d['model_name']}")
        print(f"Ticker: {d['ticker']} | Signal: {d['signal']}")
        print(f"Metadata: {json.dumps(d.get('metadata'), indent=2)}")
        print(f"Reasoning: {d.get('reasoning')[:300]}...")

        # Let's also look for reasoning logs if we can find them
        # Let's query public.llm_reasoning_logs for this source_id
        source_id = d.get("source_id")
        if source_id:
            logs_res = (
                client.table("llm_reasoning_logs").select("*").contains("metadata", {"source_id": source_id}).execute()
            )
            logs = logs_res.data or []
            print(f"Found {len(logs)} reasoning logs for source_id: {source_id}")
            for l_idx, log in enumerate(logs):
                print(f"  Log #{l_idx + 1} Model: {log.get('model_name')}")
                response_data = log.get("response")
                # print some excerpt of response to see if tool call was generated
                if isinstance(response_data, dict):
                    tool_calls = response_data.get("tool_calls")
                    if tool_calls:
                        print(f"  Tool calls: {json.dumps(tool_calls)}")
                    else:
                        print(f"  No tool_calls in response keys: {list(response_data.keys())}")
                else:
                    print(f"  Response is not a dict: {str(response_data)[:100]}")


if __name__ == "__main__":
    inspect()
