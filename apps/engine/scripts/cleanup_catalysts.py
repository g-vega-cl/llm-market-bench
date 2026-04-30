import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import os
import re
import logging
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables from the same directory as the script
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(env_path)

url = os.environ.get("SUPABASE_PROJECT_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not url or not key:
    print(f"Error: SUPABASE_PROJECT_URL and SUPABASE_SERVICE_ROLE_KEY are required.")
    exit(1)

supabase = create_client(url, key)
logger = logging.getLogger("cleanup")
logging.basicConfig(level=logging.INFO)

def _extract_date_from_content(content: str) -> Optional[str]:
    """Tries to extract a YYYY-MM-DD date from the content string."""
    match = re.search(r"(\d{4}-\d{2}-\d{2})", content)
    if match:
        date_str = match.group(1)
        try:
            # Validate actual date
            datetime.strptime(date_str, "%Y-%m-%d")
            return date_str
        except ValueError:
            pass
    return None

def _normalize_future_date(date_str: Optional[str], note_str: Optional[str], content: str = "") -> tuple[Optional[str], Optional[str]]:
    """Validates and normalizes the future date string.
    If date_str is missing, attempts to extract it from content.
    """
    if not date_str:
        extracted = _extract_date_from_content(content)
        if extracted:
            return extracted, note_str
        return None, note_str

    # Strict ISO 8601 (YYYY-MM-DD) check
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_str.strip()):
        try:
            # Validate actual date (e.g., no Feb 30)
            datetime.strptime(date_str.strip(), "%Y-%m-%d")
            return date_str.strip(), note_str
        except ValueError:
            pass

    # If it's not a valid ISO date, try extracting from it or moving to note
    extracted = _extract_date_from_content(date_str)
    if extracted:
        return extracted, note_str

    if not note_str:
        return None, date_str.strip()
    
    if date_str.strip() not in note_str:
        return None, f"{note_str} ({date_str.strip()})"
    
    return None, note_str

def cleanup_legacy_catalysts():
    # Fetch all records that might be catalysts
    response = supabase.table("memories").select("id, target_date, importance_score, metadata, content").or_("target_date.not.is.null,metadata->is_future_catalyst.eq.true").execute()
    
    memories = response.data
    logger.info(f"Scanning {len(memories)} records for Horizon Watch calibration...")
    
    updated_count = 0
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    for m in memories:
        m_id = m["id"]
        content = m.get("content", "")
        content_upper = content.upper()
        old_date = m.get("target_date")
        old_metadata = m.get("metadata") or {}
        old_note = old_metadata.get("future_date_note")
        importance_score = m.get("importance_score") or 5
        
        # 1. Normalize Date (passing content for extraction fallback)
        new_date, new_note = _normalize_future_date(old_date, old_note, content)
        
        # 2. Fix Metadata
        new_metadata = dict(old_metadata)
        if new_note != old_note:
            new_metadata["future_date_note"] = new_note
            
        # 3. Strict Calibration: Determine if it's REALLY a future catalyst
        # Criteria for REJECTION as a future catalyst:
        # - Contains "[ONGOING]"
        # - Contains "ROTATION" (usually a trend)
        # - Contains "INVESTMENT" (usually a past action)
        # - Target date is in the past
        is_effectively_past = False
        if new_date and new_date < today_str:
            is_effectively_past = True
            
        is_ongoing_trend = "[ONGOING]" in content_upper or "ROTATION" in content_upper or "INVESTMENT" in content_upper
        
        # If it's old or ongoing, it's NOT a future catalyst
        if is_effectively_past or is_ongoing_trend:
            new_metadata["is_future_catalyst"] = False
            # Only set is_ongoing if it's actually an ongoing trend, not just a past event
            if is_ongoing_trend:
                new_metadata["is_ongoing"] = True
            else:
                new_metadata["is_ongoing"] = False
        else:
            # If it has a future date and high importance, it IS a catalyst
            if new_date and new_date >= today_str and importance_score >= 8:
                new_metadata["is_future_catalyst"] = True
            else:
                # If no date, or low importance, it's just a memory
                new_metadata["is_future_catalyst"] = False
        
        # 4. Check for Update
        updates = {}
        if new_date != old_date:
            updates["target_date"] = new_date
            
        if new_metadata != old_metadata:
            updates["metadata"] = new_metadata
            
        if updates:
            cat_status = "CATALYST" if new_metadata.get("is_future_catalyst") else "MEMORY"
            logger.info(f"Updating Memory {m_id}: {cat_status} | Date: {new_date} | Content: {content[:50]}...")
            supabase.table("memories").update(updates).eq("id", m_id).execute()
            updated_count += 1
            
    logger.info(f"Cleanup complete. Updated {updated_count} records.")

if __name__ == "__main__":
    cleanup_legacy_catalysts()
