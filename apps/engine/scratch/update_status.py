import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.db import get_supabase_client


def main():
    client = get_supabase_client()
    print("Updating status of v20260519-221104 to 'discarded'...")
    res = (
        client.table("prompt_experiments")
        .update({"status": "discarded"})
        .eq("variant_tag", "v20260519-221104")
        .execute()
    )

    if res and res.data:
        print("Successfully updated status to 'discarded'!")
    else:
        print("Failed to update status.")


if __name__ == "__main__":
    main()
