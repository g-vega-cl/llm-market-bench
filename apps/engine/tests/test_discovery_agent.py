import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from analysis.discovery_agent import DiscoveryAgent


VALID_5_WHYS_RESULT = """
## 5 Whys Analysis

1. **Why** is this theme market-moving? This theme is market-moving because AI infrastructure spending is reaching unprecedented levels, creating sustained demand for data center capacity.

2. **Why** will these specific assets benefit? These specific assets will benefit because they provide essential infrastructure components like power distribution and cooling systems.

3. **Why** are these not already priced in? These are not already priced in because the AI capex cycle is still in early innings and market estimates remain conservative.

4. **Why** is this the most efficient way to profit? This is the most efficient way to profit because infrastructure plays provide leveraged exposure without direct AI competition risks.

5. **Why** is your recommendation the best beneficiary of this theme? My recommendation is the best beneficiary because these companies have long-term contracts and pricing power.

## Recommended Assets

| Ticker | Company Name | Relevance Score | Mechanism of Profit |
|--------|--------------|-----------------|---------------------|
| $DLR   | Digital Realty | 85 | Data center infrastructure |
"""


@pytest.fixture
def mock_provider():
    """Fixture to mock LLM provider calls."""
    with patch("analysis.discovery_agent.gemini") as mock_gemini, \
         patch("analysis.discovery_agent.openai") as mock_openai, \
         patch("analysis.discovery_agent.anthropic") as mock_anthropic, \
         patch("analysis.discovery_agent.clients.CLIENT_FACTORIES", {"gemini": MagicMock, "openai": MagicMock, "anthropic": MagicMock}):
        yield {"gemini": mock_gemini, "openai": mock_openai, "anthropic": mock_anthropic}


