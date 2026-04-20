"""Tests for market_feeling analysis module."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timedelta, timezone
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))


class TestBuildTradesSummary:
    """Tests for build_trades_summary function."""

    def test_empty_trades(self):
        """Test trades summary with no trades."""
        from analysis.market_feeling import build_trades_summary

        result = build_trades_summary([])
        assert result == "No trades executed today."

    def test_single_buy_trade(self):
        """Test trades summary with a single BUY trade."""
        from analysis.market_feeling import build_trades_summary

        trades = [{
            "ticker": "AAPL",
            "signal": "BUY",
            "quantity": 10,
            "total_cost": 1500.00
        }]
        result = build_trades_summary(trades)
        assert "Total trades: 1 (1 buys, 0 sells)" in result
        assert "Total value: $1,500.00" in result
        assert "Buy orders: AAPL" in result

    def test_multiple_trades(self):
        """Test trades summary with multiple buys and sells."""
        from analysis.market_feeling import build_trades_summary

        trades = [
            {"ticker": "AAPL", "signal": "BUY", "quantity": 10, "total_cost": 1500.00},
            {"ticker": "GOOGL", "signal": "BUY", "quantity": 5, "total_cost": 750.00},
            {"ticker": "TSLA", "signal": "SELL", "quantity": 3, "total_cost": 600.00}
        ]
        result = build_trades_summary(trades)
        assert "Total trades: 3 (2 buys, 1 sells)" in result
        assert "Total value: $2,850.00" in result
        assert "Buy orders: AAPL, GOOGL" in result
        assert "Sell orders: TSLA" in result

    def test_trades_truncated_at_five(self):
        """Test that ticker list is truncated at 5."""
        from analysis.market_feeling import build_trades_summary

        trades = [
            {"ticker": f"STOCK{i}", "signal": "BUY", "quantity": 1, "total_cost": 100.00}
            for i in range(8)
        ]
        result = build_trades_summary(trades)
        assert "..." in result  # Should have ellipsis for truncated tickers


class TestBuildAttemptsSummary:
    """Tests for build_attempts_summary function (rejected trade attempts)."""

    def test_empty_attempts(self):
        """Test attempts summary with no rejected decisions."""
        from analysis.market_feeling import build_attempts_summary

        result = build_attempts_summary([])
        assert "No rejected trade attempts today." in result

    def test_single_rejected_buy(self):
        """Test attempts summary with a single rejected BUY."""
        from analysis.market_feeling import build_attempts_summary

        rejected = [{"ticker": "AAPL", "signal": "BUY", "status": "REJECTED_MARGIN"}]
        result = build_attempts_summary(rejected)
        assert "Rejected buys: 1" in result
        assert "AAPL" in result

    def test_mixed_buys_and_sells(self):
        """Test attempts summary with mixed rejected BUY and SELL."""
        from analysis.market_feeling import build_attempts_summary

        rejected = [
            {"ticker": "AAPL", "signal": "BUY", "status": "REJECTED_MARGIN"},
            {"ticker": "GOOGL", "signal": "BUY", "status": "REJECTED_HALLUCINATION"},
            {"ticker": "TSLA", "signal": "SELL", "status": "REJECTED_LIQUIDITY"},
        ]
        result = build_attempts_summary(rejected)
        assert "Rejected buys: 2" in result
        assert "Rejected sells: 1" in result
        assert "AAPL" in result
        assert "TSLA" in result

    def test_shows_rejection_reasons(self):
        """Test that rejection reasons are included in summary."""
        from analysis.market_feeling import build_attempts_summary

        rejected = [
            {"ticker": "AAPL", "signal": "BUY", "status": "REJECTED_MARGIN"},
            {"ticker": "GOOGL", "signal": "BUY", "status": "REJECTED_MARGIN"},
            {"ticker": "TSLA", "signal": "BUY", "status": "REJECTED_HALLUCINATION"},
        ]
        result = build_attempts_summary(rejected)
        assert "MARGIN=2" in result
        assert "HALLUCINATION=1" in result

    def test_truncates_tickers_at_three(self):
        """Test that ticker list is truncated at 3."""
        from analysis.market_feeling import build_attempts_summary

        rejected = [
            {"ticker": f"STOCK{i}", "signal": "BUY", "status": "REJECTED_MARGIN"}
            for i in range(5)
        ]
        result = build_attempts_summary(rejected)
        assert "..." in result

    def test_weekend_mode(self):
        """Test that weekend mode uses correct date label."""
        from analysis.market_feeling import build_attempts_summary

        result = build_attempts_summary([], weekend_mode=True)
        assert "this week" in result


class TestBuildLessonsSummary:
    """Tests for build_lessons_summary function."""

    def test_empty_lessons(self):
        """Test lessons summary with no lessons."""
        from analysis.market_feeling import build_lessons_summary

        result = build_lessons_summary([])
        assert result == "No lessons learned available."

    def test_single_lesson(self):
        """Test lessons summary with a single lesson."""
        from analysis.market_feeling import build_lessons_summary

        lessons = [{"content": "Don't over-leverage on volatile stocks"}]
        result = build_lessons_summary(lessons)
        assert "Don't over-leverage on volatile stocks" in result

    def test_multiple_lessons_truncated(self):
        """Test that lessons are truncated at 5."""
        from analysis.market_feeling import build_lessons_summary

        lessons = [{"content": f"Lesson {i}"} for i in range(7)]
        result = build_lessons_summary(lessons)
        lines = result.split("\n")
        # Should only include first 5 lessons
        assert len(lines) <= 5


class TestBuildEventsSummary:
    """Tests for build_events_summary function."""

    def test_empty_events(self):
        """Test events summary with no events."""
        from analysis.market_feeling import build_events_summary

        result = build_events_summary([])
        assert result == "No market events recorded today."

    def test_events_with_content(self):
        """Test events summary with market events."""
        from analysis.market_feeling import build_events_summary

        events = [
            {"content": "Fed announced rate pause"},
            {"content": "Oil supplies tightening"}
        ]
        result = build_events_summary(events)
        assert "Fed announced rate pause" in result
        assert "Oil supplies tightening" in result


class TestBuildReasoningSummary:
    """Tests for build_reasoning_summary function."""

    def test_empty_decisions(self):
        """Test reasoning summary with no decisions."""
        from analysis.market_feeling import build_reasoning_summary

        result = build_reasoning_summary([])
        assert result == "No decisions made today."

    def test_single_decision(self):
        """Test reasoning summary with a single decision."""
        from analysis.market_feeling import build_reasoning_summary

        decisions = [{
            "ticker": "AAPL",
            "signal": "BUY",
            "confidence": 85,
            "reasoning": "Strong earnings report"
        }]
        result = build_reasoning_summary(decisions)
        assert "AAPL" in result
        assert "BUY" in result
        assert "85" in result
        assert "Strong earnings report" in result

    def test_decisions_truncated_at_ten(self):
        """Test that decisions are truncated at 10."""
        from analysis.market_feeling import build_reasoning_summary

        decisions = [{
            "ticker": f"T{i}",
            "signal": "BUY",
            "confidence": 50,
            "reasoning": f"Reason {i}"
        } for i in range(15)]

        result = build_reasoning_summary(decisions)
        lines = result.split("\n")
        # Should only include first 10 decisions
        assert len(lines) <= 10


class TestBuildPrompt:
    """Tests for build_prompt function."""

    def test_prompt_contains_data(self):
        """Test that prompt contains the provided data."""
        from analysis.market_feeling import build_prompt

        data = {
            "trades": [{"ticker": "AAPL", "signal": "BUY", "quantity": 10, "total_cost": 1500.00}],
            "rejected_attempts": [{"ticker": "NVDA", "signal": "BUY", "status": "REJECTED_MARGIN"}],
            "lessons": [{"content": "Test lesson"}],
            "events": [{"content": "Test event"}],
            "decisions": [{"ticker": "AAPL", "signal": "BUY", "confidence": 85, "reasoning": "Test reasoning"}]
        }

        prompt = build_prompt(data)

        assert "AAPL" in prompt
        assert "NVDA" in prompt
        assert "Test lesson" in prompt
        assert "Test event" in prompt
        assert "Test reasoning" in prompt
        assert "Rejected buys: 1" in prompt

    def test_prompt_has_structure(self):
        """Test that prompt contains expected sections."""
        from analysis.market_feeling import build_prompt

        data = {
            "trades": [],
            "rejected_attempts": [],
            "lessons": [],
            "events": [],
            "decisions": []
        }

        prompt = build_prompt(data)

        assert "CONTEXT:" in prompt
        assert "TASK:" in prompt
        assert "OUTPUT (JSON only" in prompt
        assert "sentiment_label" in prompt
        assert "confidence_score" in prompt
        assert "why_explanation" in prompt
        assert "market_direction" in prompt
        assert "primary_concern" in prompt
        assert "agent conviction" in prompt

    def test_weekend_prompt_has_weekend_recap_label(self):
        """Test that weekend prompt uses 'Weekend Recap' label."""
        from analysis.market_feeling import build_prompt

        data = {
            "trades": [{"ticker": "AAPL", "signal": "BUY", "quantity": 10, "total_cost": 1500.00}],
            "rejected_attempts": [],
            "lessons": [{"content": "Test lesson"}],
            "events": [{"content": "Test event"}],
            "decisions": [{"ticker": "AAPL", "signal": "BUY", "confidence": 85, "reasoning": "Test reasoning"}]
        }

        prompt = build_prompt(data, weekend_mode=True)

        assert "Weekend Recap" in prompt or "weekend" in prompt.lower()
        assert "this week" in prompt

    def test_weekday_prompt_uses_today(self):
        """Test that weekday (default) prompt uses 'today'."""
        from analysis.market_feeling import build_prompt

        data = {
            "trades": [],
            "rejected_attempts": [],
            "lessons": [],
            "events": [],
            "decisions": []
        }

        prompt = build_prompt(data, weekend_mode=False)

        assert "today" in prompt.lower()


class TestIsMarketFeelingStale:
    """Tests for is_market_feeling_stale function."""

    def test_none_feeling_is_stale(self):
        """Test that None feeling is considered stale."""
        from analysis.market_feeling import is_market_feeling_stale

        assert is_market_feeling_stale(None) is True

    def test_missing_created_at_is_stale(self):
        """Test that feeling without created_at is stale."""
        from analysis.market_feeling import is_market_feeling_stale

        assert is_market_feeling_stale({}) is True

    def test_recent_feeling_not_stale(self):
        """Test that recent feeling (1 hour old) is not stale."""
        from analysis.market_feeling import is_market_feeling_stale

        recent = {
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        assert is_market_feeling_stale(recent, stale_threshold_hours=4) is False

    def test_old_feeling_is_stale(self):
        """Test that old feeling (5 hours old) is stale."""
        from analysis.market_feeling import is_market_feeling_stale

        old_time = datetime.now(timezone.utc) - timedelta(hours=5)
        old = {"created_at": old_time.isoformat()}

        assert is_market_feeling_stale(old, stale_threshold_hours=4) is True


class TestGatherTodayData:
    """Tests for gather_today_data function."""

    @pytest.mark.asyncio
    async def test_gather_today_data_returns_structure(self):
        """Test that gather_today_data returns expected structure."""
        from analysis.market_feeling import gather_today_data

        mock_sb = MagicMock()

        # Mock empty responses for all queries
        mock_sb.table.return_value.select.return_value.gte.return_value.execute.return_value.data = []
        mock_sb.table.return_value.select.return_value.execute.return_value.data = []

        with patch("analysis.market_feeling.get_supabase_client", return_value=mock_sb):
            result = await gather_today_data(mock_sb)

            assert "trades" in result
            assert "memories" in result
            assert "lessons" in result
            assert "events" in result
            assert "decisions" in result
            assert isinstance(result["trades"], list)


class TestAnalyzeMarketFeeling:
    """Tests for analyze_market_feeling function."""

    @pytest.mark.asyncio
    async def test_skips_when_no_data(self):
        """Test that analysis skips when there's no data."""
        from analysis.market_feeling import analyze_market_feeling

        # Create a mock supabase client that returns empty data for all queries
        mock_sb = MagicMock()

        # Setup mock chain for all table queries
        def create_empty_response(*args, **kwargs):
            mock_response = MagicMock()
            mock_response.data = []
            return mock_response

        mock_sb.table.return_value.select.return_value.gte.return_value.execute.return_value.data = []
        mock_sb.table.return_value.select.return_value.execute.return_value.data = []

        with patch("analysis.market_feeling.get_supabase_client", return_value=mock_sb):
            result = await analyze_market_feeling()

            assert result is None

    @pytest.mark.asyncio
    async def test_handles_api_key_missing(self):
        """Test that analysis handles missing API key gracefully."""
        from analysis.market_feeling import analyze_market_feeling

        # Create mock supabase client
        mock_sb = MagicMock()
        mock_sb.table.return_value.select.return_value.gte.return_value.execute.return_value.data = [
            {"id": "t1", "ticker": "AAPL", "signal": "BUY", "total_cost": 1500.00}
        ]
        mock_sb.table.return_value.select.return_value.execute.return_value.data = []

        with patch("analysis.market_feeling.get_supabase_client", return_value=mock_sb), \
             patch("analysis.market_feeling.MINIMAX_API_KEY", None):
            result = await analyze_market_feeling()

            # Should return None because no API key
            assert result is None

    @pytest.mark.asyncio
    async def test_handles_api_failure(self):
        """Test that MiniMax API failures are handled without crashing."""
        from analysis.market_feeling import analyze_market_feeling

        # Create mock supabase client with some data
        mock_sb = MagicMock()
        mock_sb.table.return_value.select.return_value.gte.return_value.execute.return_value.data = [
            {"id": "t1", "ticker": "AAPL", "signal": "BUY", "total_cost": 1500.00}
        ]
        mock_sb.table.return_value.select.return_value.execute.return_value.data = []

        with patch("analysis.market_feeling.get_supabase_client", return_value=mock_sb), \
             patch("analysis.market_feeling.MINIMAX_API_KEY", "fake-key"), \
             patch("analysis.market_feeling.MiniMaxClient") as MockClient:
            mock_client_instance = MagicMock()
            mock_client_instance.chat_with_json_response = AsyncMock(side_effect=Exception("API Error"))
            mock_client_instance.close = AsyncMock()
            MockClient.return_value = mock_client_instance

            result = await analyze_market_feeling()

            # Should return None on API failure, not crash
            assert result is None