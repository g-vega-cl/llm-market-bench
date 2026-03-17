"""Asset Discovery Service.

This module uses LLMs to identify market themes and FMP to discover 
actual companies and ETFs related to those themes.
"""

from typing import List, Optional
from core.config import logger, GEMINI_MODEL
from core.llm import get_gemini_client, prompts
from core.models import DiscoveryThemes
from execution.providers.fmp import FMPProvider

class DiscoveryService:
    """Service for discovering investment assets based on market events."""

    def __init__(self):
        self.fmp = FMPProvider()
        self.client = get_gemini_client()

    async def discover_assets(self, event_content: str) -> List[dict]:
        """Maps an event to specific tickers using LLM and FMP."""
        logger.info(f"Starting asset discovery for theme: {event_content[:50]}...")
        
        # 1. Map Theme to Discovery Categories
        try:
            prompt = prompts.DISCOVERY_PROMPT.format(event_content=event_content)
            resp = self.client.chat.completions.create(
                model=GEMINI_MODEL,
                response_model=DiscoveryThemes,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Handle potential async return from instructor/gemini client
            import asyncio
            if asyncio.iscoroutine(resp):
                resp = await resp
                
            logger.info(f"Discovery targets: sectors={resp.sectors}, industries={resp.industries}, keywords={resp.keywords}")
            
        except Exception as e:
            logger.error(f"Failed to identify discovery themes: {e}")
            return []

        discovered_tickers = []
        seen_tickers = set()

        # 2. Query FMP - Stock Screener (Sector/Industry)
        # We'll take the first few sectors/industries to avoid too many calls
        for sector in resp.sectors[:2]:
            stocks = await self.fmp.screen_stocks(sector=sector, limit=5)
            for s in stocks:
                ticker = s.get("symbol")
                if ticker and ticker not in seen_tickers:
                    discovered_tickers.append({
                        "ticker": ticker,
                        "name": s.get("companyName"),
                        "reason": f"Top liquid asset in {sector} sector"
                    })
                    seen_tickers.add(ticker)

        for industry in resp.industries[:2]:
            stocks = await self.fmp.screen_stocks(industry=industry, limit=5)
            for s in stocks:
                ticker = s.get("symbol")
                if ticker and ticker not in seen_tickers:
                    discovered_tickers.append({
                        "ticker": ticker,
                        "name": s.get("companyName"),
                        "reason": f"Top liquid asset in {industry} industry"
                    })
                    seen_tickers.add(ticker)

        # 3. Query FMP - Ticker Search (Keywords)
        for keyword in resp.keywords[:3]:
            results = await self.fmp.search_tickers(keyword, limit=3)
            for r in results:
                ticker = r.get("symbol")
                if ticker and ticker not in seen_tickers:
                    discovered_tickers.append({
                        "ticker": ticker,
                        "name": r.get("name"),
                        "reason": f"Relevant to '{keyword}' keyword"
                    })
                    seen_tickers.add(ticker)

        logger.info(f"Discovered {len(discovered_tickers)} assets.")
        return discovered_tickers[:10] # Cap at 10 for analysis
