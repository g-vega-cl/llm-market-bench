"""Specialized agent for discovering investable assets based on market themes."""

import json
import logging
import re
from typing import List, Optional

from core.config import GEMINI_MODEL
from core.llm import clients, prompts, tools
from core.llm.handlers import gemini, openai, anthropic

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

    async def discover_assets(self, theme: str, context: Optional[str] = None) -> List[dict]:
        """Executes a single-call tool-calling mission to find ~5 assets for a given theme.
        
        Args:
            theme: The market theme or macro event (e.g., "AI infrastructure demand").
            context: Optional additional context or past events.
            
        Returns:
            A list of dicts with ticker, name, and reason keys.
        """
        logger.info(f"DiscoveryAgent starting mission for theme: {theme}")
        
        messages = [
            {"role": "system", "content": prompts.DISCOVERY_AGENT_SYSTEM_PROMPT},
            {"role": "user", "content": f"THEME: {theme}\n\nCONTEXT: {context or 'None'}"}
        ]

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
            await openai.run_tool_loop(
                raw_client=self.client.client,
                model_name=self.model_name,
                messages=messages,
                override_tools=self.discovery_tools,
                enable_web_search=True,
                max_tool_steps=3
            )

        final_text = self._extract_final_text(messages)
        
        if not final_text:
            logger.warning("DiscoveryAgent: No text content in final response")
            return []
        
        assets = self._parse_json_response(final_text)
        
        if not assets:
            logger.warning(f"DiscoveryAgent: Failed to parse JSON from response")
            return []
        
        logger.info(f"DiscoveryAgent: Successfully extracted {len(assets)} assets")
        return assets[:5]

    def _extract_final_text(self, messages: list) -> str:
        """Walk backward to find the last assistant/model message with meaningful text."""
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

    def _parse_json_response(self, text: str) -> List[dict]:
        """Extract and parse JSON from the response text."""
        json_match = None
        
        json_block_match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', text, re.DOTALL)
        if json_block_match:
            try:
                parsed = json.loads(json_block_match.group(1))
                json_match = parsed
            except json.JSONDecodeError:
                pass
        
        if not json_match:
            json_array_match = re.search(r'\[[\s\S]*\]', text)
            if json_array_match:
                try:
                    json_match = json.loads(json_array_match.group(0))
                except json.JSONDecodeError:
                    pass
        
        if not json_match:
            json_obj_match = re.search(r'\{[\s\S]*\}', text)
            if json_obj_match:
                try:
                    json_match = json.loads(json_obj_match.group(0))
                except json.JSONDecodeError:
                    pass
        
        if not json_match:
            logger.warning("DiscoveryAgent: No JSON found in response")
            return []
        
        if isinstance(json_match, dict) and "assets" in json_match:
            assets = json_match["assets"]
        elif isinstance(json_match, list):
            assets = json_match
        else:
            logger.warning("DiscoveryAgent: JSON does not contain assets array")
            return []
        
        validated = []
        for asset in assets:
            if isinstance(asset, dict) and "ticker" in asset:
                validated.append({
                    "ticker": str(asset.get("ticker", "")).upper(),
                    "name": asset.get("name", ""),
                    "reason": asset.get("reason", "")
                })
        
        return validated

    async def close(self):
        """Closes the underlying LLM client."""
        await clients.close_client(self.client, self.provider)
