"""News and historical memories tools: daily newsletter, memory retrieval, market feeling, and web search."""

import contextvars

from core.config import logger
from tools._compat import get_supabase_client

# Context variables for pull-based newsletter workflows
active_news_summaries = contextvars.ContextVar("active_news_summaries", default=None)
active_news_chunks = contextvars.ContextVar("active_news_chunks", default=None)


async def execute_fetch_daily_newsletter_tool(
    session: str = "latest",
    target_date: str | None = None,
    include_full_content: bool = True,
) -> str:
    """Retrieves the synthesized daily market newsletter from `generated_newsletters`.

    Args:
        session: 'open', 'close', or 'latest'.
        target_date: Optional YYYY-MM-DD string.
        include_full_content: Whether to include the full markdown content.

    Returns:
        Formatted string containing newsletter title, summary, bullets, and content.
    """
    try:
        client = get_supabase_client()
        query = client.table("generated_newsletters").select("*")
        if session in ("open", "close"):
            query = query.eq("session", session)
        if target_date:
            query = query.gte("created_at", f"{target_date}T00:00:00").lte("created_at", f"{target_date}T23:59:59")

        query = query.order("created_at", desc=True).limit(1)
        response = query.execute()

        record = None
        if response and hasattr(response, "data") and response.data:
            record = response.data[0]
        elif target_date:
            fallback_query = client.table("generated_newsletters").select("*")
            if session in ("open", "close"):
                fallback_query = fallback_query.eq("session", session)
            fallback_resp = fallback_query.order("created_at", desc=True).limit(1).execute()
            if fallback_resp and hasattr(fallback_resp, "data") and fallback_resp.data:
                record = fallback_resp.data[0]
                logger.warning(
                    f"No generated newsletter found for target date {target_date}; "
                    f"fell back to latest available ({record.get('created_at')})"
                )

        if not record:
            return (
                f"No generated daily newsletters found in database "
                f"(session: {session}, target_date: {target_date or 'latest'})."
            )

        title = record.get("title", "Daily Newsletter Briefing")
        summary = record.get("summary", "")
        bullet_points = record.get("bullet_points") or []
        bullets_text = "\n".join([f"- {bp}" for bp in bullet_points])
        formatted_time = record.get("formatted_time", "")
        sess = record.get("session", session)
        created_at = str(record.get("created_at", ""))

        lines = [
            "=== AI WALL STREET SYNTHESIZED DAILY NEWSLETTER ===",
            f"Title: {title}",
            f"Session: {sess.upper()} ({formatted_time}) | Published: {created_at}",
            f"Executive Summary: {summary}",
        ]
        if bullets_text:
            lines.append(f"Key Takeaways:\n{bullets_text}")

        if include_full_content:
            content = record.get("content", "")
            if content:
                lines.append(f"\nFull Briefing Content:\n{content}")

        lines.append("==================================================")
        return "\n".join(lines)

    except Exception as e:
        logger.exception(f"Error executing fetch_daily_newsletter tool: {e}")
        return f"Error fetching daily newsletter: {str(e)}"


async def execute_fetch_newsletter_content_tool(source_ids: list[str]) -> str:
    """Retrieves the full text content of newsletters by their source IDs from the database.

    Args:
        source_ids: A list of source_id strings.

    Returns:
        A formatted string with the full content of requested newsletters.
    """
    if not source_ids:
        return "No source IDs specified."

    try:
        client = get_supabase_client()
        response = (
            client.table("newsletter_snapshots")
            .select("source_id, content, sender, subject, date")
            .in_("source_id", source_ids)
            .execute()
        )

        if not response.data:
            return f"No newsletters found matching IDs: {source_ids}"

        output = []
        for item in response.data:
            output.append(
                f"=========================================\n"
                f"Source ID: {item.get('source_id')}\n"
                f"Sender: {item.get('sender', 'Unknown')}\n"
                f"Subject: {item.get('subject', 'No Subject')}\n"
                f"Date: {item.get('date', 'Unknown')}\n"
                f"-----------------------------------------\n"
                f"{item.get('content', '')}\n"
                f"========================================="
            )

        return "\n\n".join(output)

    except Exception as e:
        logger.exception(f"Error executing fetch_newsletter_content tool: {e}")
        return f"Error fetching newsletter content: {str(e)}"


