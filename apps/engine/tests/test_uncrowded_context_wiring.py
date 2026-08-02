"""Reproduction test for uncrowded_context dead-code bug.

The `uncrowded_context` variable in `analyze_trading_decisions` was always set
to "" and never populated, despite:
  - `UNCROWDED_TRADE` memories existing in the DB with no-decay protection
  - The prompt template having a `{uncrowded_context}` injection slot
  - `verification.py` accepting and forwarding the value

This test verifies that:
1. `retrieve_uncrowded_trades()` exists in memory.store and returns a
   formatted string of UNCROWDED_TRADE memories.
2. `analyze_trading_decisions` returns a non-empty uncrowded_context when
   UNCROWDED_TRADE memories are present in the DB.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Test 1: retrieve_uncrowded_trades is importable and returns formatted output
# ---------------------------------------------------------------------------


def test_retrieve_uncrowded_trades_exists():
    """retrieve_uncrowded_trades must exist in memory.store (was missing)."""
    from memory.store import retrieve_uncrowded_trades  # noqa: F401 — import IS the assertion


def test_retrieve_uncrowded_trades_formats_results():
    """retrieve_uncrowded_trades must format rows as [THEMATIC FLOW] prefixed lines."""
    mock_rows = [
        {
            "content": "AI infrastructure players outperform direct AI plays when the primary narrative peaks. "
            "Rotate to picks-and-shovels: power utilities, cooling, datacenter REITs.",
            "importance_score": 9,
            "memory_type": "UNCROWDED_TRADE",
        },
        {
            "content": "Crypto miners pivoting to AI datacenter leasing are an adjacent trade on AI capex.",
            "importance_score": 8,
            "memory_type": "UNCROWDED_TRADE",
        },
    ]

    mock_response = MagicMock()
    mock_response.data = mock_rows

    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.in_.return_value.order.return_value.limit.return_value.execute.return_value = (
        mock_response
    )

    with patch("memory.store.get_supabase_client", return_value=mock_client):
        from memory.store import retrieve_uncrowded_trades

        result = retrieve_uncrowded_trades(limit=5)

    assert result != "", "Should return non-empty string when UNCROWDED_TRADE rows exist"
    assert "[THEMATIC FLOW]" in result, "Output must be prefixed with [THEMATIC FLOW]"
    assert "AI infrastructure" in result or "Crypto miners" in result


def test_retrieve_uncrowded_trades_returns_empty_on_no_data():
    """retrieve_uncrowded_trades must return '' gracefully when no rows exist."""
    mock_response = MagicMock()
    mock_response.data = []

    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.in_.return_value.order.return_value.limit.return_value.execute.return_value = (
        mock_response
    )

    with patch("memory.store.get_supabase_client", return_value=mock_client):
        from memory.store import retrieve_uncrowded_trades

        result = retrieve_uncrowded_trades(limit=5)

    assert result == ""


def test_retrieve_uncrowded_trades_returns_empty_on_exception():
    """retrieve_uncrowded_trades must return '' gracefully on DB errors."""
    with patch("memory.store.get_supabase_client", side_effect=Exception("DB down")):
        from memory.store import retrieve_uncrowded_trades

        result = retrieve_uncrowded_trades(limit=5)

    assert result == ""


# ---------------------------------------------------------------------------
# Test 2: analyze_trading_decisions wires retrieve_uncrowded_trades
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_analyze_trading_decisions_populates_uncrowded_context():
    """analyze_trading_decisions must call retrieve_uncrowded_trades and return
    its result as the second element of the returned tuple (was always "").
    """
    from analysis.analyze import analyze_trading_decisions

    fake_uncrowded = "[UNCROWDED TRADE] (Importance: 9/10) AI infra rotation thesis"

    # Must pass a valid chunk (with source_id + content) to avoid the early-return guard.
    # We mock everything downstream so no real I/O happens.
    fake_chunk = {"source_id": "test-src-1", "content": "AI rotation article text"}

    with (
        patch("memory.store.get_supabase_client", return_value=MagicMock()),
        patch("analysis.analyze.retrieve_uncrowded_trades", return_value=fake_uncrowded),
        patch("analysis.analyze.retrieve_top_memories", return_value=""),
        patch("analysis.analyze.get_top_trending_concepts", return_value=""),
        patch("analysis.pre_filter.summarize_newsletters", return_value=""),
        patch("analysis.analyze.MODELS", []),  # no model configs → zero tasks, no gather needed
        patch("core.macro_tracker.get_global_macro_context", new=AsyncMock(return_value="")),
        patch("analysis.analyze.MarketDataManager", return_value=AsyncMock(get_quotes=AsyncMock(return_value={}))),
        patch("analysis.analyze.Portfolio"),
    ):
        decisions, uncrowded_context = await analyze_trading_decisions(
            chunks=[fake_chunk], consensus_events=[], sb_client=MagicMock()
        )

    # Before the fix this would be ""; after the fix it must be the mocked value
    assert uncrowded_context == fake_uncrowded, (
        f"uncrowded_context was '{uncrowded_context}' — expected retrieve_uncrowded_trades() result. "
        "This confirms the dead-code bug: the function was never called."
    )
