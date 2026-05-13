from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from analysis.discovery_agent import DiscoveryAgent

VALID_JSON_RESULT = """Here is my analysis:

```json
{
  "assets": [
    {
      "ticker": "DLR",
      "name": "Digital Realty Trust",
      "reason": "Leading data center REIT with significant AI infrastructure exposure through colocation services"
    },
    {
      "ticker": "EQIX",
      "name": "Equinix",
      "reason": "Global colocation leader providing critical infrastructure for AI compute workloads"
    },
    {
      "ticker": "NVDA",
      "name": "NVIDIA",
      "reason": "Primary GPU supplier for AI training and inference workloads"
    }
  ]
}
```

These are the top beneficiaries."""


SIMPLE_JSON_RESULT = """```json
{
  "assets": [
    {"ticker": "AAPL", "name": "Apple", "reason": "Consumer AI integration"},
    {"ticker": "MSFT", "name": "Microsoft", "reason": "Azure AI services"}
  ]
}
```"""


@pytest.fixture
def mock_provider():
    """Fixture to mock LLM provider calls."""
    with patch("analysis.discovery_agent.gemini") as mock_gemini, \
         patch("analysis.discovery_agent.openai") as mock_openai, \
         patch("analysis.discovery_agent.anthropic") as mock_anthropic, \
         patch("analysis.discovery_agent.clients.CLIENT_FACTORIES", {"gemini": MagicMock, "openai": MagicMock, "anthropic": MagicMock}):
        yield {"gemini": mock_gemini, "openai": mock_openai, "anthropic": mock_anthropic}


@pytest.fixture
def mock_client_factory():
    """Fixture to mock client factory to avoid real API calls."""
    with patch("analysis.discovery_agent.clients.CLIENT_FACTORIES", {"gemini": MagicMock, "openai": MagicMock, "anthropic": MagicMock}):
        yield


