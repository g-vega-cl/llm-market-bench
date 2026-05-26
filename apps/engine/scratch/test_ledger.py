import asyncio

from core.config import OPENAI_MODEL
from core.db import get_async_supabase_client


async def get_active_ledger_xml(sb_client, owner_id: str) -> str:
    # 1. Get portfolio
    p_res = await sb_client.table("portfolios").select("id").eq("owner_id", owner_id).execute()
    if not p_res.data:
        return ""
    portfolio_id = p_res.data[0]["id"]

    # 2. Get current holdings
    pos_res = (
        await sb_client.table("portfolio_positions")
        .select("ticker, quantity")
        .eq("portfolio_id", portfolio_id)
        .gt("quantity", 0)
        .execute()
    )
    holdings = pos_res.data or []
    if not holdings:
        return ""

    tickers = [h["ticker"] for h in holdings]

    # 3. Get recent executed decisions for these tickers
    dec_res = (
        await sb_client.table("decisions")
        .select("ticker, signal, reasoning, metadata, created_at")
        .eq("model_name", owner_id)
        .eq("status", "EXECUTED")
        .in_("ticker", tickers)
        .order("created_at", desc=True)
        .limit(50)
        .execute()
    )

    decisions_by_ticker = {}
    for d in dec_res.data or []:
        t = d["ticker"]
        if t not in decisions_by_ticker:
            decisions_by_ticker[t] = []
        decisions_by_ticker[t].append(d)

    xml_parts = ["<CURRENT_PORTFOLIO_LEDGER>"]
    for h in holdings:
        t = h["ticker"]
        qty = h["quantity"]
        xml_parts.append(f'  <POSITION ticker="{t}" current_quantity="{qty}">')
        decs = decisions_by_ticker.get(t, [])
        if not decs:
            xml_parts.append("    <HISTORY>No recorded reasoning found.</HISTORY>")
        else:
            decs.reverse()
            for d in decs:
                date_str = d["created_at"].split("T")[0]
                sig = d["signal"]
                reasoning = d["reasoning"] or ""
                metadata = d.get("metadata") or {}
                adv_plan = metadata.get("advance_planning_notes") or ""

                xml_parts.append(f'    <ACTION date="{date_str}" signal="{sig}">')
                if reasoning:
                    xml_parts.append(f"      <REASONING>{reasoning}</REASONING>")
                if adv_plan:
                    xml_parts.append(f"      <ADVANCE_PLANNING>{adv_plan}</ADVANCE_PLANNING>")
                xml_parts.append("    </ACTION>")
        xml_parts.append("  </POSITION>")
    xml_parts.append("</CURRENT_PORTFOLIO_LEDGER>")

    return "\n".join(xml_parts)


async def main():
    client = await get_async_supabase_client()
    xml = await get_active_ledger_xml(client, OPENAI_MODEL)
    print(xml)


if __name__ == "__main__":
    asyncio.run(main())
