"""Portfolio management tools for ledger XML, position PnL, buy/sell calculations, and system portfolios."""

from core.config import logger
from tools._compat import MarketDataManager, get_supabase_client


async def execute_position_pnl_tool(ticker: str, owner_id: str) -> str:
    """Fetches current position P&L for the specific owner."""
    client = get_supabase_client()
    try:
        ticker = ticker.upper()
        res = client.table("position_pnl").select("*").eq("ticker", ticker).eq("owner_id", owner_id).execute()

        if not res.data:
            return f"You do not currently own a position in {ticker}."

        pos = res.data[0]
        return (
            f"Position for {ticker}:\n"
            f"- Quantity: {pos['quantity']}\n"
            f"- Avg Cost Basis: ${float(pos['average_cost_basis']):.2f}\n"
            f"- Current Price: ${float(pos['current_price']):.2f}\n"
            f"- Unrealized P&L: ${float(pos['unrealized_pnl_usd']):,.2f} ({float(pos['unrealized_pnl_pct']):.2f}%)"
        )
    except Exception as e:
        return f"Error fetching position P&L for {ticker}: {str(e)}"


async def execute_buy_quantity_tool(ticker: str, owner_id: str, percentage: int) -> str:
    """Calculates buy quantity with 10% equity floor enforcement."""
    from execution.portfolio import Portfolio

    ticker = ticker.upper()
    portfolio = Portfolio(owner_id)
    await portfolio.initialize()

    manager = MarketDataManager()
    try:
        quote = await manager.get_quote(ticker)
        if not quote or not quote.exists:
            return f"Error: Ticker '{ticker}' not found."

        price = quote.price

        current_prices = {t: p.average_cost_basis for t, p in portfolio.positions.items()}
        current_prices[ticker] = price

        metrics = portfolio.calculate_reg_t_metrics(current_prices)

        equity_floor_usd = metrics.total_equity * 0.10

        target_value_usd = metrics.buying_power * (percentage / 100.0)

        final_target_usd = target_value_usd
        compliance_note = ""

        if target_value_usd < equity_floor_usd:
            final_target_usd = equity_floor_usd
            compliance_note = (
                f"\nNOTE: Your requested {percentage}% allocation (${target_value_usd:,.2f}) was below the "
                f"10% Total Equity Floor (${equity_floor_usd:,.2f}). This tool has automatically "
                f"upsized your request to meet the minimum required position size."
            )

        if final_target_usd > metrics.buying_power:
            final_target_usd = metrics.buying_power
            compliance_note += f"\nWARNING: Insufficient Buying Power to meet the preferred allocation. Capped at ${metrics.buying_power:,.2f}."

        quantity = int(final_target_usd / price)

        if quantity == 0 and final_target_usd > 0:
            quantity = 1

        actual_cost = quantity * price

        status = "COMPLIANT ✅" if actual_cost >= equity_floor_usd else "INSUFFICIENT FUNDS ❌"

        return (
            f"BUY CALCULATION COMPLETE for {ticker}:\n"
            f"- Current Price: ${price:.2f}\n"
            f"- Total Buying Power: ${metrics.buying_power:,.2f}\n"
            f"- 10% Total Equity Floor: ${equity_floor_usd:,.2f}\n"
            f"- Recommended BUY Quantity: {quantity} shares (Est. Cost: ${actual_cost:,.2f})\n"
            f"- Status: {status}{compliance_note}\n\n"
            f"MANDATORY ACTION: Set your decision to 'BUY' for ticker '{ticker}' with quantity: {quantity}. "
            f"You MUST include 'buy_tool_called': true in your final JSON decision."
        )
    except Exception as e:
        return f"Error calculating buy quantity for {ticker}: {str(e)}"


