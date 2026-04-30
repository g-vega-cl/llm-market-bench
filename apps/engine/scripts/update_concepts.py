import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
"""Script to manually trigger PCA update for concepts.

Run this script to recalculate 2D coordinates for all market concepts.
"""

import asyncio
import logging
from core.db import get_supabase_client
from analysis.pca_utils import update_pca_coordinates

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("engine")

def main():
    """Main entry point."""
    try:
        sb = get_supabase_client()
        update_pca_coordinates(sb)
        logger.info("PCA update completed successfully.")
    except Exception as e:
        logger.error(f"Script failed: {e}")

if __name__ == "__main__":
    main()
