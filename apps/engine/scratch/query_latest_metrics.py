import json
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.db import get_supabase_client


def main():
    client = get_supabase_client()
    res = client.table("prompt_experiments").select("*").eq("variant_tag", "v20260524-221848").maybe_single().execute()
    if res and res.data:
        metrics = res.data.get("metrics")
        if isinstance(metrics, str):
            metrics = json.loads(metrics)
        print("Metrics structure:")
        print(json.dumps(metrics, indent=2))
    else:
        print("Variant not found")


if __name__ == "__main__":
    main()
