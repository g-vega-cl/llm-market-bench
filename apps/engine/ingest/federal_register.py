"""Federal Register policy rule and executive document fetcher."""

from typing import Any

import httpx

from core.config import logger
from ingest.government_fetchers import BROWSER_USER_AGENT, DEFAULT_TIMEOUT

FEDERAL_REGISTER_API_URL = "https://www.federalregister.gov/api/v1/documents.json"


async def fetch_federal_register_documents(limit: int = 10) -> list[dict[str, Any]]:
    """Fetch recent significant US Federal Register rules, notices, and presidential documents."""
    params = {
        "per_page": max(1, min(limit, 20)),
        "order": "newest",
        "conditions[significant]": "1",
    }
    headers = {"User-Agent": BROWSER_USER_AGENT, "Accept": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT, headers=headers) as client:
            resp = await client.get(FEDERAL_REGISTER_API_URL, params=params)
            if resp.status_code != 200:
                logger.warning("Federal Register API returned HTTP %s", resp.status_code)
                return []
            payload = resp.json()
            results = payload.get("results") or []
            if not isinstance(results, list):
                return []
            return [
                {
                    "document_number": doc.get("document_number"),
                    "title": doc.get("title") or "",
                    "type": doc.get("type") or "",
                    "publication_date": doc.get("publication_date") or "",
                    "agency_names": [
                        a.get("name", "") for a in (doc.get("agencies") or []) if isinstance(a, dict) and a.get("name")
                    ],
                    "abstract": (doc.get("abstract") or "")[:400],
                    "html_url": doc.get("html_url") or "",
                }
                for doc in results[:limit]
                if isinstance(doc, dict) and doc.get("title")
            ]
    except Exception:
        logger.exception("Failed to fetch Federal Register documents")
        return []
