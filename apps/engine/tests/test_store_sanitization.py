"""Tests for memory store: HTML sanitization and RAG scoping."""

from unittest.mock import MagicMock, patch

from memory.store import prune_context, retrieve_for_decision


class TestStripHtml:
    """Unit tests for strip_html utility function."""

    def _import_strip_html(self):
        """Import strip_html directly from the module after it's defined."""
        from memory import store

        return store.strip_html

    def test_removes_simple_html_tags(self):
        strip_html = self._import_strip_html()
        assert strip_html("<button>Best for employees</button>") == "Best for employees"

    def test_removes_tags_with_attributes(self):
        strip_html = self._import_strip_html()
        html = '<button type="button" id="tabs-1" class="chakra-tabs__tab">Best for employees</button>'
        assert strip_html(html) == "Best for employees"

    def test_removes_nested_tags(self):
        strip_html = self._import_strip_html()
        html = "<div><p>Hello <b>world</b></p></div>"
        assert strip_html(html) == "Hello world"

    def test_preserves_plain_text(self):
        strip_html = self._import_strip_html()
        assert strip_html("Best for employees") == "Best for employees"

    def test_empty_string(self):
        strip_html = self._import_strip_html()
        assert strip_html("") == ""

    def test_none_input(self):
        strip_html = self._import_strip_html()
        assert strip_html(None) is None

    def test_self_closing_tags(self):
        strip_html = self._import_strip_html()
        html = "Line1<br/>Line2<br />Line3"
        result = strip_html(html)
        assert "Line1" in result
        assert "Line2" in result
        assert "Line3" in result
        assert "<br" not in result

    def test_mixed_content(self):
        strip_html = self._import_strip_html()
        html = "Buy <b>NVDA</b> now! <br> Price target: $150"
        assert strip_html(html) == "Buy NVDA now! Price target: $150"


class TestPruneContextSanitization:
    """Tests that prune_context strips HTML from content."""

    def test_strips_html_from_content(self):
        items = [
            {
                "content": "<button>Best for employees</button>",
                "importance_score": 8,
                "similarity": 0.9,
                "label": "PAST REASONING",
                "ticker": "NVDA",
            }
        ]
        result = prune_context(items, max_tokens=2000)
        assert "Best for employees" in result
        assert "<button>" not in result
        assert "</button>" not in result

    def test_strips_html_from_multiple_items(self):
        items = [
            {
                "content": "Normal text here",
                "importance_score": 5,
                "similarity": 0.8,
                "label": "PAST REASONING",
                "ticker": "AAPL",
            },
            {
                "content": '<div class="price">Price target $200</div>',
                "importance_score": 9,
                "similarity": 0.9,
                "label": "PAST REASONING",
                "ticker": "NVDA",
            },
        ]
        result = prune_context(items, max_tokens=2000)
        assert "Normal text here" in result
        assert "Price target $200" in result
        assert "<div" not in result
        assert "</div>" not in result

    def test_preserves_plain_text_unchanged(self):
        items = [
            {
                "content": "Strong earnings growth expected next quarter",
                "importance_score": 7,
                "similarity": 0.85,
                "label": "MARKET EVENT",
                "ticker": "MSFT",
            }
        ]
        result = prune_context(items, max_tokens=2000)
        assert "Strong earnings growth expected next quarter" in result

    def test_empty_content_with_html(self):
        items = [
            {
                "content": "<br/>",
                "importance_score": 5,
                "similarity": 0.5,
                "label": "MARKET EVENT",
                "ticker": "AAPL",
            }
        ]
        result = prune_context(items, max_tokens=2000)
        assert result == ""

    def test_scoring_still_works_after_sanitization(self):
        items = [
            {
                "content": "<b>Low priority</b>",
                "importance_score": 1,
                "similarity": 0.1,
                "label": "MARKET EVENT",
                "ticker": "AAPL",
            },
            {
                "content": "<i>High priority</i> event",
                "importance_score": 10,
                "similarity": 0.9,
                "label": "PAST REASONING",
                "ticker": "NVDA",
            },
        ]
        result = prune_context(items, max_tokens=2000)
        assert "High priority event" in result
        assert "Low priority" in result
        assert "<b>" not in result
        assert "<i>" not in result


class TestRetrieveForDecisionModelFilter:
    """Tests that retrieve_for_decision accepts and passes model_name."""

    @patch("memory.store.get_embedding")
    @patch("memory.store.get_supabase_client")
    def test_passes_model_name_to_match_decisions(
        self, mock_get_supabase, mock_get_embedding
    ):
        mock_get_embedding.return_value = [0.1] * 768
        mock_client = MagicMock()
        mock_rpc = MagicMock()
        mock_client.rpc = mock_rpc
        mock_get_supabase.return_value = mock_client

        mock_mem_response = MagicMock()
        mock_mem_response.data = []
        mock_dec_response = MagicMock()
        mock_dec_response.data = []

        mock_rpc.side_effect = [mock_mem_response, mock_dec_response]

        retrieve_for_decision(
            ticker="NVDA", reasoning="test", model_name="deepseek-reasoner"
        )

        # match_memories - no model_name filter
        mem_call = mock_rpc.call_args_list[0]
        assert mem_call[0][0] == "match_memories"

        # match_decisions - should have filter_model_name
        dec_call = mock_rpc.call_args_list[1]
        assert dec_call[0][0] == "match_decisions"
        assert dec_call[0][1]["filter_model_name"] == "deepseek-reasoner"

    @patch("memory.store.get_embedding")
    @patch("memory.store.get_supabase_client")
    def test_no_model_name_defaults_to_none(
        self, mock_get_supabase, mock_get_embedding
    ):
        mock_get_embedding.return_value = [0.1] * 768
        mock_client = MagicMock()
        mock_rpc = MagicMock()
        mock_client.rpc = mock_rpc
        mock_get_supabase.return_value = mock_client

        mock_mem_response = MagicMock()
        mock_mem_response.data = []
        mock_dec_response = MagicMock()
        mock_dec_response.data = []

        mock_rpc.side_effect = [mock_mem_response, mock_dec_response]

        retrieve_for_decision(ticker="NVDA", reasoning="test")

        dec_call = mock_rpc.call_args_list[1]
        assert dec_call[0][1]["filter_model_name"] is None

    @patch("memory.store.get_embedding")
    @patch("memory.store.get_supabase_client")
    def test_match_memories_never_gets_model_filter(
        self, mock_get_supabase, mock_get_embedding
    ):
        mock_get_embedding.return_value = [0.1] * 768
        mock_client = MagicMock()
        mock_rpc = MagicMock()
        mock_client.rpc = mock_rpc
        mock_get_supabase.return_value = mock_client

        mock_mem_response = MagicMock()
        mock_mem_response.data = []
        mock_dec_response = MagicMock()
        mock_dec_response.data = []

        mock_rpc.side_effect = [mock_mem_response, mock_dec_response]

        retrieve_for_decision(
            ticker="NVDA", reasoning="test", model_name="deepseek-reasoner"
        )

        mem_call = mock_rpc.call_args_list[0]
        assert "filter_model_name" not in mem_call[1]
        assert mem_call[1].get("filter_memory_types") is None
