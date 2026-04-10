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

        result = self._extract_final_response(messages)
        
        if not result or len(result.strip()) < 50:
            logger.warning("DiscoveryAgent: Empty response, trying tool results fallback")
            result = self._collect_tool_results_fallback(messages)
        
        validated = self._validate_and_enhance_result(result)
        return validated

    def _collect_tool_results_fallback(self, messages: list) -> str:
        """Collect meaningful content from tool results as fallback."""
        tool_results = []
        for msg in messages:
            if isinstance(msg, dict) and msg.get("role") == "tool":
                content = msg.get("content", "")
                if content and isinstance(content, str) and content.strip():
                    lower_content = content.lower()
                    if "no stocks found" not in lower_content and "error" not in lower_content:
                        if "stock screening results" in lower_content or content.startswith("$"):
                            tool_results.append(content)

        if tool_results:
            return "Stock Screening Results:\n" + "\n---\n".join(tool_results)
        return ""

    def _extract_final_response(self, messages: list) -> str:
        """Walk backward to find the last assistant/model message with meaningful text.
        
        Tool messages and the initial user theme prompt are ignored so a stalled
        tool loop cannot return the original input as the "result".
        """
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

        return ""

    def _validate_5_whys(self, content: str) -> tuple[bool, list[str]]:
        """Validate that all 5 Whys questions are answered in the output.
        
        Returns:
            Tuple of (is_valid, list of missing questions)
        """
        required_patterns = [
            r"1\.\s*\*\*Why\*\*.*?is this theme market-moving",
            r"2\.\s*\*\*Why\*\*.*?will these specific assets benefit",
            r"3\.\s*\*\*Why\*\*.*?not already priced in",
            r"4\.\s*\*\*Why\*\*.*?most efficient way to profit",
            r"5\.\s*\*\*Why\*\*.*?best beneficiary",
        ]
        
        import re
        missing = []
        for i, pattern in enumerate(required_patterns, 1):
            if not re.search(pattern, content, re.IGNORECASE | re.DOTALL):
                missing.append(f"Why #{i}")
        
        return len(missing) == 0, missing

    def _validate_and_enhance_result(self, result: str) -> str:
        """Validate result has 5 Whys and adequate content, improve if needed."""
        
        if not result or len(result.strip()) < 50:
            logger.warning("DiscoveryAgent: Empty result after fallback")
            return "Insufficient analysis produced. Please retry with more specific theme."

        is_valid, missing = self._validate_5_whys(result)
        
        if is_valid:
            logger.info(f"DiscoveryAgent: 5 Whys validated successfully")
            return result
        
        logger.warning(f"DiscoveryAgent: Missing 5 Whys sections: {missing}")
        
        if len(result.strip()) < 200:
            logger.warning("DiscoveryAgent: Result too short, adding enhancement note")
            result += f"\n\n**Note:** This analysis is incomplete. Missing: {', '.join(missing)}"
        
        return result

    async def close(self):
        """Closes the underlying LLM client."""
        await clients.close_client(self.client, self.provider)