async def execute_search_past_memories_tool(query: str, limit: int = 5, model_name: str | None = None) -> str:
    """Performs a semantic pgvector search against past memories and model trade decisions.

    Args:
        query: Semantic query text.
        limit: Max context snippets to return.
        model_name: Optional model name to filter trade decisions by.

    Returns:
        Formatted context string of vector search results.
    """
    if not query:
        return "No query specified."

    try:
        from memory.store import retrieve_context

        context = retrieve_context(query, model_name=model_name or "unknown_agent", limit=limit)
        if not context:
            return f"No relevant past memories or decisions found matching query: '{query}'."

        return context

    except Exception as e:
        logger.exception(f"Error executing search_past_memories tool: {e}")
        return f"Error performing historical RAG search: {str(e)}"


async def execute_get_thematic_flows_tool(limit: int = 5) -> str:
    """Fetch active THEMATIC_FLOW memories for LLM reasoning."""
    try:
        from memory.store import retrieve_thematic_flows

        context = retrieve_thematic_flows(limit=limit)
        if not context:
            return "No active thematic capital flows found."
        return context
    except Exception as e:
        logger.exception(f"Error executing get_thematic_flows tool: {e}")
        return f"Error retrieving thematic flows: {str(e)}"


async def execute_add_thematic_flow_tool(content: str, importance_score: int = 8, category: str | None = None) -> str:
    """Add a new THEMATIC_FLOW memory to Supabase."""
    if not content:
        return "Content cannot be empty."
    try:
        from memory.store import add_memory

        metadata = {"category": category} if category else {}
        memory_id = add_memory(
            content=content,
            memory_type="THEMATIC_FLOW",
            importance_score=importance_score,
            metadata=metadata,
            check_similarity=True,
        )
        if memory_id:
            return f"Successfully added thematic flow memory [ID: {memory_id}]."
        return "Thematic flow memory already exists (deduplicated)."
    except Exception as e:
        logger.exception(f"Error executing add_thematic_flow tool: {e}")
        return f"Error adding thematic flow memory: {str(e)}"


async def execute_get_todays_news_menu_tool() -> str:
    """Retrieves the pre-filtered summaries and subjects of today's newsletters."""
    try:
        summaries = active_news_summaries.get()
        chunks = active_news_chunks.get()

        if not chunks:
            return "No news chunks available for today."

        news_content_parts = []
        if summaries:
            for chunk in chunks:
                source_id = chunk["source_id"]
                summary_text = summaries.get(source_id, "No summary available.")
                sender = chunk.get("sender", "Unknown")
                subject = chunk.get("subject", "No Subject")
                news_content_parts.append(
                    f"- Source ID: {source_id}\n  Sender: {sender}\n  Subject: {subject}\n  Summary: {summary_text}"
                )
        else:
            for chunk in chunks:
                news_content_parts.append(
                    f"- Source ID: {chunk['source_id']}\n  Sender: {chunk.get('sender', 'Unknown')}\n  Subject: {chunk.get('subject', 'No Subject')}\n  (Full text available via fetch_newsletter_content)"
                )

        return "=== TODAY'S NEWSLETTER MENU ===\n" + "\n".join(news_content_parts)
    except Exception as e:
        logger.exception(f"Error in execute_get_todays_news_menu_tool: {e}")
        return f"Error retrieving newsletter menu: {str(e)}"


