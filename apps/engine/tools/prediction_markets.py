import contextlib

import httpx

from tools._compat import get_supabase_client


async def execute_search_prediction_markets_tool(query: str, platform: str | None = None) -> str:
    """Search for active prediction markets in the database.

    Args:
        query: Keyword or search term.
        platform: Optional platform filter ('polymarket' or 'kalshi').

    Returns:
        Formatted string containing matching markets.
    """
    client = get_supabase_client()
    try:
        db_query = client.table("prediction_market_snapshots").select("*").eq("is_active", True)
        if platform:
            db_query = db_query.eq("platform", platform)

        # Use ilike for Postgres-side case-insensitive keyword search
        db_query = db_query.ilike("question", f"%{query}%")

        res = db_query.execute()

        if not res.data:
            return f"No active prediction markets found matching '{query}'."

        # Sort by volume descending
        sorted_markets = sorted(res.data, key=lambda x: x.get("volume_usd") or 0, reverse=True)

        output = f"Active Prediction Markets matching '{query}' (sorted by volume, highest first):\n\n"
        for i, market in enumerate(sorted_markets[:10], 1):
            yes_pct = float(market.get("yes_odds") or 0) * 100
            no_pct = float(market.get("no_odds") or 0) * 100
            volume = market.get("volume_usd") or 0

            output += (
                f"{i}. {market['question']} [{market['platform'].upper()} ID: {market['market_id']}]\n"
                f"   Category: {market['category']} | Volume: ${volume:,.2f}\n"
                f"   Current Odds: YES {yes_pct:.1f}% / NO {no_pct:.1f}%\n"
            )
            if market.get("ends_at"):
                output += f"   Ends At: {market['ends_at']}\n"
            output += "\n"

        return output.strip()
    except Exception as e:
        return f"Error searching prediction markets for '{query}': {str(e)}"


async def execute_get_prediction_market_odds_tool(market_id: str, platform: str) -> str:
    """Fetch real-time yes/no odds for a prediction market directly from the live API.

    Args:
        market_id: Unique market identifier or ticker.
        platform: 'polymarket' or 'kalshi'.

    Returns:
        Formatted string with real-time odds and details.
    """
    if platform.lower() == "polymarket":
        url = f"https://gamma-api.polymarket.com/markets/{market_id}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url)
                if resp.status_code == 404:
                    # Fallback to query param
                    resp = await client.get(f"https://gamma-api.polymarket.com/markets?id={market_id}")
                    resp.raise_for_status()
                    data_list = resp.json()
                    if not data_list:
                        return f"Polymarket market '{market_id}' not found."
                    market_data = data_list[0]
                else:
                    resp.raise_for_status()
                    market_data = resp.json()

            question = market_data.get("question") or "Unknown Question"
            volume = float(market_data.get("volume") or 0)

            # Polymarket prices represent cents/probability (e.g. 0.52 = 52%)
            yes_price = market_data.get("outcomePrices")
            yes_pct = 0.0
            if yes_price and isinstance(yes_price, list) and len(yes_price) > 0:
                with contextlib.suppress(ValueError, TypeError):
                    yes_pct = float(yes_price[0]) * 100
            no_pct = 100.0 - yes_pct

            output = (
                f"Polymarket Live Data:\n"
                f"- Question: {question}\n"
                f"- Market ID: {market_id}\n"
                f"- Category: {market_data.get('category', 'N/A')}\n"
                f"- Current Odds: YES {yes_pct:.1f}% / NO {no_pct:.1f}%\n"
                f"- Total Volume: ${volume:,.2f}\n"
            )
            if market_data.get("end_date_iso"):
                output += f"- Ends At: {market_data['end_date_iso']}\n"
            return output.strip()

        except Exception as e:
            return f"Error fetching live Polymarket odds for '{market_id}': {str(e)}"

    elif platform.lower() == "kalshi":
        url = f"https://external-api.kalshi.com/trade-api/v2/markets/{market_id}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                market_data = resp.json().get("market") or resp.json()

            question = market_data.get("title") or "Unknown Title"
            volume = float(market_data.get("volume", 0))

            # Kalshi yields yes/no prices in cents (e.g. 52 = 52%)
            yes_price = float(market_data.get("yes_bid") or market_data.get("last_price") or 0)
            no_price = float(market_data.get("no_bid") or (100 - yes_price) or 0)

            output = (
                f"Kalshi Live Data:\n"
                f"- Question: {question}\n"
                f"- Ticker: {market_id}\n"
                f"- Status: {market_data.get('status', 'N/A')}\n"
                f"- Current Odds: YES {yes_price:.1f}% / NO {no_price:.1f}%\n"
                f"- Volume: {volume:,.0f} contracts\n"
            )
            if market_data.get("expiration_time"):
                output += f"- Expiration: {market_data['expiration_time']}\n"
            return output.strip()

        except Exception as e:
            return f"Error fetching live Kalshi odds for '{market_id}': {str(e)}"

    else:
        return f"Unsupported prediction market platform: '{platform}'."
