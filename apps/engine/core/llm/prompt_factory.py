import logging
from typing import Dict, Any

from core.llm import prompts

logger = logging.getLogger("engine")

class PromptFactory:
    """Centralized factory for building LLM prompts.
    
    This class handles the assembly of system and user messages from base templates,
    applying provider-specific modifications (e.g., stripping web search instructions 
    for providers that don't support it, adjusting role structures).
    """

    @staticmethod
    def _strip_web_search_capabilities(text: str) -> str:
        """Removes web search specific instructions from the prompt templates."""
        if not text:
            return text
            
        # Strip from system prompt intro
        text = text.replace(
            "with access to real-time web search. Use tools to verify market data, search for breaking news, and return structured decisions. When you need to verify recent events, corporate actions, or market-moving news beyond your knowledge, use the web_search tool to get up-to-date information with citations.",
            ". Use tools to verify market data and return structured decisions."
        )
        
        # Strip from user prompt block
        search_block = (
            "WEB SEARCH CAPABILITY:\n"
            "- You have access to **real-time web search** via the `web_search` tool.\n"
            "- Use web search to: (1) verify breaking news mentioned in snippets, (2) check for corporate actions (earnings, splits, M&A), (3) confirm government policy announcements, (4) fact-check claims before trading.\n"
            "- When you use web search, cite the sources in your reasoning. The search results will include URLs and cited text.\n"
            "- Do NOT overuse web search - use it strategically when you need to verify time-sensitive information.\n\n"
        )
        if search_block in text:
             text = text.replace(search_block, "")
        else:
            # Fallback if there are minor whitespace differences
            import re
            text = re.sub(r"WEB SEARCH CAPABILITY:.*?- Do NOT overuse web search - use it strategically when you need to verify time-sensitive information\.\n*", "", text, flags=re.DOTALL)
            
        return text

    @classmethod
    def _build_messages(
        cls, 
        provider: str, 
        system_template: str, 
        user_template: str, 
        **kwargs
    ) -> list[Dict[str, Any]]:
        """Base method to construct message list.
        
        Handles generic provider adaptations like web search stripping.
        """
        # 1. Format templates
        # User content often contains dynamic data (snippets, portfolio)
        user_content = user_template.format(**kwargs) if kwargs else user_template
        
        # System content is static in our high-fidelity architecture and contains literal JSON braces.
        # str.format() would fail on these braces.
        system_content = system_template
        
        # Determine if web search should be stripped from the prompt.
        # By default, we strip it unless explicitly enabled and supported by the provider.
        enable_search = kwargs.get("enable_web_search", False)
        
        # Special case: Anthropic is our primary search provider.
        # Gemini now supports combined built-in and function tools when the
        # server-side invocation flag is enabled, so we only strip search
        # instructions when search is disabled.
        if not enable_search:
            user_content = cls._strip_web_search_capabilities(user_content)
            if system_content:
                system_content = cls._strip_web_search_capabilities(system_content)

        # 2. Build message list
        messages = []
        if system_content:
            messages.append({"role": "system", "content": system_content})
        
        messages.append({"role": "user", "content": user_content})
        
        return messages

    @classmethod
    def build_analysis_messages(
        cls,
        provider: str,
        enable_web_search: bool = False,
        market_data_block: str = "",
        owner_id: str = None,
        **kwargs
    ) -> list[Dict[str, Any]]:
        """Builds messages for the primary analysis loop.

        If owner_id is in the experiment group, loads the active prompt
        variant from the database. Otherwise, uses the hardcoded baseline
        prompt from prompts.py.
        """
        from core.config import AUTORESEARCH_EXPERIMENT_OWNER_IDS

        if owner_id and owner_id in AUTORESEARCH_EXPERIMENT_OWNER_IDS:
            from autoresearch.prompt_store import get_active_prompt

            active = get_active_prompt()
            system_prompt = active if active else prompts.CORE_ANALYSIS_SYSTEM_PROMPT
        else:
            system_prompt = prompts.CORE_ANALYSIS_SYSTEM_PROMPT

        kwargs["market_data_block"] = market_data_block
        return cls._build_messages(
            provider,
            system_prompt,
            prompts.ANALYSIS_USER_PROMPT_TEMPLATE,
            enable_web_search=enable_web_search,
            **kwargs
        )

    @classmethod
    def build_verifier_messages(
        cls,
        provider: str,
        **kwargs
    ) -> list[Dict[str, Any]]:
        """Builds messages for the verifier agent."""
        return cls._build_messages(
            provider,
            prompts.VERIFIER_SYSTEM_PROMPT,
            prompts.VERIFIER_USER_PROMPT_TEMPLATE,
            **kwargs
        )

    @classmethod
    def build_contrarian_messages(
        cls,
        provider: str,
        market_data_block: str = "",
        **kwargs
    ) -> list[Dict[str, Any]]:
        """Builds messages for the contrarian agent."""
        kwargs["market_data_block"] = market_data_block
        return cls._build_messages(
            provider,
            prompts.CONTRARIAN_SYSTEM_PROMPT,
            prompts.CONTRARIAN_USER_PROMPT_TEMPLATE,
            **kwargs
        )

    @classmethod
    def build_manager_messages(
        cls,
        provider: str,
        **kwargs
    ) -> list[Dict[str, Any]]:
        """Builds messages for the manager/post-analysis agent."""
        return cls._build_messages(
            provider,
            prompts.MANAGER_SYSTEM_PROMPT,
            prompts.MANAGER_USER_PROMPT_TEMPLATE,
            **kwargs
        )

    @classmethod
    def build_synthesis_messages(
        cls,
        provider: str,
        **kwargs
    ) -> list[Dict[str, Any]]:
        """Builds messages for synthesizing events."""
        return cls._build_messages(
            provider,
            prompts.SYNTHESIS_SYSTEM_PROMPT,
            prompts.SYNTHESIS_USER_PROMPT_TEMPLATE,
            **kwargs
        )

    @classmethod
    def build_relationship_messages(
        cls,
        provider: str,
        **kwargs
    ) -> list[Dict[str, Any]]:
        """Builds messages for determining relationships."""
        return cls._build_messages(
            provider,
            prompts.RELATIONSHIP_SYSTEM_PROMPT,
            prompts.RELATIONSHIP_USER_PROMPT_TEMPLATE,
            **kwargs
        )
        
    @classmethod
    def build_cause_effect_messages(
        cls,
        provider: str,
        **kwargs
    ) -> list[Dict[str, Any]]:
        """Builds messages for defining cause and effect."""
        return cls._build_messages(
            provider,
            prompts.CAUSE_AND_EFFECT_SYSTEM_PROMPT,
            prompts.CAUSE_AND_EFFECT_USER_PROMPT_TEMPLATE,
            **kwargs
        )

    @classmethod
    def build_discovery_messages(
        cls,
        provider: str,
        **kwargs
    ) -> list[Dict[str, Any]]:
        """Builds messages for discovery mapping. No system prompt."""
        return cls._build_messages(
            provider,
            "",
            prompts.DISCOVERY_PROMPT,
            **kwargs
        )

    @classmethod
    def build_asset_ranking_messages(
        cls,
        provider: str,
        **kwargs
    ) -> list[Dict[str, Any]]:
        """Builds messages for asset ranking. No system prompt."""
        return cls._build_messages(
            provider,
            "",
            prompts.ASSET_RANKING_PROMPT,
            **kwargs
        )

    @classmethod
    def build_ticker_suggestion_messages(
        cls,
        provider: str,
        **kwargs
    ) -> list[Dict[str, Any]]:
        """Builds messages for ticker suggestion. No system prompt."""
        return cls._build_messages(
            provider,
            "",
            prompts.TICKER_SUGGESTION_PROMPT,
            **kwargs
        )

    @classmethod
    def build_de_advertisement_messages(
        cls,
        provider: str,
        **kwargs
    ) -> list[Dict[str, Any]]:
        """Builds messages for de-advertisement module."""
        return cls._build_messages(
            provider,
            prompts.DE_ADVERTISEMENT_SYSTEM_PROMPT,
            prompts.DE_ADVERTISEMENT_USER_PROMPT_TEMPLATE,
            **kwargs
        )
