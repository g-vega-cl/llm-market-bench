"""Asset Discovery Service.

This module uses specialized agents to identify market themes and 
discover actual companies and ETFs related to those themes.
"""

from typing import List, Optional
import logging
from core.config import OPENAI_MODEL
from analysis.discovery_agent import DiscoveryAgent

logger = logging.getLogger("engine")

class DiscoveryService:
    """Service for discovering investment assets based on market events."""

    def __init__(self):
        self.agent = DiscoveryAgent(model_name=OPENAI_MODEL)

    async def discover_assets(self, event_content: str, event_summary: Optional[str] = None) -> List[dict]:
        """Delegates asset discovery to a specialized Discovery Agent.
        
        The agent uses a reasoning loop (Tool-Calling) to identify beneficiaries,
        run screens, and rank results based on the provided theme.
        """
        logger.info(f"Delegating asset discovery to DiscoveryAgent for: {event_content[:50]}...")
        
        try:
            # The agent returns a structured string/analysis
            raw_findings = await self.agent.discover_assets(
                theme=event_content,
                context=event_summary
            )
            
            # Since the engine currently expects a List[dict] for its internal memory
            # and generic 'Investable Assets' display, we wrap the raw analysis.
            # In a future iteration, we could parse the agent's structured response
            # into individual RankedAsset objects if needed.
            
            # For now, we return a single "summary" asset that contains the full analysis
            # to preserve the agent's high-fidelity reasoning in the 'Investable Assets' section.
            return [{
                "ticker": "AGENT_DISCOVERY",
                "name": "Thematic Discovery Report",
                "reason": raw_findings
            }]

        except Exception as e:
            logger.error(f"Discovery Agent failed: {e}")
            return []

    async def close(self):
        """Cleanup resources."""
        if hasattr(self, 'agent'):
            await self.agent.close()
