"""PCA Utilities for Dimensionality Reduction.

This module handles fetching concept vectors from Supabase, applying PCA
to reduce them to 2 dimensions, and updating the database with the new coordinates.
"""

import json
import logging

import numpy as np
from sklearn.decomposition import PCA
from supabase import Client

logger = logging.getLogger("engine")


def update_pca_coordinates(sb_client: Client):
    """Fetches all concept vectors, calculates PCA, and updates the DB."""
    logger.info("Starting PCA update for concept metrics...")

    try:
        # 1. Fetch all concepts with their vectors
        # Limit to 10,000 to be safe, though likely much fewer
        response = sb_client.table("concept_metrics").select("*").limit(10000).execute()

        if not response.data:
            logger.info("No concepts found to update.")
            return

        concepts = response.data
        vectors = []
        ids = []

        # 2. Parse vectors
        valid_concepts = []
        for c in concepts:
            try:
                # concept_vector is stored as a JSON string or list in DB
                vec_data = c["concept_vector"]
                vec = json.loads(vec_data) if isinstance(vec_data, str) else vec_data

                vectors.append(vec)
                ids.append(c["id"])
                valid_concepts.append(c)
            except Exception as e:
                logger.warning(f"Skipping malformed vector for concept '{c.get('concept_name', 'UNKNOWN')}': {e}")

        if not vectors:
            logger.warning("No valid vectors found.")
            return

        # 3. Apply PCA
        # We need at least 2 samples to run 2-component PCA effectively
        if len(vectors) < 2:
            logger.warning("Not enough concepts to run PCA (need > 1). Skipping.")
            return

        X = np.array(vectors)
        pca = PCA(n_components=2)
        X_pca = pca.fit_transform(X)

        logger.info(f"PCA explained variance ratio: {pca.explained_variance_ratio_}")

        # 4. Update Database
        # We can't do a bulk update easily with different values for diff rows in Supabase
        # without a custom RPC or complex query. For < 1000 items, sequential updates are acceptable but slow.
        # Check if we can upsert. concept_metrics has 'id' as primary key.

        updates = []
        for i, row_data in enumerate(valid_concepts):
            row = row_data.copy()
            row["pca_x"] = float(X_pca[i, 0])
            row["pca_y"] = float(X_pca[i, 1])

            # Remove any potentially problematic auto-generated columns if necessary
            # e.g. 'created_at' usually fine to upsert back if it matches
            updates.append(row)

        # Process in batches of 100 to respect potential payload size limits
        batch_size = 100
        for i in range(0, len(updates), batch_size):
            batch = updates[i : i + batch_size]
            sb_client.table("concept_metrics").upsert(batch).execute()

        logger.info(f"Successfully updated PCA coordinates for {len(updates)} concepts.")

    except Exception as e:
        logger.error(f"Failed to update PCA coordinates: {e}")
