import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.db import get_supabase_client


def inspect():
    client = get_supabase_client()
    print("Successfully connected to Supabase.")

    # 1. Distinct task types
    print("\n--- DISTINCT TASK TYPES IN LOGS ---")
    types_res = client.table("llm_reasoning_logs").select("task_type").execute()
    types = set(t["task_type"] for t in types_res.data or [])
    print(f"Task types found: {types}")

    # 2. Get latest logs where model_name contains haiku and task_type contains ANALYSIS or similar
    print("\n--- LATEST ANALYSIS LOGS FOR CLAUDE HAIKU ---")
    logs_res = (
        client.table("llm_reasoning_logs")
        .select("*")
        .eq("model_name", "claude-haiku-4-5")
        .order("created_at", desc=True)
        .limit(3)
        .execute()
    )

    logs = logs_res.data or []
    print(f"Found {len(logs)} logs for claude-haiku-4-5.")

    for idx, log_entry in enumerate(logs):
        print(f"\n--- LOG #{idx + 1} ---")
        print(f"ID: {log_entry['id']}")
        print(f"Task Type: {log_entry['task_type']}")
        print(f"Metadata: {json.dumps(log_entry.get('metadata'), indent=2)}")

        prompt_data = log_entry.get("prompt")
        response_data = log_entry.get("response")

        # Look at the tools defined in the prompt (if any)
        # Claude prompts might have tools in the request or in system/user messages
        print(f"Prompt type: {type(prompt_data)}")
        if isinstance(prompt_data, list) and len(prompt_data) > 0:
            print(f"Prompt length: {len(prompt_data)} messages.")
            # Print the last message's content
            last_msg = prompt_data[-1]
            print(f"Last message role: {last_msg.get('role')}")
            content_str = str(last_msg.get("content"))
            print(f"Last message content excerpt: {content_str[:300]}...")
        else:
            print(f"Prompt excerpt: {str(prompt_data)[:300]}...")

        print(f"Response type: {type(response_data)}")
        if isinstance(response_data, dict):
            print(f"Response keys: {list(response_data.keys())}")
            if "tool_calls" in response_data:
                print(f"Response tool_calls: {json.dumps(response_data['tool_calls'], indent=2)}")
            elif "decisions" in response_data:
                # This might be structured output using instructor!
                print(f"Response decisions count: {len(response_data.get('decisions', []))}")
                for d_idx, d in enumerate(response_data.get("decisions", [])):
                    print(
                        f"  Decision #{d_idx + 1}: {d.get('ticker')} | {d.get('signal')} | buy_tool_called={d.get('buy_tool_called')} | sell_tool_called={d.get('sell_tool_called')}"
                    )
            else:
                print(f"Response: {json.dumps(response_data)[:400]}...")
        else:
            print(f"Response content: {str(response_data)[:500]}...")


if __name__ == "__main__":
    inspect()
