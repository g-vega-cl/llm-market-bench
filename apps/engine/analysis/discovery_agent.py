"""Specialized agent for discovering investable assets based on market themes."""

import logging
from typing import Optional

from core.config import GEMINI_MODEL
from core.llm import clients, prompts, tools
from core.llm.handlers import gemini, openai, anthropic
from execution.market_data import MarketDataManager

logger = logging.getLogger("engine")

def get_provider_from_model(model_name: str) -> str:
    """Detects provider from model name string."""
    model_name = model_name.lower()
    if "gemini" in model_name:
        return "gemini"
    if "claude" in model_name or "anthropic" in model_name:
        return "anthropic"
    if "gpt" in model_name or "o1" in model_name or "o3" in model_name:
        return "openai"
    if "deepseek" in model_name:
        return "deepseek"
    return "openai" # Default

class DiscoveryAgent:
    """Agent that uses reasoning and tools to find thematic stock beneficiaries."""

    def __init__(self, model_name: str = GEMINI_MODEL):
        self.model_name = model_name
        self.provider = get_provider_from_model(model_name)
        self.client = clients.CLIENT_FACTORIES[self.provider]()
        
        # Tools specifically for discovery
        if self.provider == "gemini":
            self.discovery_tools = [
                tools.RUN_STOCK_SCREENER_TOOL_DEFINITION_GEMINI,
            ]
        elif self.provider == "anthropic":
            self.discovery_tools = [
                tools.RUN_STOCK_SCREENER_TOOL_DEFINITION_ANTHROPIC,
            ]
        else:
            self.discovery_tools = [
                tools.RUN_STOCK_SCREENER_TOOL_DEFINITION_OPENAI,
            ]

    async def discover_assets(self, theme: str, context: Optional[str] = None) -> str:
        """Executes a tool-calling mission to find assets for a given theme.
        
        Args:
            theme: The market theme or macro event (e.g., "AI infrastructure demand").
            context: Optional additional context or past events.
            
        Returns:
            A string containing the agent's findings and recommended tickers.
        """
        logger.info(f"DiscoveryAgent starting mission for theme: {theme}")
        
        messages = [
            {"role": "system", "content": prompts.DISCOVERY_AGENT_SYSTEM_PROMPT},
            {"role": "user", "content": f"THEME: {theme}\n\nCONTEXT: {context or 'None'}"}
        ]

        # Use the standard tool loop handler for the provider
        if self.provider == "gemini":
            await gemini.run_tool_loop(
                raw_client=self.client,
                model_name=self.model_name,
                messages=messages,
                override_tools=self.discovery_tools,
                enable_google_search=True,
                max_tool_steps=3
            )
        elif self.provider == "anthropic":
            await anthropic.run_tool_loop(
                raw_client=self.client,
                model_name=self.model_name,
                messages=messages,
                override_tools=self.discovery_tools,
                enable_web_search=True,
                max_tool_steps=3
            )
        else:
            # Default OpenAI handler - use raw client (client.client) since Instructor-wrapped
            # clients intercept chat.completions.create and expect response_model
            await openai.run_tool_loop(
                raw_client=self.client.client,
                model_name=self.model_name,
                messages=messages,
                override_tools=self.discovery_tools,
                enable_web_search=True,
                max_tool_steps=3
            )

        # Walk backward to find the last assistant/model message with meaningful text.
        # Tool messages and the initial user theme prompt are ignored so a stalled
        # tool loop cannot return the original input as the "result".
        for msg in reversed(messages):
            if isinstance(msg, dict):
                if msg.get("role") not in {"assistant", "model"}:
                    continue
                content = msg.get("content", "")
            elif getattr(msg, "role", None) in {"assistant", "model"}:
                content = " ".join(
                    part.text for part in getattr(msg, "parts", []) if getattr(part, "text", None)
                )
            else:
                continue
            if content and isinstance(content, str) and content.strip():
                return content

        # If no assistant text found, collect meaningful content from tool results
        tool_results = []
        for msg in messages:
            if isinstance(msg, dict) and msg.get("role") == "tool":
                content = msg.get("content", "")
                if content and isinstance(content, str) and content.strip():
                    # Skip "no stocks found", errors, and partial/incomplete results
                    lower_content = content.lower()
                    if "no stocks found" not in lower_content and "error" not in lower_content:
                        # Only include results that look like actual stock screening output
                        if "stock screening results" in lower_content or content.startswith("$"):
                            tool_results.append(content)

        if tool_results:
            return "Stock Screening Results:\n" + "\n---\n".join(tool_results)

        return "No assets discovered."

    async def close(self):
        """Closes the underlying LLM client."""
        await clients.close_client(self.client, self.provider)
