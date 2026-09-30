"""Earnings and company peer analysis tools: earnings history, revisions, sector alternatives, and PEAD."""

from core.config import logger
from tools._compat import MarketDataManager, get_embedding, get_supabase_client


async def execute_sector_alternatives_tool(ticker: str) -> str:
    """Identifies sector alternatives for a ticker using FMP industry screener, correlation matrix, and decision history."""
    client = get_supabase_client()
    ticker = ticker.upper()

    industry_competitors = []
    correlated_plays = []
    historical_plays = []

    # 1. Fetch Company Profile & Screen Stocks from FMP
    manager = MarketDataManager()
    sector = None
    industry = None
    try:
        profiles = await manager.get_company_profile(ticker)
        if profiles and isinstance(profiles, list):
            profile = profiles[0]
            sector = profile.get("sector")
            industry = profile.get("industry")

        if sector or industry:
            screen_results = await manager.screen_stocks(sector=sector, industry=industry, limit=5)
            if screen_results:
                for item in screen_results:
                    sym = item.get("symbol")
                    if sym and sym != ticker:
                        name = item.get("companyName", "")
                        price = item.get("price", 0.0)
                        mcap = item.get("marketCap", 0.0)
                        mcap_str = f"${mcap / 1e9:.2f}B" if mcap else "unknown"
                        industry_competitors.append(f"{sym} ({name}) - Price: ${price:.2f}, Market Cap: {mcap_str}")
    except Exception as e:
        logger.warning(f"Error fetching company profile/screening for sector alternatives: {e}")

    # 2. Fetch Statistical Correlations from Database
    try:
        runs = client.table("correlation_runs").select("id").order("run_date", desc=True).limit(1).execute()
        if runs.data:
            run_id = runs.data[0]["id"]
            res_a = client.table("correlation_data").select("*").eq("run_id", run_id).eq("ticker_a", ticker).execute()
            res_b = client.table("correlation_data").select("*").eq("run_id", run_id).eq("ticker_b", ticker).execute()

            corr_rows = (res_a.data or []) + (res_b.data or [])

            filtered_corrs = []
            for row in corr_rows:
                corr = row.get("pearson_corr")
                if corr is not None and corr >= 0.40:
                    other_ticker = row.get("ticker_b") if row.get("ticker_a") == ticker else row.get("ticker_a")
                    ret_other = row.get("returns_b_90d") if row.get("ticker_a") == ticker else row.get("returns_a_90d")
                    ret_other_val = f"{ret_other:.2f}%" if ret_other is not None else "N/A"
                    filtered_corrs.append({"ticker": other_ticker, "corr": corr, "ret": ret_other_val})

            filtered_corrs.sort(key=lambda x: x["corr"], reverse=True)
            for c in filtered_corrs[:5]:
                correlated_plays.append(f"{c['ticker']} (Correlation: {c['corr']:.4f} | 90d Return: {c['ret']})")
    except Exception as e:
        logger.warning(f"Error fetching correlation data for sector alternatives: {e}")

    # 3. Vector Search on Past Decisions
    try:
        query_text = f"Market analysis and trading decision for {ticker} stock in this sector"
        embedding = get_embedding(query_text)
        if embedding:
            res = client.rpc(
                "match_decisions",
                {
                    "query_embedding": embedding,
                    "match_threshold": 0.5,
                    "match_count": 10,
                },
            ).execute()
            if res.data:
                related_tickers_set = set()
                for item in res.data:
                    t = item.get("ticker")
                    if t and t != ticker:
                        related_tickers_set.add(t)
                historical_plays = list(related_tickers_set)[:5]
    except Exception as e:
        logger.warning(f"Error fetching decision history vector search: {e}")

    # Aggregating results
    output = f"Sector Alternatives & Related Plays for {ticker}:\n\n"
    has_results = False

    if sector or industry:
        output += f"1. Industry Competitors (Sector: {sector or 'Unknown'}, Industry: {industry or 'Unknown'}):\n"
        if industry_competitors:
            for item in industry_competitors:
                output += f"   - {item}\n"
            has_results = True
        else:
            output += "   - No other liquid stocks found in this industry.\n"
        output += "\n"

    if correlated_plays:
        output += "2. Highly Correlated Assets (90d Pearson Correlation >= 0.40):\n"
        for item in correlated_plays:
            output += f"   - {item}\n"
        output += "\n"
        has_results = True

    if historical_plays:
        output += "3. Historical Related Plays (From past agent decisions):\n"
        output += f"   - {', '.join(historical_plays)}\n"
        output += "\n"
        has_results = True

    if not has_results:
        try:
            mem_res = client.table("memories").select("content").ilike("content", f"%{ticker}%").limit(5).execute()
            if mem_res.data:
                return (
                    f"No direct competitors or correlated assets found for {ticker}, but "
                    f"the ticker appears in recent market events. Consider searching for standard competitors manually."
                )
        except Exception:
            pass
        return f"No alternative plays or correlated assets found for {ticker}."

    return output.strip()


