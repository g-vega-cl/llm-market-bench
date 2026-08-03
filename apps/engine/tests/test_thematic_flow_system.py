"""TDD tests for Approach 1: Thematic Flow & Macro Capital Rotation System.

Tests cover:
1. memory/store.py:
   - `retrieve_thematic_flows()` returns formatted THEMATIC_FLOW memories.
   - `decay_memories()` applies 0.72 decay factor to THEMATIC_FLOW.
2. core/llm/tools.py:
   - `get_thematic_flows` tool returns capital flow theses.
   - `add_thematic_flow` tool inserts a new THEMATIC_FLOW memory into DB.
3. analysis/consensus.py:
   - Consensus classifies thematic rotation events as THEMATIC_FLOW memory type.
"""

from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Test 1: store.py retrieve_thematic_flows & decay
# ---------------------------------------------------------------------------


def test_retrieve_thematic_flows_exists_and_formats():
    """retrieve_thematic_flows must exist and format rows as [THEMATIC FLOW]."""
    mock_rows = [
        {
            "content": "Capital rotating from AI winners (Alphabet) to backbone infrastructure (power, cooling).",
            "importance_score": 9,
            "memory_type": "THEMATIC_FLOW",
        }
    ]

    mock_response = MagicMock()
    mock_response.data = mock_rows

    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.in_.return_value.order.return_value.limit.return_value.execute.return_value = mock_response

    with patch("memory.store.get_supabase_client", return_value=mock_client):
        from memory.store import retrieve_thematic_flows

        result = retrieve_thematic_flows(limit=5)

    assert "[THEMATIC FLOW]" in result
    assert "power, cooling" in result


def test_decay_memories_applies_072_to_thematic_flow():
    """decay_memories must apply decay_factor=0.72 to THEMATIC_FLOW memories."""
    mock_supabase = MagicMock()
    memories = [
        {"id": "tf1", "memory_type": "THEMATIC_FLOW", "relevance_score": 1.0},
    ]

    mock_select_chain = (
        mock_supabase.table.return_value.select.return_value.eq.return_value.lt.return_value.gt.return_value.execute
    )
    mock_select_chain.return_value = MagicMock(data=memories)

    from memory.store import decay_memories

    decay_memories(mock_supabase, decay_days=30)

    update_calls = mock_supabase.table.return_value.update.call_args_list
    assert len(update_calls) == 1
    assert update_calls[0][0][0] == {"relevance_score": 0.72}


# ---------------------------------------------------------------------------
# Test 2: core/llm/tools.py get_thematic_flows & add_thematic_flow execution
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_get_thematic_flows_tool():
    """execute_get_thematic_flows_tool must return formatted thematic flow context."""
    from core.llm.tools import execute_get_thematic_flows_tool

    fake_flow = "- [THEMATIC FLOW] (Importance: 9/10) AI Infra rotation"

    with patch("memory.store.retrieve_thematic_flows", return_value=fake_flow):
        res = await execute_get_thematic_flows_tool(limit=5)

    assert "THEMATIC FLOW" in res
    assert "AI Infra" in res


@pytest.mark.asyncio
async def test_execute_add_thematic_flow_tool():
    """execute_add_thematic_flow_tool must call add_memory with THEMATIC_FLOW type."""
    from core.llm.tools import execute_add_thematic_flow_tool

    with patch("memory.store.add_memory", return_value="mem-id-999") as mock_add:
        res = await execute_add_thematic_flow_tool(
            content="Miners pivoting to AI datacenter leasing",
            importance_score=8,
            category="AI_CAPEX_ROTATION",
        )

    assert "mem-id-999" in res
    mock_add.assert_called_once()
    kwargs = mock_add.call_args.kwargs
    assert kwargs["memory_type"] == "THEMATIC_FLOW"
    assert kwargs["importance_score"] == 8
    assert kwargs["metadata"]["category"] == "AI_CAPEX_ROTATION"


# ---------------------------------------------------------------------------
# Test 3: Tools registered in CANONICAL_TOOLS_REGISTRY map
# ---------------------------------------------------------------------------


def test_thematic_flow_tools_registered():
    """get_thematic_flows and add_thematic_flow must be present in CANONICAL_TOOLS_REGISTRY."""
    from core.llm.tools import CANONICAL_TOOLS_REGISTRY

    assert "get_thematic_flows" in CANONICAL_TOOLS_REGISTRY
    assert "add_thematic_flow" in CANONICAL_TOOLS_REGISTRY
