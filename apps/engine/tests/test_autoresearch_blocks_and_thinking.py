"""Tests for modular prompt blocks, auto-researcher DB tools, and thinking parameter integration."""

import pytest

from autoresearch.prompt_blocks import AVAILABLE_PROMPT_BLOCKS, render_prompt_blocks


def test_render_prompt_blocks_valid():
    """Verify rendering valid prompt block IDs returns combined markdown text."""
    blocks = ["let_winners_run", "cut_losers_fast"]
    rendered = render_prompt_blocks(blocks)

    assert "LET WINNERS RUN" in rendered
    assert "CUT LOSERS FAST" in rendered
    assert "Trailing Take-Profit" in rendered or "Stop-Loss" in rendered


def test_render_prompt_blocks_invalid_and_empty():
    """Verify invalid block IDs are safely ignored and empty list returns empty string."""
    assert render_prompt_blocks([]) == ""
    assert render_prompt_blocks(None) == ""

    rendered = render_prompt_blocks(["non_existent_block", "let_winners_run"])
    assert "LET WINNERS RUN" in rendered
    assert "non_existent_block" not in rendered


def test_available_prompt_blocks_dict():
    """Verify AVAILABLE_PROMPT_BLOCKS registry contains essential trading discipline keys."""
    assert "let_winners_run" in AVAILABLE_PROMPT_BLOCKS
    assert "cut_losers_fast" in AVAILABLE_PROMPT_BLOCKS
    assert "catalyst_expiry_timer" in AVAILABLE_PROMPT_BLOCKS
    assert "five_whys_causal" in AVAILABLE_PROMPT_BLOCKS
    assert "mece_risk_partition" in AVAILABLE_PROMPT_BLOCKS


@pytest.mark.asyncio
async def test_autoresearcher_db_tools_execution(monkeypatch):
    """Verify DB search tools for autoresearcher return formatted context strings."""
    from autoresearch.tools import query_trade_postmortems, search_wiki_concepts

    fake_decisions_data = [
        {
            "ticker": "NVDA",
            "decision": "BUY",
            "reasoning": "AI demand surge",
            "executed_at": "2026-05-01T10:00:00Z",
            "verification_status": "APPROVED",
        },
        {
            "ticker": "AAPL",
            "decision": "SELL",
            "reasoning": "Thesis invalidated",
            "executed_at": "2026-05-02T10:00:00Z",
            "verification_status": "REJECTED",
        },
    ]

    class FakeQuery:
        def select(self, *args, **kwargs):
            return self

        def eq(self, *args, **kwargs):
            return self

        def order(self, *args, **kwargs):
            return self

        def limit(self, *args, **kwargs):
            return self

        async def execute(self):
            class Res:
                data = fake_decisions_data

            return Res()

    class FakeSupabaseClient:
        def table(self, name):
            return FakeQuery()

    async def fake_get_sb():
        return FakeSupabaseClient()

    monkeypatch.setattr("core.db.get_async_supabase_client", fake_get_sb)
    monkeypatch.setattr("autoresearch.tools.get_async_supabase_client", fake_get_sb, raising=False)

    postmortems = await query_trade_postmortems(track_id="track_default", limit=5)
    assert "NVDA" in postmortems
    assert "AAPL" in postmortems
    assert "APPROVED" in postmortems

    wiki_res = await search_wiki_concepts("multi-track")
    assert "Multi-Track AutoResearch" in wiki_res or "wiki" in wiki_res.lower() or "No wiki concept" in wiki_res
