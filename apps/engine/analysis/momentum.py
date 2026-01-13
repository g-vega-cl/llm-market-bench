"""Trend & Concept Momentum Analysis logic.

This module implements Step 9 of the daily pipeline, tracking the frequency
and velocity of market concepts identified during consensus.
"""

import logging
from datetime import datetime, timedelta, timezone
from supabase import Client
from memory.embeddings import get_embeddings_batch

logger = logging.getLogger("engine")

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

def calculate_velocity(sb_client: Client, embedding: list[float], match_threshold: float = 0.85) -> float:
    """Calculates a velocity score based on mention frequency acceleration.
    
    Velocity = (Mentions in last 24h) / (Avg daily mentions in previous 7 days)
    """
    now = datetime.now(timezone.utc)
    
    # Recent: last 24 hours
    recent_cutoff = (now - timedelta(hours=24)).isoformat()
    # Baseline: previous 7 days (total 8 days of history)
    baseline_cutoff = (now - timedelta(days=8)).isoformat()

    try:
        # 1. Get recent mentions (last 24h)
        # We use a high match_count to capture most mentions
        recent_res = sb_client.rpc(
            "match_memories_with_time",
            {
                "query_embedding": embedding,
                "match_threshold": match_threshold,
                "match_count": 100,
                "min_time": recent_cutoff
            }
        ).execute()
        recent_count = len(recent_res.data) if recent_res.data else 0

        # 2. Get historical mentions (last 8 days total)
        baseline_res = sb_client.rpc(
            "match_memories_with_time",
            {
                "query_embedding": embedding,
                "match_threshold": match_threshold,
                "match_count": 1000,
                "min_time": baseline_cutoff
            }
        ).execute()
        
        total_8d_count = len(baseline_res.data) if baseline_res.data else 0
        
        # 3. Calculate baseline (total minus recent)
        baseline_count = total_8d_count - recent_count
        
        # Normalize baseline to daily average. Use 0.1 floor to avoid division by zero 
        # and give a high score to new emerging trends.
        avg_baseline_daily = max(baseline_count / 7.0, 0.1)
        velocity = recent_count / avg_baseline_daily
        
        logger.debug(
            f"Velocity calculation: {recent_count} (recent) / "
            f"{avg_baseline_daily:.2f} (avg baseline) = {velocity:.2f}"
        )
        return velocity
        
    except Exception as e:
        logger.error(f"Error calling match_memories_with_time: {e}")
        return 0.0

def update_concept_metrics(sb_client: Client, concept_name: str, embedding: list[float], velocity: float):
    """Upserts metrics for a concept into the concept_metrics table."""
    try:
        # Search for existing concept
        existing = sb_client.table("concept_metrics")\
            .select("id, mention_count")\
            .eq("concept_name", concept_name)\
            .execute()
        
        now = datetime.now(timezone.utc).isoformat()
        
        if existing.data:
            # Update existing record
            data = existing.data[0]
            new_count = data["mention_count"] + 1
            sb_client.table("concept_metrics").update({
                "mention_count": new_count,
                "last_mention_at": now,
                "velocity_score": velocity,
                "updated_at": now
            }).eq("id", data["id"]).execute()
        else:
            # Insert new record
            sb_client.table("concept_metrics").insert({
                "concept_name": concept_name,
                "concept_vector": embedding,
                "mention_count": 1,
                "first_mention_at": now,
                "last_mention_at": now,
                "velocity_score": velocity
            }).execute()
            
        logger.info(f"Updated concept metrics for '{concept_name}' (Velocity: {velocity:.2f})")
    except Exception as e:
        logger.error(f"Error updating concept_metrics table: {e}")
