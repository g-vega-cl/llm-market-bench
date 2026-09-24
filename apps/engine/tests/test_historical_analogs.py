"""Tests for Historical Market Analog research engine and tool integration."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from analysis.historical_analogs import (
    AssetReturnTape,
    HistoricalAnalogReport,
    HistoricalPrecedentCandidate,
    PlaybookSynthesis,
    fetch_empirical_market_tape,
    format_analog_markdown,
    identify_historical_precedent,
    persist_analog_memory,
    research_historical_market_analog,
    synthesize_analog_playbook,
)


@pytest.mark.asyncio
async def test_identify_historical_precedent_calls_instructor_with_thinking():
    """Verify identify_historical_precedent invokes OpenAI gpt-5.6-luna with reasoning_effort='medium'."""
    mock_client = MagicMock()
    fake_precedent = HistoricalPrecedentCandidate(
        title="August 2024 Yen Carry Trade Unwind",
        start_date="2024-08-01",
        end_date="2024-08-15",
        trigger_description="Bank of Japan rate hike triggered sudden liquidation of leveraged yen-carry positions.",
        macro_backdrop="Global central banks diverging as BoJ hiked while Fed signaled September cut.",
        relevance_score=0.95,
    )

    mock_client.chat.completions.create = AsyncMock(return_value=fake_precedent)

    result = await identify_historical_precedent(
        situation="Japan stocks plunging as yen strengthens sharply",
        client=mock_client,
        model="gpt-5.6-luna",
    )

    assert result.title == "August 2024 Yen Carry Trade Unwind"
    assert result.start_date == "2024-08-01"
    assert result.end_date == "2024-08-15"
    assert result.relevance_score == 0.95

    # Check that reasoning_effort was passed as 'medium'
    call_kwargs = mock_client.chat.completions.create.call_args[1]
    assert call_kwargs.get("reasoning_effort") == "medium"
    assert call_kwargs.get("response_model") == HistoricalPrecedentCandidate


@pytest.mark.asyncio
async def test_fetch_empirical_market_tape_calculates_returns():
    """Verify fetch_empirical_market_tape pulls price history and computes percent returns hermetically."""
    mock_mdm = MagicMock()

    # Mock historical price rows for TLT and SPY
    def mock_get_history(ticker, days=14, force_refresh=False):
        if ticker == "TLT":
            return [
                {"price": 95.0, "fetched_at": "2024-08-15"},
                {"price": 93.0, "fetched_at": "2024-08-08"},
                {"price": 90.0, "fetched_at": "2024-08-01"},
            ]
        if ticker == "SPY":
            return [
                {"price": 530.0, "fetched_at": "2024-08-15"},
                {"price": 510.0, "fetched_at": "2024-08-08"},
                {"price": 550.0, "fetched_at": "2024-08-01"},
            ]
        return [
            {"price": 100.0, "fetched_at": "2024-08-15"},
            {"price": 100.0, "fetched_at": "2024-08-01"},
        ]

    mock_mdm.get_history = AsyncMock(side_effect=mock_get_history)

    tape = await fetch_empirical_market_tape(
        start_date="2024-08-01",
        end_date="2024-08-15",
        focus_assets=["EWJ"],
        market_data_manager=mock_mdm,
    )

    assert len(tape) >= 2
    tape_dict = {t.ticker: t for t in tape}

    assert "TLT" in tape_dict
    assert "SPY" in tape_dict
    # TLT went from 90 to 95 -> +5.56%
    assert tape_dict["TLT"].start_price == 90.0
    assert tape_dict["TLT"].end_price == 95.0
    assert tape_dict["TLT"].return_pct == pytest.approx(5.56, abs=0.1)
    assert tape_dict["TLT"].reaction_status == "GAINED"

    # SPY went from 550 to 530 -> -3.64%
    assert tape_dict["SPY"].start_price == 550.0
    assert tape_dict["SPY"].end_price == 530.0
    assert tape_dict["SPY"].return_pct == pytest.approx(-3.64, abs=0.1)
    assert tape_dict["SPY"].reaction_status == "DROPPED"


@pytest.mark.asyncio
async def test_synthesize_analog_playbook_calls_instructor_with_thinking():
    """Verify synthesize_analog_playbook invokes OpenAI with thinking and returns structured playbook."""
    mock_client = MagicMock()
    fake_playbook = PlaybookSynthesis(
        summary_takeaway="Carry unwind shock creates steep 72-hour liquidity drawdown followed by aggressive dip buying.",
        key_divergences_today=[
            "Fed is currently cutting rates rather than holding at terminal highs.",
            "Valuations are 10% richer than in August 2024.",
        ],
        long_expression="Long TLT and GLD on Day 1; buy beaten-down high-beta tech on Day 4.",
        hedge_fade_expression="Fade high-volatility energy and short short-duration volatility ETF spikes.",
        falsification_trigger="If 10Y yield breaches 4.50% resistance, abort duration longs.",
        predicted_outcome="Expect VIX compression within 10 trading days and recovery in equities.",
    )

    mock_client.chat.completions.create = AsyncMock(return_value=fake_playbook)

    precedent = HistoricalPrecedentCandidate(
        title="August 2024 Yen Carry Trade Unwind",
        start_date="2024-08-01",
        end_date="2024-08-15",
        trigger_description="BoJ rate hike forced cross-currency liquidation.",
        macro_backdrop="Monetary divergence.",
        relevance_score=0.9,
    )
    tape = [
        AssetReturnTape(
            ticker="TLT",
            asset_class="20+Y Treasury",
            start_price=90.0,
            end_price=95.0,
            return_pct=5.56,
            reaction_status="GAINED",
        )
    ]

    playbook = await synthesize_analog_playbook(
        situation="Japan stocks plunging as yen strengthens sharply",
        precedent=precedent,
        tape=tape,
        horizon="1m",
        client=mock_client,
        model="gpt-5.6-luna",
    )

    assert playbook.summary_takeaway.startswith("Carry unwind shock")
    assert len(playbook.key_divergences_today) == 2
    assert "TLT" in playbook.long_expression

    call_kwargs = mock_client.chat.completions.create.call_args[1]
    assert call_kwargs.get("reasoning_effort") == "medium"
    assert call_kwargs.get("response_model") == PlaybookSynthesis


def test_format_analog_markdown_renders_clean_tokens():
    """Verify format_analog_markdown renders dense, unbloated markdown without ANSI codes."""
    precedent = HistoricalPrecedentCandidate(
        title="August 2024 Yen Carry Trade Unwind",
        start_date="2024-08-01",
        end_date="2024-08-15",
        trigger_description="BoJ rate hike forced liquidation.",
        macro_backdrop="Monetary divergence.",
        relevance_score=0.92,
    )
    tape = [
        AssetReturnTape(
            ticker="TLT",
            asset_class="Fixed Income",
            start_price=90.0,
            end_price=95.0,
            return_pct=5.56,
            reaction_status="GAINED",
        ),
        AssetReturnTape(
            ticker="SPY",
            asset_class="Equities",
            start_price=550.0,
            end_price=530.0,
            return_pct=-3.64,
            reaction_status="DROPPED",
        ),
    ]
    playbook = PlaybookSynthesis(
        summary_takeaway="Liquidity shock followed by quick mean reversion.",
        key_divergences_today=["Fed is cutting rates now."],
        long_expression="Long TLT; buy equity dips after 3 days.",
        hedge_fade_expression="Fade spikes in VIX futures.",
        falsification_trigger="Yields break higher.",
        predicted_outcome="Equities rebound within 2 weeks.",
    )

    md = format_analog_markdown(
        situation="Japan stocks tumbling as yen surges",
        precedent=precedent,
        tape=tape,
        playbook=playbook,
    )

    assert "\x1b[" not in md  # Zero ANSI escapes
    assert "### Historical Analog: August 2024 Yen Carry Trade Unwind" in md
    assert "| TLT | Fixed Income | $90.00 | $95.00 | +5.56% | GAINED |" in md
    assert "| SPY | Equities | $550.00 | $530.00 | -3.64% | DROPPED |" in md
    assert "Fed is cutting rates now." in md
    assert "Long TLT" in md


@pytest.mark.asyncio
async def test_persist_analog_memory_stores_row_in_supabase():
    """Verify persist_analog_memory inserts a record with memory_type='HISTORICAL_ANALOG'."""
    mock_sb = MagicMock()
    mock_chain = MagicMock()
    mock_chain.insert.return_value = mock_chain
    mock_chain.execute.return_value = MagicMock(data=[{"id": "mem-123"}])
    mock_sb.table.return_value = mock_chain

    precedent = HistoricalPrecedentCandidate(
        title="2023 SVB Regional Banking Panic",
        start_date="2023-03-08",
        end_date="2023-03-24",
        trigger_description="Deposit run on Silicon Valley Bank sparked systemic fears.",
        macro_backdrop="Rapid Fed tightening cycle.",
        relevance_score=0.88,
    )
    tape = []
    playbook = PlaybookSynthesis(
        summary_takeaway="Flight to Treasuries and mega-cap tech as regional banks plummeted.",
        key_divergences_today=[],
        long_expression="Long QQQ and TLT",
        hedge_fade_expression="Short KRE",
        falsification_trigger="Discount window usage spikes",
        predicted_outcome="Flight to fortress balance sheets",
    )
    report = HistoricalAnalogReport(
        situation="Banking distress emerging in mid-sized lenders",
        precedent=precedent,
        empirical_tape=tape,
        playbook=playbook,
        markdown_report="Report content",
    )

    with patch("analysis.historical_analogs.generate_embedding", new_callable=AsyncMock) as mock_embed:
        mock_embed.return_value = [0.01] * 768
        memory_id = await persist_analog_memory(report, sb_client=mock_sb)

    assert memory_id == "mem-123"
    assert mock_sb.table.called
    table_name = mock_sb.table.call_args[0][0]
    assert table_name == "memories"

    insert_payload = mock_chain.insert.call_args[0][0]
    assert insert_payload["memory_type"] == "HISTORICAL_ANALOG"
    assert insert_payload["importance_score"] == 8
    assert "2023 SVB Regional Banking Panic" in insert_payload["content"]


@pytest.mark.asyncio
async def test_research_historical_market_analog_full_flow():
    """Verify research_historical_market_analog coordinates the complete pipeline end-to-end."""
    fake_precedent = HistoricalPrecedentCandidate(
        title="October 2023 5% 10-Year Yield Peak",
        start_date="2023-10-01",
        end_date="2023-10-31",
        trigger_description="10-Year Treasury yields touched 5.0%, hammering equities and gold.",
        macro_backdrop="Higher for longer narrative.",
        relevance_score=0.91,
    )
    fake_playbook = PlaybookSynthesis(
        summary_takeaway="Yield exhaustion preceded one of the strongest multi-month rallies in SPY and TLT.",
        key_divergences_today=["Inflation is now decelerating toward target."],
        long_expression="Long TLT and long SPY call spreads.",
        hedge_fade_expression="Fade dollar strength.",
        falsification_trigger="Yields push cleanly past 5.25%.",
        predicted_outcome="Violent short-covering rally across duration assets.",
    )

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(side_effect=[fake_precedent, fake_playbook])

    mock_mdm = MagicMock()
    mock_mdm.get_history = AsyncMock(
        return_value=[
            {"price": 88.0, "fetched_at": "2023-10-31"},
            {"price": 84.0, "fetched_at": "2023-10-01"},
        ]
    )

    mock_sb = MagicMock()
    mock_chain = MagicMock()
    mock_chain.insert.return_value = mock_chain
    mock_chain.execute.return_value = MagicMock(data=[{"id": "mem-456"}])
    mock_sb.table.return_value = mock_chain

    with (
        patch("analysis.historical_analogs.get_openai_client", return_value=mock_client),
        patch("analysis.historical_analogs.get_market_data_manager", return_value=mock_mdm),
        patch("analysis.historical_analogs.get_supabase_client", return_value=mock_sb),
        patch("analysis.historical_analogs.generate_embedding", new_callable=AsyncMock, return_value=[0.1] * 768),
    ):
        result_md = await research_historical_market_analog(
            situation="10-year Treasury yields spiking to new cycle highs",
            focus_assets=["TLT"],
            horizon="1m",
        )

    assert "Historical Analog: October 2023 5% 10-Year Yield Peak" in result_md
    assert "Actionable Profit Playbook" in result_md
    assert "Empirical Cross-Asset Reaction Tape" in result_md


@pytest.mark.asyncio
async def test_execute_research_historical_market_analog_tool_wrapper():
    """Verify core.llm.tools.execute_research_historical_market_analog_tool delegates properly."""
    from core.llm.tools import execute_research_historical_market_analog_tool

    with patch(
        "analysis.historical_analogs.research_historical_market_analog",
        new_callable=AsyncMock,
        return_value="Mocked report",
    ) as mock_research:
        res = await execute_research_historical_market_analog_tool(
            situation="Gold surging past 3000",
            focus_assets=["GLD"],
            horizon="1m",
            model_name="gpt-5.6-luna",
        )

        assert res == "Mocked report"
        mock_research.assert_awaited_once_with(
            situation="Gold surging past 3000",
            focus_assets=["GLD"],
            horizon="1m",
            model_name="gpt-5.6-luna",
        )


@pytest.mark.asyncio
async def test_handler_dispatch_research_historical_market_analog():
    """Verify execute_tool in handlers/base.py dispatches to execute_research_historical_market_analog_tool."""
    from core.llm.handlers.base import execute_tool

    with patch(
        "core.llm.tools.execute_research_historical_market_analog_tool",
        new_callable=AsyncMock,
        return_value="Dispatched markdown",
    ) as mock_tool:
        res = await execute_tool(
            "research_historical_market_analog",
            {"situation": "Bitcoin breaking 100k", "focus_assets": ["BTCUSD"], "horizon": "1w"},
            model_name="gpt-5.6-luna",
        )

        assert res == "Dispatched markdown"
        mock_tool.assert_awaited_once_with(
            situation="Bitcoin breaking 100k",
            focus_assets=["BTCUSD"],
            horizon="1w",
            model_name="gpt-5.6-luna",
        )


@pytest.mark.asyncio
async def test_research_historical_market_analog_empty_situation():
    """Verify research_historical_market_analog returns an error string when situation is empty."""
    res = await research_historical_market_analog(situation="")
    assert "Error: No market situation" in res


def test_main_cli_analog_command_parsed():
    """Verify main.py CLI correctly parses the 'analog' command with options."""
    import sys
    from unittest.mock import patch

    import main

    test_args = ["main.py", "analog", "--situation", "Bond prices surging", "--assets", "TLT,IEF", "--horizon", "3m"]
    with (
        patch.object(sys, "argv", test_args),
        patch("analysis.historical_analogs.research_historical_market_analog", new_callable=AsyncMock) as mock_run,
    ):
        mock_run.return_value = "CLI Analog Output"
        with patch("builtins.print") as mock_print:
            main.main()
            mock_print.assert_called_with("CLI Analog Output")
            mock_run.assert_awaited_once_with(
                situation="Bond prices surging",
                focus_assets=["TLT", "IEF"],
                horizon="3m",
            )
