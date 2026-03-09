import os
import re
import logging
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables from apps/engine/.env
load_dotenv("apps/engine/.env")

url = os.environ.get("SUPABASE_PROJECT_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not url or not key:
    print(f"Error: SUPABASE_PROJECT_URL and SUPABASE_SERVICE_ROLE_KEY are required.")
    exit(1)

supabase = create_client(url, key)
logger = logging.getLogger("cleanup")
logging.basicConfig(level=logging.INFO)

def _normalize_future_date(date_str: Optional[str], note_str: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    """Validates and normalizes the future date string.
    Duplicate of the logic in apps/engine/core/llm/events.py
    """
    if not date_str:
        return None, note_str

    # Strict ISO 8601 (YYYY-MM-DD) check
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_str.strip()):
        try:
            # Validate actual date (e.g., no Feb 30)
            datetime.strptime(date_str.strip(), "%Y-%m-%d")
            return date_str.strip(), note_str
        except ValueError:
            pass

    # If it's not a valid ISO date, move it to the note if note is empty
    if not note_str:
        return None, date_str.strip()
    
    if date_str.strip() not in note_str:
        return None, f"{note_str} ({date_str.strip()})"
    
    return None, note_str

def cleanup_legacy_catalysts():
    # Fetch all memories that could be catalysts
    response = supabase.table("memories").select("id, target_date, importance_score, metadata, content").or_("target_date.not.is.null,metadata->is_future_catalyst.eq.true").execute()
    
    memories = response.data
    logger.info(f"Scanning {len(memories)} legacy records...")
    
    updated_count = 0
    
    for m in memories:
        m_id = m["id"]
        old_date = m.get("target_date")
        old_metadata = m.get("metadata") or {}
        old_note = old_metadata.get("future_date_note")
        importance_score = m.get("importance_score")
        
        # 1. Normalize Date
        new_date, new_note = _normalize_future_date(old_date, old_note)
        
        # 2. Fix Metadata
        new_metadata = dict(old_metadata)
        if new_note != old_note:
            new_metadata["future_date_note"] = new_note
            
        # Ensure is_future_catalyst is true if we are in this list
        new_metadata["is_future_catalyst"] = True
        
        # 3. Check for Update
        updates = {}
        if new_date != old_date:
            updates["target_date"] = new_date
            
        if new_metadata != old_metadata:
            updates["metadata"] = new_metadata
            
        # If importance_score is missing, we can't easily fix it without LLM,
        # but we ensure it's at least recorded.
        
        if updates:
            logger.info(f"Updating Memory {m_id}: {old_date} -> {new_date} | Note: {new_note}")
            supabase.table("memories").update(updates).eq("id", m_id).execute()
            updated_count += 1
            
    logger.info(f"Cleanup complete. Updated {updated_count} records.")

if __name__ == "__main__":
    cleanup_legacy_catalysts()
