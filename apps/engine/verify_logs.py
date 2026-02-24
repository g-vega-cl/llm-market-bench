"""Script to verify ingestion logs using DeepSeek."""

import argparse
import asyncio
import logging
import os
import sys

# Ensure apps/engine is in path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.llm.clients import get_deepseek_client, close_client
from core.models import IngestionVerification
from core.config import DEEPSEEK_MODEL

async def verify_logs(log_path: str):
    """Reads logs and uses DeepSeek to verify execution success."""
    if not os.path.exists(log_path):
        print(f"Error: Log file {log_path} not found.")
        return

    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            logs = f.read()
    except Exception as e:
        print(f"Error reading log file {log_path}: {e}")
        return

    if not logs.strip():
        print(f"Warning: Log file {log_path} is empty.")
        return

    # Truncate logs if too long (DeepSeek usually handles 64k+ tokens, but let's stay reasonable)
    max_chars = 100000
    if len(logs) > max_chars:
        # Take the end of the logs as that's usually where errors and summaries are
        logs = logs[-max_chars:]
        print(f"Note: Logs truncated to last {max_chars} characters for analysis.")

    print(f"Analyzing {len(logs)} characters of logs using {DEEPSEEK_MODEL}...")

    client = get_deepseek_client()

    prompt = f"""You are a senior system reliability engineer. Analyze the following execution logs from an AI-driven trading pipeline.
Check for any critical errors, failed API calls (Gmail, LLMs, Financial APIs), database connection issues, or logic failures (e.g. invalid tickers, empty results).

Ignore minor warnings or expected throttling unless they lead to a total failure of a step.

LOGS:
---
{logs}
---

Your task:
1. Determine if the run was successful or if there were critical failures that need attention.
2. If there were failures, state the problem clearly.
3. Propose a specific fix or investigation step for the identified problem.

Return the result as a structured JSON object with 'status' ("PASSED" or "FAILED"), 'problem', and 'proposed_fix'."""

    try:
        res = await client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            response_model=IngestionVerification,
            messages=[
                {"role": "system", "content": "You are a system reliability engineer. Analyze logs and return structured JSON."},
                {"role": "user", "content": prompt}
            ]
        )

        print("\n" + "="*50)
        print("=== INGESTION VERIFICATION RESULT ===")
        print("="*50)
        print(f"STATUS: {res.status}")

        if res.status == "FAILED":
            print(f"\nPROBLEM IDENTIFIED:\n{res.problem}")
            print(f"\nPROPOSED FIX:\n{res.proposed_fix}")
            print("="*50 + "\n")
            sys.exit(1)
        else:
            print("\nResult: No critical issues found in the logs. Ingestion appears healthy.")

        print("="*50 + "\n")

    except Exception as e:
        print(f"Verification failed during LLM analysis: {e}")
        sys.exit(1)
    finally:
        await close_client(client, "deepseek")

def main():
    parser = argparse.ArgumentParser(description="Verify ingestion logs using DeepSeek")
    parser.add_argument("log_file", help="Path to the log file to analyze")
    args = parser.parse_args()

    asyncio.run(verify_logs(args.log_file))

if __name__ == "__main__":
    main()