async def execute_search_related_tickers_tool(theme: str) -> str:
    """Uses LLM to search for tickers related to a theme."""
    import asyncio

    from core.config import GEMINI_MODEL
    from core.llm.clients import get_gemini_client
    from core.llm.prompt_factory import PromptFactory
    from core.models import TickerSuggestion

    client = get_gemini_client()
    try:
        messages = PromptFactory.build_ticker_suggestion_messages(provider="gemini", event_summary=theme)

        resp = client.chat.completions.create(model=GEMINI_MODEL, response_model=TickerSuggestion, messages=messages)
        if asyncio.iscoroutine(resp):
            resp = await resp

        return f"Suggested Tickers for '{theme}': {', '.join(resp.tickers)}\nReasoning: {resp.reasoning}"
    except Exception as e:
        return f"Error suggesting tickers for '{theme}': {str(e)}"


async def execute_earnings_history_tool(ticker: str, limit: int = 8) -> str:
    """Fetches earnings history and upcoming calendar info for a ticker."""
    manager = MarketDataManager()
    try:
        data = await manager.get_earnings_history(ticker, limit)
        if not data:
            return f"No earnings history or upcoming reports found for {ticker}."

        output = f"Earnings History and Calendar for {ticker.upper()}:\n"

        upcoming = [e for e in data if e.get("isUpcoming")]
        past = [e for e in data if not e.get("isUpcoming")]

        if upcoming:
            output += "\n--- Upcoming Earnings Announcement ---\n"
            for entry in upcoming:
                est_eps = f"${entry['epsEstimated']:.2f}" if entry.get("epsEstimated") is not None else "N/A"
                est_rev = (
                    f"${entry['revenueEstimated'] / 1e9:.2f}B" if entry.get("revenueEstimated") is not None else "N/A"
                )
                output += f"- Date: {entry['date']} | Estimated EPS: {est_eps} | Estimated Revenue: {est_rev}\n"

        if past:
            output += "\n--- Historical Earnings Reports (Recent first) ---\n"
            for entry in past:
                act_eps = f"${entry['epsActual']:.2f}" if entry.get("epsActual") is not None else "N/A"
                est_eps = f"${entry['epsEstimated']:.2f}" if entry.get("epsEstimated") is not None else "N/A"
                act_rev = f"${entry['revenueActual'] / 1e9:.2f}B" if entry.get("revenueActual") is not None else "N/A"
                est_rev = (
                    f"${entry['revenueEstimated'] / 1e9:.2f}B" if entry.get("revenueEstimated") is not None else "N/A"
                )

                surprise = entry.get("surprisePct")
                surprise_str = f"{surprise:+.2f}%" if surprise is not None else "N/A"

                output += f"- Date: {entry['date']}\n"
                output += f"  * EPS: Actual {act_eps} vs Estimate {est_eps} (Surprise: {surprise_str})\n"
                output += f"  * Revenue: Actual {act_rev} vs Estimate {est_rev}\n"

        return output
    except Exception as e:
        logger.exception(f"Error executing get_earnings_history tool for {ticker}")
        return f"Error retrieving earnings history for {ticker}: {str(e)}"


async def execute_pead_candidates_tool(sector: str | None = None, min_sue: float = 2.0, limit: int = 15) -> str:
    """Execute get_pead_candidates tool."""
    try:
        from tools.earnings_alpha_tools import handle_get_pead_candidates

        return await handle_get_pead_candidates({"sector": sector, "min_sue": min_sue, "limit": limit})
    except Exception as e:
        logger.exception("Error executing get_pead_candidates tool")
        return f"Error retrieving PEAD candidates: {str(e)}"


async def execute_earnings_revisions_tool(ticker: str) -> str:
    """Execute get_earnings_revisions tool."""
    try:
        from tools.earnings_alpha_tools import handle_get_earnings_revisions

        return await handle_get_earnings_revisions({"ticker": ticker})
    except Exception as e:
        logger.exception(f"Error executing get_earnings_revisions tool for {ticker}")
        return f"Error retrieving earnings revisions for {ticker}: {str(e)}"


async def execute_sector_bellwethers_tool(sector: str) -> str:
    """Execute get_sector_bellwethers tool."""
    try:
        from tools.earnings_alpha_tools import handle_get_sector_bellwethers

        return await handle_get_sector_bellwethers({"sector": sector})
    except Exception as e:
        logger.exception(f"Error executing get_sector_bellwethers tool for {sector}")
        return f"Error retrieving sector bellwethers for {sector}: {str(e)}"
