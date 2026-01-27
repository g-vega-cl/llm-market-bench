"""Script to recalculate velocity scores for all concepts.

This is a one-off maintenance script to fix velocity scores after the formula update.
"""

import sys
import os
import logging
from datetime import datetime, timezone
import tqdm

# Add the directory containing this script to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.db import get_supabase_client
from analysis.momentum import calculate_velocity

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("engine")

def main():
    """Recalculate velocity for all concepts."""
    sb = get_supabase_client()
    
    logger.info("Fetching all concepts...")
    try:
        # Fetch all concepts. Assuming not too many for memory (<10k).
        # If massive, would need pagination.
        response = sb.table("concept_metrics").select("id", "concept_name", "concept_vector").execute()
        concepts = response.data
        
        if not concepts:
            logger.info("No concepts found.")
            return

        logger.info(f"Found {len(concepts)} concepts. Recalculating velocity...")
        
        updated_count = 0
        
        for concept in tqdm.tqdm(concepts):
            try:
                c_id = concept["id"]
                concept_name = concept["concept_name"]
                
                # Regerate embedding with proper prefix for memory matching
                # in a real run we use get_embedding, but for speed let's assume
                # the passed vector is okay OR we should regenerate it if we want
                # to be 100% sure about the prefix matching.
                # Momentum analysis now uses f"MARKET EVENT: {concept_name}"
                from memory.embeddings import get_embedding
                proper_text = f"MARKET EVENT: {concept_name}"
                vector = get_embedding(proper_text)
                
                if not vector:
                    logger.warning(f"Could not get embedding for {concept_name}")
                    continue

                # Recalculate
                new_velocity = calculate_velocity(sb, vector)
                
                # Update DB
                sb.table("concept_metrics").update({
                    "concept_vector": vector, # Update to the new prefixed vector!
                    "velocity_score": new_velocity,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }).eq("id", c_id).execute()
                
                updated_count += 1
                
            except Exception as e:
                logger.error(f"Error processing concept {concept.get('concept_name')}: {e}")
        
        logger.info(f"Successfully recalculated {updated_count}/{len(concepts)} concepts.")
            
    except Exception as e:
        logger.error(f"Failed to fetch concepts: {e}")

if __name__ == "__main__":
    main()
