"""Trend & Concept Momentum Analysis logic.

This module implements Step 9 of the daily pipeline, tracking the frequency
and velocity of market concepts identified during consensus.
"""

import logging
from datetime import datetime, timedelta, timezone
from supabase import Client
from memory.embeddings import get_embeddings_batch
from core import config

logger = logging.getLogger("engine")

async def decay_stale_concepts(sb_client: Client, decay_days: int = None):
    """Apply time-based decay to velocity scores of concepts not updated recently.

    Concepts that haven't been mentioned in `decay_days` have their velocity
    reduced by 50% (half-life decay model).

    Args:
        sb_client: Supabase client instance.
        decay_days: Number of days of inactivity before decay applies.
            Defaults to MOMENTUM_DECAY_HALF_LIFE_DAYS from config.
    """
    decay_days = decay_days or config.MOMENTUM_DECAY_HALF_LIFE_DAYS
    cutoff = (datetime.now(timezone.utc) - timedelta(days=decay_days)).isoformat()

    try:
        # Fetch stale concepts with velocity > 0.01 (skip already-decayed concepts)
        response = sb_client.table("concept_metrics").select(
            "id", "concept_name", "velocity_score", "last_mention_at"
        ).lt("last_mention_at", cutoff).gt("velocity_score", 0.01).execute()

        if not response.data:
            logger.info("No stale concepts to decay.")
            return

        for concept in response.data:
            new_velocity = concept["velocity_score"] * 0.5
            sb_client.table("concept_metrics").update({
                "velocity_score": new_velocity,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", concept["id"]).execute()

        logger.info(f"Decayed velocity for {len(response.data)} stale concepts.")
    except Exception as e:
        logger.error(f"Error decaying stale concepts: {e}")


async def analyze_momentum(sb_client: Client, consensus_events: list[dict]):
    """Orchestrates momentum analysis for all new consensus events.
    
    Args:
        sb_client: Supabase client instance.
        consensus_events: List of synthesized events from the consensus protocol.
    """
    if not consensus_events:
        logger.info("No consensus events to analyze for momentum.")
        return

    concept_names = [e["event_name"] for e in consensus_events]
    logger.info(f"Analyzing momentum for {len(concept_names)} concepts...")
    
    try:
        embeddings = get_embeddings_batch(concept_names)
    except Exception as e:
        logger.error(f"Failed to get embeddings for momentum analysis: {e}")
        return

    for event, embedding in zip(consensus_events, embeddings):
        try:
            velocity = calculate_velocity(sb_client, embedding)
            update_concept_metrics(sb_client, event["event_name"], embedding, velocity)
        except Exception as e:
            logger.error(f"Failed to process momentum for '{event['event_name']}': {e}")

def calculate_velocity(sb_client: Client, embedding: list[float]) -> float:
    """Calculates a velocity score based on mention frequency acceleration.
    
    Velocity = (Mentions in last 24h) / (Avg daily mentions in previous 7 days)
    """
    now = datetime.now(timezone.utc)
    
    # Recent: last 24 hours
    recent_cutoff = (now - timedelta(hours=24)).isoformat()
    # Baseline: previous 7 days
    baseline_cutoff = (now - timedelta(days=config.MOMENTUM_BASELINE_DAYS + 1)).isoformat()

    try:
        # 1. Get recent mentions (last 24h)
        recent_res = sb_client.rpc(
            "match_memories_with_time",
            {
                "query_embedding": embedding,
                "match_threshold": config.MOMENTUM_SIMILARITY_THRESHOLD,
                "match_count": 100,
                "min_time": recent_cutoff
            }
        ).execute()
        recent_count = len(recent_res.data) if recent_res.data else 0

        # 2. Get historical mentions (last N days total)
        baseline_res = sb_client.rpc(
            "match_memories_with_time",
            {
                "query_embedding": embedding,
                "match_threshold": config.MOMENTUM_SIMILARITY_THRESHOLD,
                "match_count": 1000,
                "min_time": baseline_cutoff
            }
        ).execute()
        
        total_days_count = len(baseline_res.data) if baseline_res.data else 0
        
        # 3. Calculate baseline (total minus recent)
        baseline_count = total_days_count - recent_count
        
        # Normalize baseline to daily average. Use 0.1 floor to avoid division by zero.
        avg_baseline_daily = max(baseline_count / float(config.MOMENTUM_BASELINE_DAYS), 0.1)
        velocity = recent_count / avg_baseline_daily
        
        return velocity
        
    except Exception as e:
        logger.error(f"Error calculating velocity: {e}")
        return 0.0

def _get_90d_mentions(sb_client: Client, embedding: list[float]) -> int:
    """Helper to get mention count over the last 90 days."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=config.MOMENTUM_EXTENDED_WINDOW_DAYS)).isoformat()
    try:
        res = sb_client.rpc(
            "match_memories_with_time",
            {
                "query_embedding": embedding,
                "match_threshold": config.MOMENTUM_SIMILARITY_THRESHOLD,
                "match_count": 10000, # Large limit for 90d history
                "min_time": cutoff
            }
        ).execute()
        return len(res.data) if res.data else 0
    except Exception as e:
        logger.error(f"Error fetching 90d mentions: {e}")
        return 0

def update_concept_metrics(sb_client: Client, concept_name: str, embedding: list[float], velocity: float):
    """Upserts metrics for a concept into the concept_metrics table with semantic merging."""
    try:
        # 1. Semantic Search: Find the most similar existing concept
        match_res = sb_client.rpc(
            "match_concepts",
            {
                "query_embedding": embedding,
                "match_threshold": config.MOMENTUM_CONCEPT_MERGE_THRESHOLD,
                "match_count": 1
            }
        ).execute()
        
        now = datetime.now(timezone.utc).isoformat()
        mentions_90d = _get_90d_mentions(sb_client, embedding)
        
        if match_res.data:
            # Semantic match found - merge!
            existing = match_res.data[0]
            existing_id = existing["id"]
            existing_name = existing["concept_name"]
            new_count = existing["mention_count"] + 1
            
            sb_client.table("concept_metrics").update({
                "mention_count": new_count,
                "last_mention_at": now,
                "velocity_score": velocity,
                "updated_at": now
                # In a more advanced version, we could also store mentions_90d in a column
            }).eq("id", existing_id).execute()
            
            logger.info(f"Merged '{concept_name}' into existing concept '{existing_name}' (Similarity: {existing['similarity']:.2f})")
        else:
            # No semantic match - create new concept
            sb_client.table("concept_metrics").insert({
                "concept_name": concept_name,
                "concept_vector": embedding,
                "mention_count": 1,
                "first_mention_at": now,
                "last_mention_at": now,
                "velocity_score": velocity
            }).execute()
            logger.info(f"Created new unique concept: '{concept_name}'")
            
    except Exception as e:
        logger.error(f"Error updating concept_metrics: {e}")
