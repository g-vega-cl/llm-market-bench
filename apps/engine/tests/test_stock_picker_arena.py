"""Hermetic tests for the Daily Stock Picker Arena.

Pins the provider/client contract, the atomic pick replacement and the
append-only guard for graded sessions. No network, no sleeps.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.llm.stock_picker_prompts import StockPickerOutput, StockPickItem
from tasks import stock_picker as arena

CANDIDATES = ["NVDA", "MSFT", "AMZN", "TSLA", "AVGO", "JPM"]


def _output() -> StockPickerOutput:
    up = [
        StockPickItem(
            ticker=ticker,
            direction="UP",
            rank=rank,
            confidence=70.0,
            expected_return_pct=1.2,
            reasoning=f"Relative strength thesis for {ticker} today.",
        )
        for rank, ticker in enumerate(CANDIDATES[:3], start=1)
    ]
    down = [
        StockPickItem(
            ticker=ticker,
            direction="DOWN",
            rank=rank,
            confidence=65.0,
            expected_return_pct=-1.2,
            reasoning=f"Relative weakness thesis for {ticker} today.",
        )
        for rank, ticker in enumerate(CANDIDATES[3:], start=1)
    ]
    return StockPickerOutput(
        picks_up=up,
        picks_down=down,
        market_regime_rationale="Neutral tape with rotation into AI infrastructure.",
    )


def _mock_client() -> MagicMock:
    client = MagicMock()
    client.chat.completions.create = AsyncMock(return_value=_output())
    return client


@pytest.mark.asyncio
async def test_minimax_track_uses_shared_extraction_args():
    """Anthropic-format endpoint needs max_tokens + a hoisted system message."""
    minimax_client = _mock_client()
    close_mock = AsyncMock()

    with (
        patch.object(arena, "fetch_active_prompt", AsyncMock(return_value=("baseline", "prompt"))),
        patch.object(arena, "get_minimax_client", return_value=minimax_client),
        patch.object(arena, "close_client", close_mock),
    ):
        result = await arena.execute_model_picker({"name": "MiniMax-M3", "provider": "minimax"}, CANDIDATES, "briefing")

    assert len(result.picks_up) == 3
    create_kwargs = minimax_client.chat.completions.create.await_args.kwargs
    assert create_kwargs["model"] == "MiniMax-M3"
    assert create_kwargs["max_tokens"] == 32000
    assert create_kwargs["system"] == "prompt"
    assert [m["role"] for m in create_kwargs["messages"]] == ["user"]
    close_mock.assert_awaited_once_with(minimax_client, "minimax")


@pytest.mark.asyncio
async def test_openai_track_uses_json_mode_client_with_extraction_effort():
    """gpt-5.6-luna rejects tool-based extraction and non-default temperature."""
    openai_client = _mock_client()
    close_mock = AsyncMock()

    with (
        patch.object(arena, "fetch_active_prompt", AsyncMock(return_value=("baseline", "prompt"))),
        patch.object(arena, "get_openai_json_client", return_value=openai_client),
        patch.object(arena, "close_client", close_mock),
    ):
        result = await arena.execute_model_picker(
            {"name": "gpt-5.6-luna", "provider": "openai"}, CANDIDATES, "briefing"
        )

    assert len(result.picks_down) == 3
    create_kwargs = openai_client.chat.completions.create.await_args.kwargs
    assert create_kwargs["model"] == "gpt-5.6-luna"
    assert create_kwargs["response_model"] is StockPickerOutput
    assert create_kwargs["reasoning_effort"] == "none"
    assert "temperature" not in create_kwargs
    close_mock.assert_awaited_once_with(openai_client, "openai")


@pytest.mark.asyncio
async def test_deepseek_track_closes_client_with_provider():
    ds_client = _mock_client()
    close_mock = AsyncMock()

    with (
        patch.object(arena, "fetch_active_prompt", AsyncMock(return_value=("baseline", "prompt"))),
        patch.object(arena, "get_deepseek_client", return_value=ds_client),
        patch.object(arena, "close_client", close_mock),
    ):
        result = await arena.execute_model_picker(
            {"name": "deepseek-v4-flash", "provider": "deepseek"}, CANDIDATES, "briefing"
        )

    assert len(result.picks_up) == 3
    assert "temperature" not in ds_client.chat.completions.create.await_args.kwargs
    close_mock.assert_awaited_once_with(ds_client, "deepseek")


@pytest.mark.asyncio
async def test_unknown_provider_raises_instead_of_falling_back():
    with (
        patch.object(arena, "fetch_active_prompt", AsyncMock(return_value=("baseline", "prompt"))),
        pytest.raises(ValueError, match="Unsupported stock picker provider"),
    ):
        await arena.execute_model_picker({"name": "mystery-model", "provider": "mystery"}, CANDIDATES, "briefing")


@pytest.mark.asyncio
async def test_client_is_closed_even_when_inference_fails():
    ds_client = _mock_client()
    ds_client.chat.completions.create = AsyncMock(side_effect=RuntimeError("upstream 500"))
    close_mock = AsyncMock()

    with (
        patch.object(arena, "fetch_active_prompt", AsyncMock(return_value=("baseline", "prompt"))),
        patch.object(arena, "get_deepseek_client", return_value=ds_client),
        patch.object(arena, "close_client", close_mock),
    ):
        with pytest.raises(RuntimeError, match="upstream 500"):
            await arena.execute_model_picker(
                {"name": "deepseek-v4-flash", "provider": "deepseek"}, CANDIDATES, "briefing"
            )

    close_mock.assert_awaited_once_with(ds_client, "deepseek")


def _supabase_for_persist(basket_id: str = "basket-1") -> MagicMock:
    table_mock = MagicMock()
    table_mock.upsert.return_value.execute.return_value = MagicMock(data=[{"id": basket_id}])
    supabase_mock = MagicMock()
    supabase_mock.table.return_value = table_mock
    return supabase_mock


@pytest.mark.asyncio
async def test_persist_replaces_picks_atomically_via_rpc():
    """Delete + insert must be one DB transaction, not two round-trips."""
    supabase_mock = _supabase_for_persist()

    with patch.object(arena, "get_supabase_client", return_value=supabase_mock):
        basket_id = await arena.persist_stock_basket("2026-11-13", "consensus", _output())

    assert basket_id == "basket-1"
    supabase_mock.rpc.assert_called_once()
    rpc_name, rpc_args = supabase_mock.rpc.call_args.args
    assert rpc_name == "replace_daily_stock_picks"
    assert rpc_args["p_basket_id"] == "basket-1"
    assert len(rpc_args["p_picks"]) == 6
    assert {p["ticker"] for p in rpc_args["p_picks"]} == set(CANDIDATES)
    assert all(p["basket_id"] == "basket-1" for p in rpc_args["p_picks"])
    # No second write path may exist outside the transaction.
    assert not supabase_mock.table.return_value.delete.called


@pytest.mark.asyncio
async def test_persist_resets_basket_metrics_when_rerunning():
    """A 'pending' basket must never keep stale graded metrics."""
    supabase_mock = _supabase_for_persist()

    with patch.object(arena, "get_supabase_client", return_value=supabase_mock):
        await arena.persist_stock_basket("2026-11-13", "consensus", _output())

    (table_name,) = supabase_mock.table.call_args.args
    assert table_name == "daily_stock_baskets"
    basket_row = supabase_mock.table.return_value.upsert.call_args.args[0]
    assert basket_row["status"] == "pending"
    for metric in (
        "directional_hit_rate",
        "mean_long_return_pct",
        "mean_short_return_pct",
        "ls_spread_alpha_pct",
        "excess_alpha_vs_spy_pct",
        "benchmark_spy_return_pct",
        "evaluated_at",
    ):
        assert basket_row[metric] is None, metric


def test_session_skip_reason_allows_empty_dates():
    assert arena.session_skip_reason([], force=False) is None
    assert arena.session_skip_reason([], force=True) is None


def test_session_skip_reason_skips_existing_consensus_without_force():
    rows = [{"model_name": "consensus", "status": "pending"}]
    assert arena.session_skip_reason(rows, force=False) == "already-exists"
    assert arena.session_skip_reason(rows, force=True) is None


def test_session_skip_reason_protects_evaluated_sessions_even_with_force():
    rows = [
        {"model_name": "consensus", "status": "evaluated"},
        {"model_name": "gpt-5.6-luna", "status": "evaluated"},
    ]
    assert arena.session_skip_reason(rows, force=True) == "already-evaluated"
    assert arena.session_skip_reason(rows, force=False) == "already-evaluated"