async def execute_get_market_feeling_tool() -> str:
    """Retrieves the latest generated market sentiment and feeling."""
    try:
        from analysis.market_feeling import get_latest_market_feeling

        feeling = await get_latest_market_feeling()
        if not feeling:
            return "No market feeling records found."

        lines = [
            "=== LATEST MARKET FEELING ===",
            f"Sentiment: {feeling.get('sentiment_label', 'Neutral')} {feeling.get('sentiment_emoji', '')}".strip(),
        ]
        if feeling.get("market_direction"):
            lines.append(f"Direction: {feeling['market_direction']}")
        if feeling.get("confidence_score") is not None:
            lines.append(f"Confidence: {feeling['confidence_score']}%")
        if feeling.get("why_explanation"):
            lines.append(f"Rationale: {feeling['why_explanation']}")
        elif feeling.get("feeling_text"):
            lines.append(f"Feelings: {feeling['feeling_text']}")
        if feeling.get("primary_concern"):
            lines.append(f"Primary Concern: {feeling['primary_concern']}")
        if feeling.get("secondary_concern"):
            lines.append(f"Secondary Concern: {feeling['secondary_concern']}")
        if feeling.get("news_summary"):
            lines.append(f"News Context: {feeling['news_summary']}")
        if feeling.get("causal_cues"):
            lines.append(f"Causal Cues: {feeling['causal_cues']}")
        if feeling.get("created_at"):
            lines.append(f"Timestamp: {feeling['created_at']}")

        return "\n".join(lines)
    except Exception as e:
        logger.exception(f"Error in execute_get_market_feeling_tool: {e}")
        return f"Error retrieving market feeling: {str(e)}"


async def execute_web_search_tool(query: str, max_results: int = 5) -> str:
    """Performs a live web search for financial news, market reports, and catalysts."""
    if not query or not query.strip():
        return "Error: Empty search query provided."

    query_str = query.strip()
    logger.info(f"Executing web_search tool for query: '{query_str}'")

    results = []

    # 1. Primary: DuckDuckGo HTML search
    try:
        import httpx
        from bs4 import BeautifulSoup

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.get(
                "https://html.duckduckgo.com/html/",
                params={"q": query_str},
                headers=headers,
            )

            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                result_blocks = soup.find_all("div", class_=lambda c: c and "result" in c)
                for block in result_blocks:
                    title_elem = block.find("a", class_=lambda c: c and "title" in c) or block.find(
                        "a", class_="result__url"
                    )
                    snippet_elem = block.find("div", class_=lambda c: c and "snippet" in c) or block.find(
                        "a", class_="result__snippet"
                    )
                    url_elem = block.find("a", class_=lambda c: c and "url" in c) or title_elem

                    if title_elem and snippet_elem:
                        title = title_elem.get_text(strip=True)
                        snippet = snippet_elem.get_text(strip=True)
                        href = url_elem.get("href", "") if url_elem else ""
                        if title and snippet:
                            results.append({"title": title, "snippet": snippet, "url": href})
                            if len(results) >= max_results:
                                break

    except Exception as e:
        logger.warning(f"DuckDuckGo web search encountered error: {e}")

    # 2. Fallback: FMP Stock News Search if ticker is present in query or general search had no hits
    if not results:
        try:
            import httpx

            from execution.providers.fmp import FMPProvider

            fmp = FMPProvider()
            if fmp.api_key:
                words = query_str.split()
                candidate_tickers = [
                    w.strip("$,.:;\"'()")
                    for w in words
                    if w.strip("$,.:;\"'()").isupper() and 1 <= len(w.strip("$,.:;\"'()")) <= 5
                ]
                ticker_to_search = candidate_tickers[0] if candidate_tickers else "LIN"
                async with httpx.AsyncClient(timeout=10.0) as client:
                    fmp_resp = await client.get(
                        "https://financialmodelingprep.com/api/v3/stock_news",
                        params={"tickers": ticker_to_search, "limit": max_results, "apikey": fmp.api_key},
                    )
                    if fmp_resp.status_code == 200:
                        news_items = fmp_resp.json()
                        if isinstance(news_items, list):
                            for item in news_items[:max_results]:
                                results.append(
                                    {
                                        "title": item.get("title", ""),
                                        "snippet": item.get("text", "")[:250] + "...",
                                        "url": item.get("url", ""),
                                    }
                                )
        except Exception as e:
            logger.warning(f"FMP news search fallback failed: {e}")

    if not results:
        return f"No relevant web search results found for '{query_str}'."

    lines = [f"=== WEB SEARCH RESULTS FOR '{query_str}' ==="]
    for i, r in enumerate(results, 1):
        url_part = f" ({r['url']})" if r.get("url") else ""
        lines.append(f"{i}. {r['title']}{url_part}\n   {r['snippet']}")

    return "\n\n".join(lines)