class TestDiscoveryAgentSingleCall:
    """Tests for single-call JSON output in discover_assets."""

    @pytest.mark.asyncio
    async def test_parses_valid_json_response(self, mock_provider):
        """Verify that valid JSON in response is parsed correctly."""
        agent = DiscoveryAgent(model_name="gemini/gemini-2.0-flash")
        
        mock_run_tool_loop = AsyncMock()
        mock_provider["gemini"].run_tool_loop = mock_run_tool_loop
        
        async def capture_messages(raw_client, model_name, messages, **kwargs):
            messages.append({"role": "assistant", "content": VALID_JSON_RESULT})
        
        mock_run_tool_loop.side_effect = capture_messages
        agent.client = MagicMock()
        
        result = await agent.discover_assets("AI infrastructure")
        
        assert len(result) == 3
        assert result[0]["ticker"] == "DLR"
        assert result[0]["name"] == "Digital Realty Trust"
        assert "AI infrastructure" in result[0]["reason"]
        assert mock_run_tool_loop.call_count == 1

    @pytest.mark.asyncio
    async def test_returns_max_5_assets(self, mock_provider):
        """Verify that no more than 5 assets are returned."""
        agent = DiscoveryAgent(model_name="openai/gpt-4o-mini")
        
        mock_run_tool_loop = AsyncMock()
        mock_provider["openai"].run_tool_loop = mock_run_tool_loop
        
        many_assets = """```json
{
  "assets": [
    {"ticker": "A", "name": "Asset A", "reason": "Reason A"},
    {"ticker": "B", "name": "Asset B", "reason": "Reason B"},
    {"ticker": "C", "name": "Asset C", "reason": "Reason C"},
    {"ticker": "D", "name": "Asset D", "reason": "Reason D"},
    {"ticker": "E", "name": "Asset E", "reason": "Reason E"},
    {"ticker": "F", "name": "Asset F", "reason": "Reason F"},
    {"ticker": "G", "name": "Asset G", "reason": "Reason G"}
  ]
}
```"""
        
        async def capture_messages(raw_client, model_name, messages, **kwargs):
            messages.append({"role": "assistant", "content": many_assets})
        
        mock_run_tool_loop.side_effect = capture_messages
        agent.client = MagicMock()
        
        result = await agent.discover_assets("AI infrastructure")
        
        assert len(result) == 5

    @pytest.mark.asyncio
    async def test_returns_empty_on_no_text(self, mock_provider):
        """Verify empty list returned when no text content in response, even after forced completion."""
        agent = DiscoveryAgent(model_name="anthropic/claude-haiku")
        
        mock_run_tool_loop = AsyncMock()
        mock_provider["anthropic"].run_tool_loop = mock_run_tool_loop
        
        async def capture_messages(raw_client, model_name, messages, **kwargs):
            messages.append({"role": "tool", "content": "Some tool result"})
        
        mock_run_tool_loop.side_effect = capture_messages
        agent.client = MagicMock()
        
        with patch.object(agent, "_force_text_completion", new_callable=AsyncMock) as mock_force:
            result = await agent.discover_assets("AI infrastructure")
        
        assert result == []
        mock_force.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_forced_completion_saves_the_result(self, mock_provider):
        """Verify forced text completion can extract results when tool loop produces no text."""
        agent = DiscoveryAgent(model_name="openai/gpt-4o-mini")
        
        mock_run_tool_loop = AsyncMock()
        mock_provider["openai"].run_tool_loop = mock_run_tool_loop
        
        async def capture_messages(raw_client, model_name, messages, **kwargs):
            messages.append({"role": "tool", "content": "Some tool result"})
        
        mock_run_tool_loop.side_effect = capture_messages
        agent.client = MagicMock()
        
        with patch.object(agent, "_force_text_completion", new_callable=AsyncMock) as mock_force:
            async def force_side_effect(messages):
                messages.append({"role": "assistant", "content": SIMPLE_JSON_RESULT})
            mock_force.side_effect = force_side_effect
            
            result = await agent.discover_assets("AI infrastructure")
        
        assert len(result) == 2
        assert result[0]["ticker"] == "AAPL"
        assert result[1]["ticker"] == "MSFT"
        mock_force.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_returns_empty_on_invalid_json(self, mock_provider):
        """Verify empty list returned when JSON parsing fails."""
        agent = DiscoveryAgent(model_name="gemini/gemini-2.0-flash")
        
        mock_run_tool_loop = AsyncMock()
        mock_provider["gemini"].run_tool_loop = mock_run_tool_loop
        
        invalid_json = """Here is my analysis but I didn't format it correctly.
Just some text without proper JSON."""
        
        async def capture_messages(raw_client, model_name, messages, **kwargs):
            messages.append({"role": "assistant", "content": invalid_json})
        
        mock_run_tool_loop.side_effect = capture_messages
        agent.client = MagicMock()
        
        result = await agent.discover_assets("AI infrastructure")
        
        assert result == []


class TestJSONParsing:
    """Tests for _parse_json_response method."""

    @pytest.fixture(autouse=True)
    def setup_mocks(self, mock_client_factory):
        """Apply mock_client_factory to all tests in this class."""
        pass

    def test_parse_valid_json_with_assets_key(self):
        """Verify parsing JSON object with assets array."""
        agent = DiscoveryAgent(model_name="gemini/gemini-2.0-flash")
        
        text = """```json
{
  "assets": [
    {"ticker": "DLR", "name": "Digital Realty", "reason": "Data centers"}
  ]
}
```"""
        
        result = agent._parse_json_response(text)
        
        assert len(result) == 1
        assert result[0]["ticker"] == "DLR"

    def test_parse_valid_json_array_directly(self):
        """Verify parsing JSON array directly without assets wrapper."""
        agent = DiscoveryAgent(model_name="gemini/gemini-2.0-flash")
        
        text = """[
  {"ticker": "AAPL", "name": "Apple", "reason": "Consumer AI"}
]"""
        
        result = agent._parse_json_response(text)
        
        assert len(result) == 1
        assert result[0]["ticker"] == "AAPL"

    def test_ticker_uppercased(self):
        """Verify tickers are uppercased."""
        agent = DiscoveryAgent(model_name="gemini/gemini-2.0-flash")
        
        text = '{"assets": [{"ticker": "aapl", "name": "Apple", "reason": "Test"}]}'
        
        result = agent._parse_json_response(text)
        
        assert result[0]["ticker"] == "AAPL"

    def test_missing_ticker_filtered(self):
        """Verify assets without ticker are filtered out."""
        agent = DiscoveryAgent(model_name="gemini/gemini-2.0-flash")
        
        text = """{"assets": [
            {"ticker": "AAPL", "name": "Apple", "reason": "Test"},
            {"name": "No Ticker", "reason": "Missing"}
        ]}"""
        
        result = agent._parse_json_response(text)
        
        assert len(result) == 1
        assert result[0]["ticker"] == "AAPL"


