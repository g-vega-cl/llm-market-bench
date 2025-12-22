import os
from typing import Any, Dict, List
from supabase import create_client, Client
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file in the apps/engine directory
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

SUPABASE_URL = os.getenv("SUPABASE_PROJECT_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

def get_supabase_client() -> Client:
    """Initializes and returns a Supabase client using the service role key."""
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        raise ValueError("Supabase configuration missing: ensure SUPABASE_PROJECT_URL and SUPABASE_SERVICE_ROLE_KEY are set.")
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

def upsert_newsletter_snapshot(client: Client, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Upserts a newsletter snapshot into the database.
    Uses (date, source_id) to prevent duplicates.
    """
    # Prepare the payload for Supabase
    # The newsletter.py output has: source_id, chunk_hash, sender, date, subject, content, ingested_at
    payload = {
        "source_id": data["source_id"],
        "chunk_hash": data["chunk_hash"],
        "sender": data["sender"],
        "subject": data["subject"],
        "content": data["content"],
        "date": data["date"],
    }
    
    # Supabase upsert using the unique constraint (date, source_id)
    response = client.table("newsletter_snapshots").upsert(
        payload, 
        on_conflict="date,source_id"
    ).execute()
    
    return response.data[0] if response.data else {}
