"""Verification script for Memory Chains."""

import asyncio
import logging
import sys
from pathlib import Path

# Add engine to path
engine_path = str(Path(__file__).parent.parent / "apps" / "engine")
sys.path.append(engine_path)

from memory.store import add_memory, update_memory_status, find_potential_ancestors
from core.llm import analyze_event_relationship

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verification")

async def verify_memory_chains():
    print("--- Memory Chains Verification ---\n")

    # 1. Add an initial "Threat" event
    content1 = "Donald Trump threatens to impose 100% tariffs on all goods from Greenland if they don't sell the island."
    print(f"1. Adding initial event: '{content1}'")
    id1 = add_memory(
        content=content1,
        metadata={"type": "consensus_event", "context": "initial_threat"}
    )
    
    if not id1:
        print("❌ Failed to add initial memory.")
        return

    print(f"✅ Initial memory added with ID: {id1}\n")

    # 2. Simulate a "Retraction" event
    content2 = "Donald Trump retracts Greenland tariff threat after successful diplomatic talks."
    print(f"2. Analyzing relationship for: '{content2}'")
    
    # Find potential ancestors
    potential_parents = find_potential_ancestors(content2, threshold=0.4)
    print(f"Found {len(potential_parents)} potential ancestors.")
    
    # Analyze relationship
    relationship = await analyze_event_relationship(content2, potential_parents)
    print(f"Relationship Analysis: {relationship}")
    
    if relationship["parent_id"] == id1 and relationship["relationship_type"] == "REVERSAL":
        print("✅ Correct relationship detected: REVERSAL of original threat.")
    else:
        print(f"❌ Incorrect relationship detection. Expected parent {id1} and REVERSAL.")
        # We'll continue anyway to see if the linking works if a parent was found
    
    parent_id = relationship.get("parent_id")
    rel_type = relationship.get("relationship_type")
    should_resolve = relationship.get("should_resolve", False)

    # 3. Add the second event with link
    print("\n3. Adding second event with link...")
    id2 = add_memory(
        content=content2,
        metadata={"type": "consensus_event", "context": "retraction"},
        parent_id=parent_id,
        status="ACTIVE",
        relationship_type=rel_type
    )
    
    if id2:
        print(f"✅ Second memory added with ID: {id2}")
        if should_resolve and parent_id:
            update_memory_status(parent_id, "RESOLVED")
            print(f"✅ Ancestor {parent_id} marked as RESOLVED.")
    else:
        print("❌ Failed to add second memory.")
        return

    print("\n--- Verification Complete ---")

if __name__ == "__main__":
    asyncio.run(verify_memory_chains())
