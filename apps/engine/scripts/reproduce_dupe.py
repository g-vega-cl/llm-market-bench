import asyncio
import logging
import sys

sys.path.insert(0, "..")
from core.db import get_supabase_client
from memory.store import add_memory

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("engine")


async def reproduce():
    logger.info("Starting reproduction script...")

    # 1. Add a base memory
    base_content = (
        "Inflation is rising rapidly due to supply chain constraints, causing the Fed to consider rate hikes."
    )
    base_id = add_memory(
        content=base_content, metadata={"test": "reproduction", "type": "base"}, memory_type="TEST_EVENT"
    )
    logger.info(f"Added base memory: {base_id}")

    # 2. Add a semantically similar memory
    dupe_content = (
        "Supply chain issues are driving up inflation, leading to potential Federal Reserve interest rate increases."
    )

    # Check if standard add_memory blocks it (it SHOULD now with check_similarity=True)
    dupe_id = add_memory(
        content=dupe_content,
        metadata={"test": "reproduction", "type": "dupe"},
        memory_type="TEST_EVENT",
        check_similarity=True,
        lookback_hours=1,
    )
    logger.info(f"Added duplicate memory: {dupe_id}")

    if dupe_id:
        logger.info("FAILURE: Duplicate memory was allowed.")
    else:
        logger.info("SUCCESS: Duplicate memory was blocked.")

    # 3. Validation manually (optional now)
    # is_dupe = add_memory(dupe_content, check_similarity=True, lookback_hours=1)
    # logger.info(f"detected dupe: {is_dupe is None}")

    # Cleanup
    client = get_supabase_client()
    if base_id:
        client.table("memories").delete().eq("id", base_id).execute()
    if dupe_id:
        client.table("memories").delete().eq("id", dupe_id).execute()
    logger.info("Cleanup complete.")


if __name__ == "__main__":
    import os
    import sys

    # Add project root to path
    sys.path.append(os.getcwd())

    asyncio.run(reproduce())
