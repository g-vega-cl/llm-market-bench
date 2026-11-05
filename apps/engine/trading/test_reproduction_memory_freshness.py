"""Reproduction test showing ranking failure where stale decayed memories outrank fresh active memories."""

from datetime import UTC, datetime

from trading.conversational_explainer import (
    extract_search_keywords,
    rank_and_filter_memories,
)


def test_extract_search_keywords_filters_fillers():
    query = "Can the SPY go lower? Should I sell some puts or get more LEAPS?"
    kws = extract_search_keywords(query)
    assert "the" not in kws
    assert "can" not in kws
    assert "some" not in kws
    assert "get" not in kws
    assert "more" not in kws
    # "spy" and "leaps" should be extracted
    assert "spy" in kws or "leaps" in kws


def test_rank_and_filter_memories_prefers_fresh_active_over_stale_decayed():
    now_utc = datetime(2026, 11, 5, 20, 0, tzinfo=UTC)
    raw_memories = [
        # Stale memory from April 2026 with high initial importance but heavily decayed
        {
            "id": "mem-stale-apr",
            "content": "[CALENDAR EVENT] (07:30 AM) 2026-04-22: US Federal Reserve Interest Rate Decision (2026-04-29)",
            "importance_score": 10,
            "relevance_score": 0.04,
            "status": "ACTIVE",
            "created_at": "2026-04-22T07:30:00Z",
            "target_date": "2026-04-29",
            "memory_type": "CALENDAR_EVENT",
        },
        # Resolved memory from March 2026
        {
            "id": "mem-resolved",
            "content": "MARKET EVENT: Strait of Hormuz Supply Shock",
            "importance_score": 10,
            "relevance_score": 0.9,
            "status": "RESOLVED",
            "created_at": "2026-03-05T00:00:00Z",
            "memory_type": "MARKET_EVENT",
        },
        # Academic paper (textbook noise)
        {
            "id": "mem-academic",
            "content": "EMPIRICAL ASSET PRICING PRINCIPLE: The Cross-Section of Expected Stock Returns Fama French",
            "importance_score": 10,
            "relevance_score": 1.0,
            "status": "ACTIVE",
            "created_at": "2026-05-21T00:00:00Z",
            "memory_type": "ACADEMIC_PAPER",
        },
        # Fresh active memory from today (Nov 5, 2026) with importance 5, relevance 1.0
        {
            "id": "mem-fresh-today",
            "content": "THEMATIC FLOW: AI Mega-Cap Value Rotation [ONGOING] | SUMMARY: A sharp shift from tech",
            "importance_score": 5,
            "relevance_score": 1.0,
            "status": "ACTIVE",
            "created_at": "2026-11-05T20:36:32Z",
            "target_date": None,
            "memory_type": "THEMATIC_FLOW",
        },
        # Fresh active jobs report catalyst for tomorrow
        {
            "id": "mem-jobs-tomorrow",
            "content": "MARKET EVENT: November 6 Jobs Report | SUMMARY: The payrolls release",
            "importance_score": 5,
            "relevance_score": 1.0,
            "status": "ACTIVE",
            "created_at": "2026-11-05T20:35:29Z",
            "target_date": "2026-11-06",
            "memory_type": "MARKET_EVENT",
        },
    ]

    ranked = rank_and_filter_memories(raw_memories, query="SPY lower puts LEAPS", now_dt=now_utc, limit=5)
    ranked_ids = [m["id"] for m in ranked]

    # Stale April expired calendar event, resolved event, and academic paper must be excluded or lower ranked
    assert "mem-resolved" not in ranked_ids
    assert "mem-academic" not in ranked_ids
    assert "mem-stale-apr" not in ranked_ids
    # Fresh memories must be at the top
    assert "mem-fresh-today" in ranked_ids
    assert "mem-jobs-tomorrow" in ranked_ids
