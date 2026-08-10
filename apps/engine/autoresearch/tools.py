"""Database and context search tools for the Auto-Researcher meta-agent."""

import logging

logger = logging.getLogger("engine")


async def query_trade_postmortems(track_id: str = "track_default", limit: int = 10) -> str:
    """Fetch recent model trade decisions and verifier rejections for a track to audit performance.

    Args:
        track_id: Research track ID to audit.
        limit: Max decisions to retrieve.

    Returns:
        Formatted summary string of recent trade decisions and verifier feedback.
    """
    try:
        from core.db import get_async_supabase_client

        sb_client = await get_async_supabase_client()
        res = (
            await sb_client.table("decisions")
            .select("ticker, signal, reasoning, status, created_at")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )

        if not res or not hasattr(res, "data") or not res.data:
            return "No recent trade decisions found in database."

        lines = [f"=== RECENT TRADE DECISIONS AUDIT (Track: {track_id}) ==="]
        for row in res.data:
            ticker = row.get("ticker", "UNKNOWN")
            action = row.get("signal") or row.get("decision") or "HOLD"
            status = row.get("status") or row.get("verification_status") or "N/A"
            reasoning = (row.get("reasoning") or "")[:150]
            lines.append(f"- [{status}] {action} {ticker}: {reasoning}")

        return "\n".join(lines)

    except Exception as e:
        logger.exception("Error fetching trade postmortems for autoresearcher: %s", e)
        return f"Error fetching trade postmortems: {str(e)}"


async def search_wiki_concepts(query: str) -> str:
    """Search wiki concept documentation for trading strategy inspiration.

    Args:
        query: Concept keyword or query.

    Returns:
        Summary of relevant concept titles or guidance.
    """
    if not query:
        return "No query specified."

    try:
        from pathlib import Path

        wiki_dir = Path(__file__).parent.parent.parent / "wiki" / "concepts"
        if not wiki_dir.exists():
            return "Wiki concepts directory not found."

        matches = []
        query_lower = query.lower()
        for md_file in wiki_dir.glob("*.md"):
            content = md_file.read_text()
            if query_lower in content.lower() or query_lower in md_file.name.lower():
                matches.append(f"[[concepts/{md_file.stem}]]: {content[:200].strip()}...")

        if not matches:
            return f"No wiki concept matching '{query}' found."

        return "=== WIKI CONCEPTS MATCHES ===\n" + "\n".join(matches[:5])

    except Exception as e:
        logger.exception("Error searching wiki concepts: %s", e)
        return f"Error searching wiki concepts: {str(e)}"
