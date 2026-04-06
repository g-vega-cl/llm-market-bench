"""Asset Discovery Service.

This module uses LLMs to identify market themes and FMP to discover 
actual companies and ETFs related to those themes.
"""

from typing import List, Optional
import asyncio
from core.config import logger, GEMINI_MODEL, DEEPSEEK_MODEL
from core.llm import get_gemini_client, get_deepseek_client
from core.llm.prompt_factory import PromptFactory
from core.models import DiscoveryThemes, RankedAsset, DiscoveryRankingResponse
from execution.providers.fmp import FMPProvider

class DiscoveryService:
    """Service for discovering investment assets based on market events."""

    def __init__(self):
        self.fmp = FMPProvider()
        self.gemini_client = get_gemini_client()
        self.deepseek_client = get_deepseek_client()

    async def discover_assets(self, event_content: str, event_summary: Optional[str] = None) -> List[dict]:
        """Maps an event to specific tickers using multi-stage discovery and LLM re-ranking."""
        logger.info(f"Starting asset discovery for theme: {event_content[:50]}...")
        
        # 1. Map Theme to Discovery Categories (Gemini)
        try:
            messages = PromptFactory.build_discovery_messages(
                provider="gemini",
                event_content=event_content
            )
            resp = self.gemini_client.chat.completions.create(
                model=GEMINI_MODEL,
                response_model=DiscoveryThemes,
                messages=messages
            )
            
            if asyncio.iscoroutine(resp):
                resp = await resp
                
            logger.info(f"Discovery targets: sectors={resp.sectors}, industries={resp.industries}, market_cap_min={resp.market_cap_min}")
            
        except Exception as e:
            logger.error(f"Failed to identify discovery themes: {e}")
            return []

        candidate_pool = []
        seen_tickers = set()

        # 2. Expanded Candidate Retrieval (FMP)
        # We fetch more candidates than we need to allow for re-ranking
        tasks = []
        
        # Sector/Industry Screen
        for sector in resp.sectors[:2]:
            tasks.append(self.fmp.screen_stocks(
                sector=sector, 
                market_cap_min=resp.market_cap_min,
                limit=15
            ))
            
        for industry in resp.industries[:3]:
            tasks.append(self.fmp.screen_stocks(
                industry=industry, 
                market_cap_min=resp.market_cap_min,
                limit=15
            ))
            
        # Keyword Search
        for keyword in resp.keywords[:3]:
            tasks.append(self.fmp.search_tickers(keyword, limit=5))

        results = await asyncio.gather(*tasks)
        
        for r_list in results:
            for item in r_list:
                ticker = item.get("symbol")
                if ticker and ticker not in seen_tickers:
                    candidate_pool.append({
                        "ticker": ticker,
                        "name": item.get("companyName") or item.get("name"),
                        "industry": item.get("industry"),
                        "sector": item.get("sector")
                    })
                    seen_tickers.add(ticker)

        if not candidate_pool:
            logger.warning("No candidate assets found in FMP.")
            return []

        logger.info(f"Retrieved {len(candidate_pool)} candidates. Starting Deepseek re-ranking...")

        # 3. LLM Re-Ranking (Deepseek)
        try:
            # Format candidate pool for prompt
            pool_text = "\n".join([f"- {c['ticker']}: {c['name']} (Industry: {c['industry']})" for c in candidate_pool[:40]])
            
            messages = PromptFactory.build_asset_ranking_messages(
                provider="deepseek",
                event_content=event_content,
                event_summary=event_summary or "Detailed analysis of the event drivers and thematic impact.",
                candidate_pool=pool_text
            )
            
            ranked_resp = self.deepseek_client.chat.completions.create(
                model=DEEPSEEK_MODEL,
                response_model=DiscoveryRankingResponse,
                messages=messages
            )
            
            if asyncio.iscoroutine(ranked_resp):
                ranked_resp = await ranked_resp
                
            # Filter and convert to expected output format
            top_assets = []
            for asset in sorted(ranked_resp.ranked_assets, key=lambda x: x.relevance_score, reverse=True):
                if asset.relevance_score >= 40: # Quality threshold
                    top_assets.append({
                        "ticker": asset.ticker,
                        "name": asset.name,
                        "reason": f"[Score {asset.relevance_score}] {asset.reason}"
                    })

            logger.info(f"Re-ranking complete. Found {len(top_assets)} high-relevance assets.")
            return top_assets[:10]

        except Exception as e:
            logger.error(f"Failed to re-rank assets with Deepseek: {e}")
            # Fallback to basic list if ranking fails
            return [{"ticker": c["ticker"], "name": c["name"], "reason": "Thematic candidate (ranking failed)"} for c in candidate_pool[:10]]