async def execute_sell_quantity_tool(ticker: str, owner_id: str, percentage: int) -> str:
    """Calculates sell quantity with 10% equity 'dust' check."""
    from execution.portfolio import Portfolio

    client = get_supabase_client()

    ticker = ticker.upper()
    portfolio = Portfolio(owner_id)
    await portfolio.initialize()

    MarketDataManager()

    try:
        res = client.table("position_pnl").select("*").eq("ticker", ticker).eq("owner_id", owner_id).execute()

        if not res.data:
            return f"Error: You do not currently own a position in {ticker}."

        pos_data = res.data[0]
        total_shares = int(pos_data["quantity"])
        price = float(pos_data["current_price"])

        current_prices = {t: p.average_cost_basis for t, p in portfolio.positions.items()}
        current_prices[ticker] = price
        metrics = portfolio.calculate_reg_t_metrics(current_prices)
        equity_floor_usd = metrics.total_equity * 0.10

        sell_shares = int(total_shares * (percentage / 100.0))
        remaining_shares = total_shares - sell_shares
        remaining_value = remaining_shares * price

        compliance_note = ""
        if remaining_shares > 0 and remaining_value < equity_floor_usd:
            sell_shares = total_shares
            remaining_shares = 0
            compliance_note = (
                f"\nWARNING: Selling {percentage}% would leave a position worth ${remaining_value:,.2f}, "
                f"which is below your 10% Equity Floor (${equity_floor_usd:,.2f}). "
                f"To prevent 'dust' positions, this tool has mandated a 100% (FULL) sell."
            )

        if sell_shares == 0 and percentage > 0:
            sell_shares = 1

        sell_shares = min(sell_shares, total_shares)

        return (
            f"SELL CALCULATION COMPLETE for {ticker}:\n"
            f"- Current Holdings: {total_shares} shares\n"
            f"- Recommended SELL Quantity: {sell_shares} shares\n"
            f"- Remaining Position: {remaining_shares} shares{compliance_note}\n\n"
            f"MANDATORY ACTION: Set your decision to 'SELL' for ticker '{ticker}' with quantity: {sell_shares}. "
            f"You MUST include 'sell_tool_called': true in your final JSON decision."
        )

    except Exception as e:
        return f"Error calculating sell quantity for {ticker}: {str(e)}"


async def execute_get_portfolio_ledger_tool(owner_id: str) -> str:
    """Retrieves current cash, total equity, buying power (SMA), active positions, and recent trade thesis history."""
    try:
        client = get_supabase_client()

        # 1. Fetch general portfolio details
        p_res = client.table("portfolios").select("*").eq("owner_id", owner_id).execute()
        if not p_res.data:
            return f"No portfolio ledger found for owner: {owner_id}"

        p_data = p_res.data[0]
        cash = float(p_data.get("cash_balance", 0.0))
        sma = float(p_data.get("sma", 0.0))
        buying_power = float(p_data.get("buying_power", 0.0))
        total_equity = float(p_data.get("total_equity", 0.0))

        # 2. Fetch positions and PnL
        pos_res = client.table("position_pnl").select("*").eq("owner_id", owner_id).execute()
        positions_str = ""
        if pos_res.data:
            positions_str = "\nStock Holdings:\n"
            for pos in pos_res.data:
                qty = pos.get("quantity", 0)
                if float(qty) <= 0:
                    continue
                ticker = pos["ticker"]
                avg_cost = float(pos.get("average_cost_basis", 0.0))
                curr_price = float(pos.get("current_price", 0.0))
                pnl_usd = float(pos.get("unrealized_pnl_usd", 0.0))
                pnl_pct = float(pos.get("unrealized_pnl_pct", 0.0))
                positions_str += (
                    f"- {ticker}: {qty} shares | Avg Cost: ${avg_cost:.2f} | "
                    f"Current Price: ${curr_price:.2f} | Unrealized PnL: ${pnl_usd:+,.2f} ({pnl_pct:+.2f}%)\n"
                )
        else:
            positions_str = "\nStock Holdings: None (you have no active stock positions)\n"

        # 3. Fetch thesis history / ledger XML
        from attribution.service import get_active_ledger_xml

        ledger_xml = await get_active_ledger_xml(client, owner_id)
        ledger_str = f"\n{ledger_xml}" if ledger_xml else ""

        return (
            f"=== PORTFOLIO LEDGER ===\n"
            f"Account Owner: {owner_id}\n"
            f"Total Account Equity: ${total_equity:,.2f}\n"
            f"Cash Balance: ${cash:,.2f}\n"
            f"Buying Power (SMA): ${buying_power:,.2f}\n"
            f"SMA High Water Mark: ${sma:,.2f}\n"
            f"{positions_str}"
            f"{ledger_str}"
        )
    except Exception as e:
        logger.exception(f"Error in execute_get_portfolio_ledger_tool: {e}")
        return f"Error retrieving portfolio ledger: {str(e)}"


async def execute_get_system_portfolios_tool(
    category: str = "all",
    include_positions: bool = True,
    lookback_days: int = 7,
) -> str:
    """Executes the get_system_portfolios tool."""
    from analytics.system_portfolios_report import (
        execute_get_system_portfolios_tool as _sys_port_report,
    )

    return await _sys_port_report(
        category=category,
        include_positions=include_positions,
        lookback_days=lookback_days,
    )
