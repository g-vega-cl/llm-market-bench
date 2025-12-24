"""Integration test for RAG context retrieval."""

import asyncio
import logging
from memory.store import add_memory, retrieve_context
from core.db import get_supabase_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test")

async def test_memory_flow():
    """Verify that we can add and retrieve memories."""
    
    test_content = "The Federal Reserve unexpectedly kept interest rates unchanged in December 2025."
    metadata = {"source": "test_script", "type": "macro"}
    
    print(f"\n1. Adding test memory: '{test_content}'")
    success = add_memory(test_content, metadata)
    if success:
        print("✅ Memory added successfully.")
    else:
        print("❌ Failed to add memory.")
        return

    print(f"\n2. Retrieving context for query: 'What did the Fed do recently?'")
    context = retrieve_context("What did the Fed do recently?")
    
    if test_content in context:
        print(f"✅ Context retrieved correctly:\n{context}")
    else:
        print(f"❌ Context retrieval failed. Result was: '{context}'")

if __name__ == "__main__":
    asyncio.run(test_memory_flow())
