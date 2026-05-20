"""Asset Discovery Service.

This module uses specialized agents to identify market themes and
discover actual companies and ETFs related to those themes.
"""

import logging

from analysis.discovery_agent import DiscoveryAgent
from core.config import OPENAI_MODEL

logger = logging.getLogger("engine")


class DiscoveryService:
    """Service for discovering investment assets based on market events."""

    def __init__(self):
        self.agent = DiscoveryAgent(model_name=OPENAI_MODEL)

    async def discover_assets(self, event_content: str, event_summary: str | None = None) -> list[dict]:
        """Delegates asset discovery to a specialized Discovery Agent.

        The agent uses a single-call tool-calling approach to identify ~5 beneficiaries,
        run screens, and rank results based on the provided theme.
        """
        logger.info(f"Delegating asset discovery to DiscoveryAgent for: {event_content[:50]}...")

        try:
            assets = await self.agent.discover_assets(theme=event_content, context=event_summary)
            return assets

        except Exception as e:
            logger.error(f"Discovery Agent failed: {e}")
            return []

    async def close(self):
        """Cleanup resources."""
        if hasattr(self, "agent"):
            await self.agent.close()