class TestDiscoveryAgentRetryLogic:
    """Tests for retry logic in discover_assets."""

    @pytest.mark.asyncio
    async def test_retry_on_empty_result_then_success(self, mock_provider):
        """Verify retry when first attempt returns empty, second succeeds with 5 Whys."""
        agent = DiscoveryAgent(model_name="gemini/gemini-2.0-flash")
        
        mock_run_tool_loop = AsyncMock()
        mock_provider["gemini"].run_tool_loop = mock_run_tool_loop
        
        call_count = [0]
        
        async def capture_messages(raw_client, model_name, messages, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                messages.append({"role": "assistant", "content": ""})
                messages.append({"role": "tool", "content": "Some tool result"})
            else:
                messages.append({"role": "assistant", "content": VALID_5_WHYS_RESULT})
        
        mock_run_tool_loop.side_effect = capture_messages
        
        agent.client = MagicMock()
        
        result = await agent.discover_assets("AI infrastructure")
        
        assert VALID_5_WHYS_RESULT in result
        assert mock_run_tool_loop.call_count == 2

    @pytest.mark.asyncio
    async def test_retry_on_missing_5_whys(self, mock_provider):
        """Verify retry when 5 Whys validation fails, second attempt succeeds."""
        agent = DiscoveryAgent(model_name="gemini/gemini-2.0-flash")
        
        mock_run_tool_loop = AsyncMock()
        mock_provider["gemini"].run_tool_loop = mock_run_tool_loop
        
        incomplete_result = """
## Recommended Assets

Some stocks were found but 5 Whys not completed.
"""
        
        call_count = [0]
        
        async def capture_messages(raw_client, model_name, messages, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                messages.append({"role": "assistant", "content": incomplete_result})
            else:
                messages.append({"role": "assistant", "content": VALID_5_WHYS_RESULT})
        
        mock_run_tool_loop.side_effect = capture_messages
        
        agent.client = MagicMock()
        
        result = await agent.discover_assets("AI infrastructure")
        
        assert mock_run_tool_loop.call_count == 2
        assert "5 Whys" in result

    @pytest.mark.asyncio
    async def test_no_retry_on_success(self, mock_provider):
        """Verify no extra call when first attempt succeeds with valid 5 Whys."""
        agent = DiscoveryAgent(model_name="gemini/gemini-2.0-flash")
        
        mock_run_tool_loop = AsyncMock()
        mock_provider["gemini"].run_tool_loop = mock_run_tool_loop
        
        async def capture_messages(raw_client, model_name, messages, **kwargs):
            messages.append({"role": "assistant", "content": VALID_5_WHYS_RESULT})
        
        mock_run_tool_loop.side_effect = capture_messages
        
        agent.client = MagicMock()
        
        result = await agent.discover_assets("AI infrastructure")
        
        assert VALID_5_WHYS_RESULT in result
        assert mock_run_tool_loop.call_count == 1

    @pytest.mark.asyncio
    async def test_max_2_attempts(self, mock_provider):
        """Verify exactly 2 attempts total when validation keeps failing."""
        agent = DiscoveryAgent(model_name="gemini/gemini-2.0-flash")
        
        mock_run_tool_loop = AsyncMock()
        mock_provider["gemini"].run_tool_loop = mock_run_tool_loop
        
        incomplete_result = "Incomplete analysis without 5 Whys."
        
        async def capture_messages(raw_client, model_name, messages, **kwargs):
            messages.append({"role": "assistant", "content": incomplete_result})
        
        mock_run_tool_loop.side_effect = capture_messages
        
        agent.client = MagicMock()
        
        result = await agent.discover_assets("AI infrastructure")
        
        assert mock_run_tool_loop.call_count == 2


class TestFallbackCollection:
    """Tests for _collect_tool_results_fallback."""

    def test_fallback_captures_valid_tool_results(self):
        """Verify fallback captures valid tool results even without assistant text."""
        agent = DiscoveryAgent(model_name="gemini/gemini-2.0-flash")
        
        messages = [
            {"role": "user", "content": "THEME: AI infrastructure\n\nCONTEXT: None"},
            {"role": "assistant", "content": ""},
            {"role": "tool", "content": "$DLR (Digital Realty): Price $150, Data center REIT"},
            {"role": "tool", "content": "$EQIX (Equinix): Price $800, Colocation services"},
        ]
        
        result = agent._collect_tool_results_fallback(messages)
        
        assert "DLR" in result
        assert "EQIX" in result

    def test_fallback_ignores_error_results(self):
        """Verify fallback ignores tool results containing errors."""
        agent = DiscoveryAgent(model_name="gemini/gemini-2.0-flash")
        
        messages = [
            {"role": "tool", "content": "Error: API rate limit exceeded"},
            {"role": "tool", "content": "$DLR: Price $150"},
        ]
        
        result = agent._collect_tool_results_fallback(messages)
        
        assert "Error" not in result
        assert "DLR" in result

    def test_fallback_ignores_no_stocks_found(self):
        """Verify fallback ignores 'no stocks found' messages."""
        agent = DiscoveryAgent(model_name="gemini/gemini-2.0-flash")
        
        messages = [
            {"role": "tool", "content": "No stocks found matching criteria"},
            {"role": "tool", "content": "$DLR: Price $150"},
        ]
        
        result = agent._collect_tool_results_fallback(messages)
        
        assert "No stocks found" not in result
        assert "DLR" in result


class TestValidate5Whys:
    """Tests for _validate_5_whys method."""

    def test_valid_5_whys_all_present(self):
        """Verify validation passes when all 5 Whys are present."""
        agent = DiscoveryAgent(model_name="gemini/gemini-2.0-flash")
        
        is_valid, missing = agent._validate_5_whys(VALID_5_WHYS_RESULT)
        
        assert is_valid is True
        assert len(missing) == 0

    def test_valid_5_whys_missing_some(self):
        """Verify validation fails with list of missing Whys."""
        agent = DiscoveryAgent(model_name="gemini/gemini-2.0-flash")
        
        incomplete = """
1. **Why** is this theme market-moving? Answer here.
2. **Why** will these specific assets benefit? Answer here.
Missing others.
"""
        
        is_valid, missing = agent._validate_5_whys(incomplete)
        
        assert is_valid is False
        assert "Why #3" in missing
        assert "Why #4" in missing
        assert "Why #5" in missing

    def test_validate_5_whys_empty_content(self):
        """Verify validation fails on empty content."""
        agent = DiscoveryAgent(model_name="gemini/gemini-2.0-flash")
        
        is_valid, missing = agent._validate_5_whys("")
        
        assert is_valid is False
        assert len(missing) == 5


class TestBuildCorrectionPrompt:
    """Tests for _build_correction_prompt method."""

    def test_build_correction_prompt_with_missing(self):
        """Verify correction prompt includes missing 5 Whys."""
        agent = DiscoveryAgent(model_name="gemini/gemini-2.0-flash")
        
        previous_result = "Incomplete analysis"
        missing = ["Why #3", "Why #5"]
        
        prompt = agent._build_correction_prompt("AI theme", "context", previous_result, missing)
        
        assert "PREVIOUS ATTEMPT RESULTS" in prompt
        assert "Missing 5 Whys sections" in prompt
        assert "Why #3" in prompt
        assert "Why #5" in prompt
        assert "AI theme" in prompt

    def test_build_correction_prompt_no_missing(self):
        """Verify correction prompt when no missing (shouldn't happen but should handle)."""
        agent = DiscoveryAgent(model_name="gemini/gemini-2.0-flash")
        
        previous_result = "Complete analysis"
        missing = []
        
        prompt = agent._build_correction_prompt("AI theme", "context", previous_result, missing)
        
        assert "PREVIOUS ATTEMPT RESULTS" in prompt
        assert "None" in prompt