class TestExtractFinalText:
    """Tests for _extract_final_text method."""

    @pytest.fixture(autouse=True)
    def setup_mocks(self, mock_client_factory):
        """Apply mock_client_factory to all tests in this class."""
        pass

    def test_finds_last_assistant_message(self):
        """Verify last assistant message is found."""
        agent = DiscoveryAgent(model_name="gemini/gemini-2.0-flash")
        
        messages = [
            {"role": "user", "content": "Theme: AI"},
            {"role": "assistant", "content": "Thinking..."},
            {"role": "tool", "content": "Tool result"},
            {"role": "assistant", "content": "Final answer"}
        ]
        
        result = agent._extract_final_text(messages)
        
        assert result == "Final answer"

    def test_skips_empty_content(self):
        """Verify empty content is skipped."""
        agent = DiscoveryAgent(model_name="gemini/gemini-2.0-flash")
        
        messages = [
            {"role": "user", "content": "Theme: AI"},
            {"role": "assistant", "content": ""},
            {"role": "assistant", "content": "Final answer"}
        ]
        
        result = agent._extract_final_text(messages)
        
        assert result == "Final answer"

    def test_handles_object_with_parts(self):
        """Verify handling of message objects with parts attribute."""
        agent = DiscoveryAgent(model_name="gemini/gemini-2.0-flash")
        
        msg = MagicMock()
        msg.role = "model"
        msg.parts = [MagicMock(text="Final answer with parts")]
        
        result = agent._extract_final_text([msg])
        
        assert result == "Final answer with parts"

    def test_handles_anthropic_list_content(self):
        """Verify handling of Anthropic messages where content is a list of text blocks."""
        agent = DiscoveryAgent(model_name="gemini/gemini-2.0-flash")
        
        messages = [
            {"role": "user", "content": "Theme: AI"},
            {"role": "assistant", "content": [
                {"type": "tool_use", "name": "screener", "input": {}},
                {"type": "text", "text": "Here are my findings"},
            ]},
        ]
        
        result = agent._extract_final_text(messages)
        assert result == "Here are my findings"

    def test_handles_anthropic_mixed_blocks(self):
        """Verify Anthropic blocks with multiple text parts are joined."""
        agent = DiscoveryAgent(model_name="gemini/gemini-2.0-flash")
        
        messages = [
            {"role": "assistant", "content": [
                {"type": "text", "text": "Part one"},
                {"type": "tool_use", "name": "screener", "input": {}},
                {"type": "text", "text": "Part two"},
            ]},
        ]
        
        result = agent._extract_final_text(messages)
        assert result == "Part one Part two"

    def test_returns_empty_on_no_content(self):
        """Verify empty string returned when no valid content found."""
        agent = DiscoveryAgent(model_name="gemini/gemini-2.0-flash")
        
        messages = [
            {"role": "tool", "content": "Tool result"},
            {"role": "user", "content": "Theme: AI"}
        ]
        
        result = agent._extract_final_text(messages)
        
        assert result == ""
