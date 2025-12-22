from typing import Any, Dict
from supabase import create_client, Client
from core.config import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, logger

def get_supabase_client() -> Client:
    """Initializes and returns a Supabase client using the service role key."""
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        error_msg = "Supabase configuration missing: ensure SUPABASE_PROJECT_URL and SUPABASE_SERVICE_ROLE_KEY are set."
        logger.error(error_msg)
        raise ValueError(error_msg)
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

def upsert_newsletter_snapshot(client: Client, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Upserts a newsletter snapshot into the database.
    Uses (date, source_id) to prevent duplicates.
    """
    # Prepare the payload for Supabase
    payload = {
        "source_id": data["source_id"],
        "chunk_hash": data["chunk_hash"],
        "sender": data["sender"],
        "subject": data["subject"],
        "content": data["content"],
        "date": data["date"],
    }
    
    # Supabase upsert using the unique constraint (date, source_id)
    try:
        response = client.table("newsletter_snapshots").upsert(
            payload, 
            on_conflict="date,source_id"
        ).execute()
        
        return response.data[0] if response.data else {}
    except Exception as e:
        logger.error(f"Failed to upsert snapshot for {data.get('source_id')}: {e}")
        raise
