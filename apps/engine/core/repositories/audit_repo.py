"""Typed repository helpers for database access.

This module provides a clean abstraction over Supabase calls to ensure
consistent schema access and easier auditing/testing.
"""

from typing import Any, Dict, List, Optional
from core.db import get_supabase_client

def fetch_trade_by_id(trade_id: str) -> Optional[Dict[str, Any]]:
    client = get_supabase_client()
    res = client.table("trades").select("*").eq("id", trade_id).execute()
    return res.data[0] if res.data else None

def fetch_decision_by_id(decision_id: str) -> Optional[Dict[str, Any]]:
    client = get_supabase_client()
    res = client.table("decisions").select("*").eq("id", decision_id).execute()
    return res.data[0] if res.data else None

def fetch_news_by_source_id(source_id: str) -> Optional[Dict[str, Any]]:
    client = get_supabase_client()
    res = client.table("newsletter_snapshots").select("id, source_id").eq("source_id", source_id).execute()
    return res.data[0] if res.data else None

def fetch_reasoning_logs_for_ticker_source(ticker: str, source_id: str) -> List[Dict[str, Any]]:
    client = get_supabase_client()
    res = client.table("llm_reasoning_logs") \
        .select("id, task_type, metadata") \
        .filter("metadata->>ticker", "eq", ticker) \
        .filter("metadata->>source_id", "eq", source_id) \
        .execute()
    return res.data if res.data else []

def fetch_reasoning_logs_by_decision_id(decision_id: str) -> List[Dict[str, Any]]:
    """Fetches logs anchored by decision_id for precise lineage."""
    client = get_supabase_client()
    res = client.table("llm_reasoning_logs") \
        .select("id, task_type, metadata") \
        .filter("metadata->>decision_id", "eq", str(decision_id)) \
        .execute()
    return res.data if res.data else []

def fetch_lessons_for_trade(trade_id: str) -> List[Dict[str, Any]]:
    client = get_supabase_client()
    res = client.table("memories") \
        .select("id, metadata") \
        .eq("memory_type", "LESSON_LEARNED") \
        .filter("metadata->>trade_id", "eq", trade_id) \
        .execute()
    return res.data if res.data else []
