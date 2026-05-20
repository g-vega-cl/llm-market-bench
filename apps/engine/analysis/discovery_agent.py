"""Specialized agent for discovering investable assets based on market themes."""

import contextlib
import json
import logging
import re

from core.config import GEMINI_MODEL
from core.llm import clients, prompts, tools
from core.llm.handlers import anthropic, gemini, openai

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
    return "openai"  # Default


class DiscoveryAgent:
    """Agent that uses reasoning and tools to find thematic stock beneficiaries."""

    def __init__(self, model_name: str = GEMINI_MODEL):
        self.model_name = model_name
        self.provider = get_provider_from_model(model_name)
        self.client = clients.CLIENT_FACTORIES[self.provider]()

        # Handlers translate canonical defs to provider-specific format internally.
        self.discovery_tools = [tools.RUN_STOCK_SCREENER_TOOL]

    async def discover_assets(self, theme: str, context: str | None = None) -> list[dict]:
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
            {"role": "user", "content": f"THEME: {theme}\n\nCONTEXT: {context or 'None'}"},
        ]

        if self.provider == "gemini":
            await gemini.run_tool_loop(
                raw_client=self.client,
                model_name=self.model_name,
                messages=messages,
                override_tools=self.discovery_tools,
                enable_google_search=True,
                max_tool_steps=3,
            )
        elif self.provider == "anthropic":
            await anthropic.run_tool_loop(
                raw_client=self.client,
                model_name=self.model_name,
                messages=messages,
                override_tools=self.discovery_tools,
                enable_web_search=True,
                max_tool_steps=3,
            )
        else:
            await openai.run_tool_loop(
                raw_client=self.client.client,
                model_name=self.model_name,
                messages=messages,
                override_tools=self.discovery_tools,
                enable_web_search=True,
                max_tool_steps=3,
            )

        final_text = self._extract_final_text(messages)

        if not final_text:
            messages.append({"role": "user", "content": "Please output your top 5 stock picks as a JSON array now."})
            await self._force_text_completion(messages)
            final_text = self._extract_final_text(messages)

        if not final_text:
            logger.warning("DiscoveryAgent: No text content in final response")
            return []

        assets = self._parse_json_response(final_text)

        if not assets:
            logger.warning("DiscoveryAgent: Failed to parse JSON from response")
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
                if isinstance(content, list):
                    content = " ".join(
                        block.get("text", "")
                        for block in content
                        if isinstance(block, dict) and block.get("type") == "text"
                    )
            elif getattr(msg, "role", None) in {"assistant", "model"}:
                content = " ".join(part.text for part in getattr(msg, "parts", []) if getattr(part, "text", None))
            else:
                continue
            if content and isinstance(content, str) and content.strip():
                return content
        return ""

    async def _force_text_completion(self, messages: list) -> None:
        """Force a text-only completion when tool loop produced no assistant text."""
        try:
            if self.provider in ("openai", "deepseek"):
                resp = await self.client.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                )
                if resp.choices and resp.choices[0].message:
                    messages.append(resp.choices[0].message.model_dump())
            elif self.provider == "gemini":
                from google import genai as google_genai

                contents = []
                system_instruction = None
                for m in messages:
                    if isinstance(m, google_genai.types.Content):
                        contents.append(m)
                    elif isinstance(m, dict) and m.get("role") == "system":
                        system_instruction = m.get("content")
                    elif isinstance(m, dict):
                        role = "model" if m.get("role") in ("assistant", "model") else "user"
                        parts = [{"text": m.get("content", "") or ""}]
                        contents.append({"role": role, "parts": parts})
                config = {}
                if system_instruction:
                    config["system_instruction"] = system_instruction
                resp = await self.client.client.aio.models.generate_content(
                    model=self.model_name,
                    contents=contents,
                    config=config,
                )
                if resp.candidates and resp.candidates[0].content:
                    messages.append(resp.candidates[0].content)
            elif self.provider == "anthropic":
                system = ""
                anthropic_msgs = []
                for m in messages:
                    if isinstance(m, dict):
                        if m.get("role") == "system":
                            system = m.get("content", "")
                        elif m.get("role") in ("assistant", "user"):
                            content = m.get("content", "")
                            if isinstance(content, list):
                                text = " ".join(
                                    b.get("text", "")
                                    for b in content
                                    if isinstance(b, dict) and b.get("type") == "text"
                                )
                                anthropic_msgs.append({"role": m["role"], "content": text})
                            elif isinstance(content, str):
                                anthropic_msgs.append({"role": m["role"], "content": content})
                resp = await self.client.client.messages.create(
                    model=self.model_name,
                    system=system,
                    messages=anthropic_msgs,
                    max_tokens=4096,
                )
                text_blocks = [b.text for b in resp.content if b.type == "text"]
                messages.append({"role": "assistant", "content": "\n".join(text_blocks)})
        except Exception as e:
            logger.warning(f"DiscoveryAgent: forced text completion failed: {e}")

    def _parse_json_response(self, text: str) -> list[dict]:
        """Extract and parse JSON from the response text."""
        json_match = None

        json_block_match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text, re.DOTALL)
        if json_block_match:
            try:
                parsed = json.loads(json_block_match.group(1))
                json_match = parsed
            except json.JSONDecodeError:
                pass

        if not json_match:
            json_array_match = re.search(r"\[[\s\S]*\]", text)
            if json_array_match:
                with contextlib.suppress(json.JSONDecodeError):
                    json_match = json.loads(json_array_match.group(0))

        if not json_match:
            json_obj_match = re.search(r"\{[\s\S]*\}", text)
            if json_obj_match:
                with contextlib.suppress(json.JSONDecodeError):
                    json_match = json.loads(json_obj_match.group(0))

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
                validated.append(
                    {
                        "ticker": str(asset.get("ticker", "")).upper(),
                        "name": asset.get("name", ""),
                        "reason": asset.get("reason", ""),
                    }
                )

        return validated

    async def close(self):
        """Closes the underlying LLM client."""
        await clients.close_client(self.client, self.provider)
