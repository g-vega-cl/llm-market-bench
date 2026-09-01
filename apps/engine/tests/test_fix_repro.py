"""Repro tests for ingestion & consensus pipeline fixes (2026-09-01 audit)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core import config


def test_momentum_merge_threshold_is_085():
    """MOMENTUM_CONCEPT_MERGE_THRESHOLD must be 0.85 to avoid false merges (FTC Amazon->Hims 0.80)."""
    assert config.MOMENTUM_CONCEPT_MERGE_THRESHOLD == 0.85
    # Velocity threshold stays 0.75 (counts are permissive)
    assert config.MOMENTUM_SIMILARITY_THRESHOLD == 0.75


def test_momentum_merge_080_does_not_merge(mock_supabase=None):
    """Sim 0.80 should NOT merge after fix (previously merged at 0.75)."""
    from unittest.mock import MagicMock

    from analysis.momentum import update_concept_metrics

    client = MagicMock()
    # RPC match_concepts returns no data when threshold 0.85 and sim 0.80 – mocked as empty
    match_empty = MagicMock()
    match_empty.data = []
    client.rpc.return_value.execute.return_value = match_empty
    # Also mock table insert/update
    table_mock = MagicMock()
    client.table.return_value = table_mock
    insert_mock = MagicMock()
    table_mock.insert.return_value = insert_mock
    insert_mock.execute.return_value = MagicMock(data=[{"id": "new"}])

    # Patch config threshold check via rpc call inspection
    with patch.object(config, "MOMENTUM_CONCEPT_MERGE_THRESHOLD", 0.85):
        update_concept_metrics(client, "FTC Amazon Ad-Auction", [0.1] * 768, 1.0)
        # Assert rpc called with threshold 0.85 (not 0.75)
        assert client.rpc.called
        # rpc("match_concepts", {threshold: ...})
        args, kwargs = client.rpc.call_args
        assert args[1]["match_threshold"] == 0.85
        # Should have inserted, not updated (no merge)
        table_mock.insert.assert_called_once()


def test_momentum_dead_rpc_removed():
    """_get_90d_mentions should not be called inside update_concept_metrics."""
    # Inspect source: no call to _get_90d_mentions
    import inspect

    import analysis.momentum as m

    src = inspect.getsource(m.update_concept_metrics)
    assert "_get_90d_mentions" not in src, "dead RPC still present"


def test_embeddings_throttle_and_retry():
    """Embeddings must throttle and retry 4x with longer backoff."""
    import memory.embeddings as emb

    assert hasattr(emb, "_EMBED_MIN_INTERVAL")
    assert emb._EMBED_MIN_INTERVAL == 1.2
    # Check retry decorator: stop_after_attempt 4, max 30
    assert emb._call_embed_with_retry.retry.stop.max_attempt_number == 4
    # wait max 30
    assert emb._call_embed_with_retry.retry.wait.max == 30


@pytest.mark.asyncio
async def test_consensus_skips_discovery_on_duplicate():
    """If duplicate found, DiscoveryAgent should not be called."""
    from analysis.consensus import _synthesize_and_promote_group
    from core.models import MacroEvent

    events = [
        MacroEvent(
            event_name="Global Bond Selloff and Fiscal Dominance",
            impact="BEARISH",
            confidence=90,
            reasoning="yields surge",
            source_id="src1",
            model_provider="openai",
            model_name="gpt-4",
        ),
        MacroEvent(
            event_name="Global Bond Selloff and Fiscal Dominance",
            impact="BEARISH",
            confidence=85,
            reasoning="fiscal dominance",
            source_id="src1",
            model_provider="anthropic",
            model_name="claude-3",
        ),
    ]

    with (
        patch("analysis.consensus.synthesize_event", new_callable=AsyncMock) as mock_synth,
        patch("analysis.consensus.get_embedding", return_value=[0.1] * 768),
        patch("analysis.consensus.find_similar_memory", return_value="dup-id"),
        patch("analysis.consensus.find_potential_ancestors", return_value=[]),
        patch("analysis.consensus.analyze_event_relationship", new_callable=AsyncMock) as mock_rel,
        patch("analysis.consensus.add_memory", return_value="dup-id") as mock_add,
        patch("analysis.consensus.DiscoveryService") as mock_disc_cls,
    ):
        mock_synth.return_value = {
            "name": "Global Bond Selloff and Fiscal Dominance",
            "summary": "yields surge fiscal dominance",
        }
        mock_rel.return_value = {"parent_id": None, "relationship_type": None, "should_resolve": False}
        mock_disc = MagicMock()
        mock_disc.discover_assets = AsyncMock(return_value=[])
        mock_disc_cls.return_value = mock_disc

        await _synthesize_and_promote_group(events, mock_disc, 0.75)
        # Should skip discovery
        mock_disc.discover_assets.assert_not_called()
        # But still promote (duplicate path reuses embedding)
        assert mock_add.called
        # Reuse embedding should be passed
        assert mock_add.call_args.kwargs.get("embedding") == [0.1] * 768


@pytest.mark.asyncio
async def test_consensus_reuses_embedding():
    """Non-duplicate should pass prelim embedding to add_memory to save quota."""
    from analysis.consensus import _synthesize_and_promote_group
    from core.models import MacroEvent

    events = [
        MacroEvent(
            event_name="New Unique Event XYZ",
            impact="BULLISH",
            confidence=90,
            reasoning="unique",
            source_id="src1",
            model_provider="openai",
            model_name="gpt-4",
        ),
        MacroEvent(
            event_name="New Unique Event XYZ",
            impact="BULLISH",
            confidence=85,
            reasoning="unique2",
            source_id="src1",
            model_provider="anthropic",
            model_name="claude-3",
        ),
    ]

    with (
        patch("analysis.consensus.synthesize_event", new_callable=AsyncMock) as mock_synth,
        patch("analysis.consensus.get_embedding", return_value=[0.2] * 768),
        patch("analysis.consensus.find_similar_memory", return_value=None),
        patch("analysis.consensus.find_potential_ancestors", return_value=[]),
        patch("analysis.consensus.analyze_event_relationship", new_callable=AsyncMock) as mock_rel,
        patch("analysis.consensus.add_memory", return_value="new-id") as mock_add,
        patch("analysis.consensus.DiscoveryService") as mock_disc_cls,
    ):
        mock_synth.return_value = {
            "name": "New Unique Event XYZ",
            "summary": "unique summary",
            "scenarios": [{"cleanHeader": "Scenario A", "outcome": "out", "tradingPlan": "plan", "percentage": "50%"}],
        }
        mock_rel.return_value = {"parent_id": None, "relationship_type": None, "should_resolve": False}
        mock_disc = MagicMock()
        mock_disc.discover_assets = AsyncMock(return_value=[{"ticker": "AAPL", "name": "Apple", "reason": "test"}])
        mock_disc_cls.return_value = mock_disc

        await _synthesize_and_promote_group(events, mock_disc, 0.75)
        # Discovery should happen (not duplicate)
        assert mock_disc.discover_assets.called
        # add_memory should reuse prelim embedding
        assert mock_add.call_args.kwargs.get("embedding") == [0.2] * 768
