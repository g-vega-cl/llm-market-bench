import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import os
import sys

# Ensure apps/engine is in path
sys.path.append(os.path.join(os.getcwd(), "apps/engine"))

from core.llm.handlers.deepseek import run_tool_loop
from execution.market_data import MarketDataManager
from execution.providers.base import TickerData


@pytest.mark.asyncio
async def test_discovery_agent_invokes_gemini_handler_submodule():
    """
    Regression test for discovery agent handler imports.
    Ensures the Gemini tool loop is resolved from the concrete submodule.
    """
    dummy_client = MagicMock()

    async def fake_run_tool_loop(raw_client, model_name, messages, **kwargs):
        messages.append({"role": "assistant", "content": "AI infrastructure beneficiaries: NVDA, ARM"})

    with patch("analysis.discovery_agent.clients.CLIENT_FACTORIES", {"gemini": lambda: dummy_client}), \
         patch("analysis.discovery_agent.gemini.run_tool_loop", new=AsyncMock(side_effect=fake_run_tool_loop)) as mock_loop:
        from analysis.discovery_agent import DiscoveryAgent

        agent = DiscoveryAgent(model_name="gemini-2.0-flash")
        result = await agent.discover_assets("AI infrastructure demand")

    assert result == "AI infrastructure beneficiaries: NVDA, ARM"
    assert mock_loop.await_count == 1


@pytest.mark.asyncio
async def test_discovery_agent_does_not_echo_theme_when_tool_loop_stalls():
    """
    Regression test for the discovery fallback path.
    If no assistant/model text is produced, the original theme prompt must not be returned.
    """
    dummy_client = MagicMock()

    async def stalled_run_tool_loop(raw_client, model_name, messages, **kwargs):
        messages.append({"role": "tool", "content": "partial tool output"})

    with patch("analysis.discovery_agent.clients.CLIENT_FACTORIES", {"openai": lambda: dummy_client}), \
         patch("analysis.discovery_agent.openai.run_tool_loop", new=AsyncMock(side_effect=stalled_run_tool_loop)) as mock_loop:
        from analysis.discovery_agent import DiscoveryAgent

        agent = DiscoveryAgent(model_name="gpt-4o-mini")
        theme = "Global uranium supply shortage"
        result = await agent.discover_assets(theme)

    assert result == "No assets discovered."
    assert "THEME:" not in result
    assert result != theme
    assert mock_loop.await_count == 1

@pytest.mark.asyncio
async def test_deepseek_reasoning_preservation_regression():
    """
    Regression test for DeepSeek reasoning preservation during tool loops.
    Ensures reasoning_content is not cleared when tool_calls are present.
    """
    mock_client = AsyncMock()
    
    # Simulate two-step response
    msg1 = MagicMock()
    msg1.role = "assistant"
    msg1.content = "Thinking..."
    msg1.reasoning_content = "I should check the price of AAPL."
    msg1.tool_calls = [
        MagicMock(id="call_1", function=MagicMock(name="get_stock_quote", arguments='{"ticker": "AAPL"}'))
    ]
    
    msg2 = MagicMock()
    msg2.role = "assistant"
    msg2.content = "AAPL is $180. Buy."
    msg2.reasoning_content = "Price is good."
    msg2.tool_calls = None
    
    resp1 = MagicMock()
    resp1.choices = [MagicMock(message=msg1)]
    resp2 = MagicMock()
    resp2.choices = [MagicMock(message=msg2)]
    
    mock_client.chat.completions.create.side_effect = [resp1, resp2]
    
    messages = [{"role": "user", "content": "Buy AAPL?"}]
    
    await run_tool_loop(
        mock_client,
        model_name="deepseek-reasoner",
        messages=messages,
        provider="deepseek",
        max_tool_steps=2
    )
    
    # Verify that the second request sent to deepseek included the reasoning_content from the first step
    call_args = mock_client.chat.completions.create.call_args_list
    assert len(call_args) > 1, "Loop did not reach second call"
    
    sent_messages = call_args[1].kwargs['messages']
    asst_msg = sent_messages[1]
    assert asst_msg.get('reasoning_content') == "I should check the price of AAPL.", "Reasoning content was lost/cleared"

@pytest.mark.asyncio
async def test_market_data_fallback_logic_regression():
    """
    Regression test for market data fallback logic.
    Mocks providers to verify that if primary fails, fallback is used.
    This avoids hitting real APIs in CI while verifying the structural fix.
    """
    with patch("execution.market_data.get_supabase_client") as mock_get_db:
        # Mock Supabase
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        # Mock cache miss
        mock_db.table().select().eq().execute.return_value = MagicMock(data=[])
        # Mock history miss
        mock_db.table().select().eq().order().limit().execute.return_value = MagicMock(data=[])

        # Initialize manager - it will load configured providers
        manager = MarketDataManager()
        
        # Mock the providers inside the manager
        primary = AsyncMock()
        primary.provider_name = "mock_primary"
        primary.get_ticker_data.return_value = None # Simulate failure
        
        fallback = AsyncMock()
        fallback.provider_name = "mock_fallback"
        fallback.get_ticker_data.return_value = TickerData(ticker="AMZN", price=150.0, market_cap=1e12, exists=True)
        
        manager.providers = [primary, fallback]
        
        # Execute
        quote = await manager.get_quote("AMZN")
        
        # Verify
        assert quote is not None
        assert quote.price == 150.0
        assert primary.get_ticker_data.called
        assert fallback.get_ticker_data.called
        assert mock_db.table("market_data_cache").upsert.called, "Should have saved fallback result to cache"

def test_config_fmp_key_resolution():
    """
    Verifies that the engine is looking for FMP_API_KEY in the environment.
    In CI, this might be empty unless secrets are provided, but we check 
    that the logic is searching for the correct key name.
    """
    from core import config
    # We just verify the attribute exists. 
    # Whether it has a value depends on CI secrets config.
    assert hasattr(config, "FMP_API_KEY")
