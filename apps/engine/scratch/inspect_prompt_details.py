import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.db import get_supabase_client


def inspect():
    client = get_supabase_client()
    print("Successfully connected to Supabase.")
    
    # Query for the latest ingestion log for claude-haiku-4-5
    response = (
        client.table("llm_reasoning_logs")
        .select("*")
        .eq("model_name", "claude-haiku-4-5")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    
    logs = response.data or []
    if not logs:
        print("No logs found.")
        return
        
    log = logs[0]
    print(f"Log ID: {log['id']}")
    print(f"Task Type: {log['task_type']}")
    
    prompt = log.get("prompt")
    print(f"Prompt is a {type(prompt)}")
    
    if isinstance(prompt, list):
        for idx, msg in enumerate(prompt):
            role = msg.get("role")
            content = msg.get("content")
            print(f"\n--- MESSAGE #{idx+1} ({role}) ---")
            if isinstance(content, str):
                # Check if it has the flattened tool call pattern
                print(f"Type: String | Length: {len(content)}")
                if "[Tool Call" in content or "[Tool Result" in content:
                    print("--> FOUND FLATTENED PATTERN!")
                print(f"Content: {content[:400]}")
                if len(content) > 400:
                    print("... [TRUNCATED] ...")
                    print(f"Tail: {content[-200:]}")
            else:
                print(f"Type: {type(content)} | Content: {str(content)[:400]}...")
                
    response_val = log.get("response")
    print("\n--- RESPONSE ---")
    print(json.dumps(response_val, indent=2))

if __name__ == "__main__":
    inspect()
