"""Hermetic test suite for Daily Stock Picker Task (3 Up, 3 Down).

Verifies candidate ticker extraction, pick sanitization, consensus RRF math,
and end-to-end multi-model orchestration with zero live network calls.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.llm.stock_picker_prompts import (
    STOCK_PICKER_CONSTRAINTS_FOOTER,
    STOCK_PICKER_CONSTRAINTS_HEADER,
    STOCK_PICKER_MUTABLE_STRATEGIES,
    StockPickerOutput,
    StockPickItem,
    split_stock_picker_prompt,
)
from tasks.stock_picker import (
    compute_consensus_basket,
    extract_candidate_tickers,
    run_daily_stock_picker,
    sanitize_picks,
)


def test_extract_candidate_tickers_from_briefing():
    text = (
        "Headline catalysts: **NVDA** rallied +4% on Blackwell volume. "
        "Meanwhile (TSM) approved investments in Anthropic. "
        "Also watching **ETR** and **ABNB** into CPI. (SPY) and (QQQ) are choppy."
    )
    candidates = extract_candidate_tickers(text)

    # Should include specific equities, but filter out broad index proxies and macro acronyms
    assert "NVDA" in candidates
    assert "TSM" in candidates
    assert "ETR" in candidates
    assert "ABNB" in candidates
    assert "CPI" not in candidates
    assert "SPY" not in candidates
    assert "QQQ" not in candidates


def test_extract_candidate_tickers_empty_fallback():
    candidates = extract_candidate_tickers("")
    assert len(candidates) >= 10
    assert "AAPL" in candidates
    assert "MSFT" in candidates


def test_sanitize_picks_enforces_exact_three_unique():
    candidate_pool = ["AAPL", "MSFT", "GOOGL", "AMZN", "META"]
    raw_picks = [
        StockPickItem(ticker="AAPL", direction="UP", rank=1, confidence=75.0, reasoning="Strong cash flow."),
        StockPickItem(ticker="AAPL", direction="UP", rank=2, confidence=70.0, reasoning="Duplicate ticker."),
        StockPickItem(ticker="INVALID", direction="UP", rank=3, confidence=65.0, reasoning="Not in candidate pool."),
    ]

    cleaned = sanitize_picks(raw_picks, "UP", candidate_pool)
    assert len(cleaned) == 3
    assert [p.rank for p in cleaned] == [1, 2, 3]

    tickers = [p.ticker for p in cleaned]
    assert len(set(tickers)) == 3
    assert tickers[0] == "AAPL"
    # Backfilled from candidate pool
    assert tickers[1] in candidate_pool
    assert tickers[2] in candidate_pool


def test_compute_consensus_basket_rrf_and_leg_exclusivity():
    candidate_pool = ["NVDA", "TSM", "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA"]

    # Model 1 picks
    m1_output = StockPickerOutput(
        picks_up=[
            StockPickItem(ticker="NVDA", direction="UP", rank=1, confidence=80.0, reasoning="AI infrastructure leader"),
            StockPickItem(ticker="TSM", direction="UP", rank=2, confidence=75.0, reasoning="Foundry strength and moat"),
            StockPickItem(
                ticker="AAPL", direction="UP", rank=3, confidence=70.0, reasoning="Services ecosystem growth"
            ),
        ],
        picks_down=[
            StockPickItem(
                ticker="GOOGL", direction="DOWN", rank=1, confidence=75.0, reasoning="Ad revenue margin weakness"
            ),
            StockPickItem(ticker="AMZN", direction="DOWN", rank=2, confidence=70.0, reasoning="Capex spending drag"),
            StockPickItem(
                ticker="META", direction="DOWN", rank=3, confidence=65.0, reasoning="High valuation multiple"
            ),
        ],
        market_regime_rationale="Model 1 view",
    )

    # Model 2 picks with a conflict: picks TSM as DOWN rank 3, but Model 1 picked TSM as UP rank 2
    m2_output = StockPickerOutput(
        picks_up=[
            StockPickItem(ticker="NVDA", direction="UP", rank=1, confidence=85.0, reasoning="Blackwell ramp"),
            StockPickItem(ticker="MSFT", direction="UP", rank=2, confidence=72.0, reasoning="Cloud demand"),
            StockPickItem(
                ticker="AAPL",
                direction="UP",
                rank=3,
                confidence=68.0,
                reasoning="Broad services and hardware ecosystem",
            ),
        ],
        picks_down=[
            StockPickItem(ticker="GOOGL", direction="DOWN", rank=1, confidence=80.0, reasoning="Search pressure"),
            StockPickItem(ticker="TSLA", direction="DOWN", rank=2, confidence=75.0, reasoning="Margin drop"),
            StockPickItem(ticker="TSM", direction="DOWN", rank=3, confidence=55.0, reasoning="Conflicting short"),
        ],
        market_regime_rationale="Model 2 view",
    )

    model_outputs = {"model-1": m1_output, "model-2": m2_output}
    consensus = compute_consensus_basket(model_outputs, candidate_pool)

    assert len(consensus.picks_up) == 3
    assert len(consensus.picks_down) == 3

    up_tickers = [p.ticker for p in consensus.picks_up]
    down_tickers = [p.ticker for p in consensus.picks_down]

    # NVDA unanimously ranked #1 UP
    assert up_tickers[0] == "NVDA"
    # GOOGL unanimously ranked #1 DOWN
    assert down_tickers[0] == "GOOGL"

    # Leg exclusivity: TSM had higher score in UP than DOWN, so must be in UP or neither, NEVER in DOWN
    assert "TSM" not in down_tickers

    # Disjoint check: No ticker may appear in both legs
    assert set(up_tickers).isdisjoint(set(down_tickers))


def test_split_stock_picker_prompt():
    prompt = STOCK_PICKER_CONSTRAINTS_HEADER + STOCK_PICKER_MUTABLE_STRATEGIES + STOCK_PICKER_CONSTRAINTS_FOOTER
    header, mutable, footer = split_stock_picker_prompt(prompt)

    assert "You are an elite quantitative equity analyst" in header
    assert "=== LONG/SHORT RELATIVE SELECTION STRATEGY ===" in mutable
    assert "=== REQUIRED OUTPUT FORMAT ===" in footer


@pytest.mark.asyncio
async def test_run_daily_stock_picker_orchestration():
    mock_supabase = MagicMock()

    # Mock no existing basket
    mock_supabase.table().select().eq().eq().execute.return_value = MagicMock(data=[])

    # Mock morning newsletter
    mock_supabase.table().select().order().limit().execute.return_value = MagicMock(
        data=[{"content": "Morning briefing: **NVDA** and **TSM** look strong. Watch **ABNB** down."}]
    )

    # Mock upsert basket & picks
    mock_supabase.table().upsert().execute.return_value = MagicMock(data=[{"id": "b-123"}])

    mock_output = StockPickerOutput(
        picks_up=[
            StockPickItem(ticker="NVDA", direction="UP", rank=1, confidence=75.0, reasoning="AI compute leader"),
            StockPickItem(ticker="TSM", direction="UP", rank=2, confidence=72.0, reasoning="Foundry moat"),
            StockPickItem(ticker="AAPL", direction="UP", rank=3, confidence=68.0, reasoning="Services growth"),
        ],
        picks_down=[
            StockPickItem(ticker="ABNB", direction="DOWN", rank=1, confidence=74.0, reasoning="Credit slowdown"),
            StockPickItem(ticker="GOOGL", direction="DOWN", rank=2, confidence=70.0, reasoning="Multiple compression"),
            StockPickItem(
                ticker="META", direction="DOWN", rank=3, confidence=65.0, reasoning="Ad cycle margin compression"
            ),
        ],
        market_regime_rationale="Simulated bullish dispersion.",
    )

    with (
        patch("tasks.stock_picker.get_supabase_client", return_value=mock_supabase),
        patch("tasks.stock_picker.fetch_active_prompt", new_callable=AsyncMock) as mock_prompt,
        patch("tasks.stock_picker.execute_model_picker", new_callable=AsyncMock) as mock_exec,
    ):
        mock_prompt.return_value = ("active-tag", "prompt content")
        mock_exec.return_value = mock_output

        result = await run_daily_stock_picker(target_date="2026-11-12", force=True)

        assert result["status"] == "success"
        assert result["target_date"] == "2026-11-12"
        assert result["consensus_basket_id"] == "b-123"
        assert len(result["models_run"]) == 3
