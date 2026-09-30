"""Valuation and fundamental analysis tools: key metrics, DCF audit, market barometer, and sector fundamentals."""

import contextlib

from core.config import logger
from tools._compat import MarketDataManager, get_supabase_client
from tools.earnings import (
    execute_search_related_tickers_tool as execute_search_related_tickers_tool,
)
from tools.earnings import (
    execute_sector_alternatives_tool as execute_sector_alternatives_tool,
)


async def execute_key_metrics_tool(ticker: str, period: str = "annual", limit: int = 2) -> str:
    """Fetches fundamental financial key metrics for a ticker to help analyze valuation/health."""
    manager = MarketDataManager()
    try:
        data = await manager.get_key_metrics(ticker, period, limit)

        if not data:
            return f"No fundamental key metrics found for {ticker}."

        # Fetch quote, estimates, and annual history to calculate Forward P/E and CAPE
        price = None
        forward_pe = None
        cape_val = None
        avg_eps = None
        eps_count = 0
        next_eps_est = None

        try:
            quote = await manager.get_quote(ticker)
            if quote and quote.exists:
                price = quote.price
        except Exception as e:
            logger.warning(f"Failed to fetch quote for new metrics calculation for {ticker}: {e}")

        # Helper to safely format decimal/float metrics
        def fmt(val, percentage=False):
            if val is None:
                return "N/A"
            if percentage:
                return f"{val * 100:.2f}%"
            return f"{val:.2f}"

        if price and price > 0:
            # Calculate Forward P/E
            try:
                estimates = await manager.get_analyst_estimates(ticker, period="annual", limit=5)
                if estimates and isinstance(estimates, list):
                    from datetime import datetime

                    now_year = datetime.now().year
                    for est in estimates:
                        est_date = est.get("date")
                        if est_date:
                            try:
                                est_year = int(est_date.split("-")[0])
                                if est_year >= now_year:
                                    next_eps_est = est.get("epsAvg")
                                    break
                            except ValueError:
                                pass
                    if next_eps_est is None and estimates:
                        next_eps_est = estimates[0].get("epsAvg")
                    if next_eps_est is not None:
                        try:
                            next_eps_est_val = float(next_eps_est)
                            if next_eps_est_val > 0:
                                forward_pe = price / next_eps_est_val
                        except (ValueError, TypeError):
                            pass
            except Exception as e:
                logger.warning(f"Failed to calculate Forward P/E for {ticker}: {e}")

            # Calculate CAPE (10-Yr Avg EPS)
            try:
                # Fetch up to 10 annual records
                annual_metrics = await manager.get_key_metrics(ticker, period="annual", limit=10)
                if annual_metrics:
                    eps_values = []
                    for yr_entry in annual_metrics:
                        val = yr_entry.get("netIncomePerShare")
                        if val is not None:
                            with contextlib.suppress(ValueError, TypeError):
                                eps_values.append(float(val))
                    if len(eps_values) >= 3:
                        avg_eps = sum(eps_values) / len(eps_values)
                        eps_count = len(eps_values)
                        if avg_eps > 0:
                            cape_val = price / avg_eps
            except Exception as e:
                logger.warning(f"Failed to calculate CAPE for {ticker}: {e}")

        output = f"Fundamental Key Metrics for {ticker} ({period.capitalize()} periods, recent first):\n"
        for i, entry in enumerate(data, 1):
            date_str = entry.get("date") or "N/A"
            period_str = entry.get("period") or "N/A"
            year_str = entry.get("calendarYear") or "N/A"

            output += f"\n--- Period {i}: {period_str} {year_str} (Date: {date_str}) ---\n"

            output += f"- P/E Ratio: {fmt(entry.get('peRatio'))}\n"
            output += f"- Price/Sales Ratio: {fmt(entry.get('priceToSalesRatio'))}\n"

            pb = entry.get("pbRatio")
            book_to_market = (1.0 / pb) if (pb is not None and pb != 0) else None
            output += f"- Price/Book Ratio: {fmt(pb)}\n"
            output += f"- Book-to-Market Ratio: {fmt(book_to_market)}\n"

            output += f"- EV/EBITDA: {fmt(entry.get('enterpriseValueOverEBITDA'))}\n"
            output += f"- Debt/Equity: {fmt(entry.get('debtToEquity'))}\n"
            output += f"- Current Ratio: {fmt(entry.get('currentRatio'))}\n"
            output += f"- ROE: {fmt(entry.get('roe'), percentage=True)}\n"
            output += f"- Dividend Yield: {fmt(entry.get('dividendYield'), percentage=True)}\n"
            output += f"- Free Cash Flow Yield: {fmt(entry.get('freeCashFlowYield'), percentage=True)}\n"
            if "priceToFreeCashFlowsRatio" in entry:
                output += f"- Price/Free Cash Flow Ratio: {fmt(entry.get('priceToFreeCashFlowsRatio'))}\n"
            output += f"- Book Value Per Share: ${fmt(entry.get('bookValuePerShare'))}\n"
            output += f"- Revenue Per Share: ${fmt(entry.get('revenuePerShare'))}\n"
            if "netIncomePerShare" in entry:
                output += f"- Net Income Per Share: ${fmt(entry.get('netIncomePerShare'))}\n"
            if "freeCashFlowPerShare" in entry:
                output += f"- Free Cash Flow Per Share: ${fmt(entry.get('freeCashFlowPerShare'))}\n"

        output += "\n--- Current Valuation Metrics (Derived) ---\n"
        if price and price > 0:
            output += f"- Current Stock Price: ${price:.2f}\n"
            if forward_pe is not None:
                output += f"- Forward P/E: {fmt(forward_pe)} (based on Next FY EPS Est. of ${fmt(next_eps_est)})\n"
            else:
                output += "- Forward P/E: N/A\n"
            if cape_val is not None:
                output += f"- CAPE ({eps_count}-Yr Avg EPS): {fmt(cape_val)} (Average EPS: ${fmt(avg_eps)})\n"
            else:
                output += "- CAPE (10-Yr Avg EPS): N/A\n"
        else:
            output += "- Current Stock Price: N/A\n"
            output += "- Forward P/E: N/A\n"
            output += "- CAPE (10-Yr Avg EPS): N/A\n"

        return output
    except Exception as e:
        return f"Error fetching key metrics for {ticker}: {str(e)}"


async def execute_market_health_barometer_tool(limit: int = 5) -> str:
    """Fetches S&P 500 aggregate valuation and earnings metrics from Supabase with historical variation & ERP."""
    try:
        client = get_supabase_client()
        # Query up to 30 snapshots for historical context and distribution statistics
        fetch_limit = max(limit, 30)
        res = client.table("market_barometer_history").select("*").order("date", desc=True).limit(fetch_limit).execute()

        if not res.data:
            return "No S&P 500 Market Health Barometer data found."

        all_snapshots = res.data
        latest_entry = all_snapshots[0]
        recent_snapshots = all_snapshots[:limit]

        # 1. Latest Forward Earnings Yield & Equity Risk Premium (ERP)
        fwd_pe = latest_entry.get("forward_pe")
        fwd_ey_str = "N/A"
        erp_str = "N/A"

        if fwd_pe is not None and float(fwd_pe) > 0:
            fwd_pe_val = float(fwd_pe)
            fwd_ey = 100.0 / fwd_pe_val
            fwd_ey_str = f"{fwd_ey:.2f}%"

            try:
                from core.fred import fetch_fred_series_observations

                t10_data = await fetch_fred_series_observations("treasury_10y", lookback_periods=1)
                latest_yield = None
                if t10_data and t10_data.get("latest_value") is not None:
                    latest_yield = float(t10_data["latest_value"])
                elif t10_data and t10_data.get("observations"):
                    obs = [o for o in t10_data["observations"] if o.get("value") is not None]
                    if obs:
                        latest_yield = float(obs[-1]["value"])

                if latest_yield is not None:
                    erp = fwd_ey - latest_yield
                    erp_str = f"{erp:+.2f}% (Forward Earnings Yield {fwd_ey:.2f}% minus 10Y Yield {latest_yield:.2f}%)"
                else:
                    erp_str = f"N/A (Forward Earnings Yield: {fwd_ey_str}, 10Y Yield unavailable)"
            except Exception as e:
                logger.debug(f"Could not compute ERP from FRED 10Y yield: {e}")
                erp_str = f"N/A (Forward Earnings Yield: {fwd_ey_str})"

        # 2. Historical Variation & Percentiles over available snapshots
        pe_vals = [float(e["pe_ratio"]) for e in all_snapshots if e.get("pe_ratio") is not None]
        fwd_vals = [float(e["forward_pe"]) for e in all_snapshots if e.get("forward_pe") is not None]

        valuation_context_lines = []
        if pe_vals:
            cur_pe = pe_vals[0]
            min_pe, max_pe = min(pe_vals), max(pe_vals)
            mean_pe = sum(pe_vals) / len(pe_vals)
            pe_rank = (sum(1 for v in pe_vals if v <= cur_pe) / len(pe_vals)) * 100.0
            pe_diff = ((cur_pe - mean_pe) / mean_pe * 100.0) if mean_pe > 0 else 0.0
            valuation_context_lines.append(
                f"- Trailing P/E: Range {min_pe:.2f} - {max_pe:.2f} (Mean: {mean_pe:.2f}) | {pe_rank:.0f}th percentile ({pe_diff:+.1f}% vs {len(all_snapshots)}d mean)"
            )

        if fwd_vals:
            cur_fwd = fwd_vals[0]
            min_fwd, max_fwd = min(fwd_vals), max(fwd_vals)
            mean_fwd = sum(fwd_vals) / len(fwd_vals)
            fwd_rank = (sum(1 for v in fwd_vals if v <= cur_fwd) / len(fwd_vals)) * 100.0
            fwd_diff = ((cur_fwd - mean_fwd) / mean_fwd * 100.0) if mean_fwd > 0 else 0.0
            valuation_context_lines.append(
                f"- Forward P/E:  Range {min_fwd:.2f} - {max_fwd:.2f} (Mean: {mean_fwd:.2f}) | {fwd_rank:.0f}th percentile ({fwd_diff:+.1f}% vs {len(all_snapshots)}d mean)"
            )

        output = f"S&P 500 Aggregate Market Health Barometer (Recent {len(recent_snapshots)} daily snapshots):\n"
        for idx, entry in enumerate(recent_snapshots):
            date_str = entry.get("date") or "N/A"
            pe = entry.get("pe_ratio")
            fwd_pe_entry = entry.get("forward_pe")
            pb = entry.get("pb_ratio")
            ps = entry.get("ps_ratio")
            pfcf = entry.get("pfcf_ratio")
            surprise = entry.get("earnings_surprise_momentum")

            pe_val = f"{float(pe):.2f}" if pe is not None else "N/A"
            fwd_pe_val = f"{float(fwd_pe_entry):.2f}" if fwd_pe_entry is not None else "N/A"
            pb_val = f"{float(pb):.2f}" if pb is not None else "N/A"
            ps_val = f"{float(ps):.2f}" if ps is not None else "N/A"
            pfcf_val = f"{float(pfcf):.2f}" if pfcf is not None else "N/A"
            surprise_val = f"{float(surprise):.1f}%" if surprise is not None else "N/A"

            output += f"\n- Date: {date_str}\n"
            output += f"  * Aggregate Trailing P/E: {pe_val}\n"
            output += f"  * Aggregate Forward P/E:  {fwd_pe_val}\n"
            if idx == 0:
                output += f"  * Forward Earnings Yield:   {fwd_ey_str}\n"
                output += f"  * Equity Risk Premium (ERP): {erp_str}\n"
            output += f"  * Aggregate P/S Ratio:   {ps_val}\n"
            output += f"  * Aggregate P/B Ratio:   {pb_val}\n"
            output += f"  * Aggregate Price/FCF:    {pfcf_val}\n"
            output += f"  * Earnings Beat Rate:     {surprise_val} of companies beating expectations\n"

        if valuation_context_lines:
            output += f"\n[ Historical Valuation Context ({len(all_snapshots)}-Day Snapshot Window) ]\n"
            output += "\n".join(valuation_context_lines) + "\n"

        return output
    except Exception as e:
        logger.exception("Error executing get_market_health_barometer tool")
        return f"Error retrieving barometer data: {str(e)}"


# Standard GICS sector string mapping to SPDR Sector ETFs
GICS_TO_SECTOR_ETF: dict[str, tuple[str, str]] = {
    "technology": ("XLK", "Technology"),
    "information technology": ("XLK", "Technology"),
    "financial services": ("XLF", "Financials"),
    "financials": ("XLF", "Financials"),
    "healthcare": ("XLV", "Healthcare"),
    "health care": ("XLV", "Healthcare"),
    "energy": ("XLE", "Energy"),
    "industrials": ("XLI", "Industrials"),
    "consumer cyclical": ("XLY", "Consumer Discretionary"),
    "consumer discretionary": ("XLY", "Consumer Discretionary"),
    "consumer defensive": ("XLP", "Consumer Staples"),
    "consumer staples": ("XLP", "Consumer Staples"),
    "utilities": ("XLU", "Utilities"),
    "real estate": ("XLRE", "Real Estate"),
    "basic materials": ("XLB", "Materials"),
    "materials": ("XLB", "Materials"),
    "communication services": ("XLC", "Communication Services"),
}

# Fallback constituent ticker mapping for top S&P 500 stocks
TICKER_TO_SECTOR_ETF: dict[str, tuple[str, str]] = {
    "AAPL": ("XLK", "Technology"),
    "MSFT": ("XLK", "Technology"),
    "NVDA": ("XLK", "Technology"),
    "AVGO": ("XLK", "Technology"),
    "ORCL": ("XLK", "Technology"),
    "ADBE": ("XLK", "Technology"),
    "CRM": ("XLK", "Technology"),
    "AMD": ("XLK", "Technology"),
    "QCOM": ("XLK", "Technology"),
    "TXN": ("XLK", "Technology"),
    "INTC": ("XLK", "Technology"),
    "AMAT": ("XLK", "Technology"),
    "NOW": ("XLK", "Technology"),
    "PANW": ("XLK", "Technology"),
    "LRCX": ("XLK", "Technology"),
    "KLAC": ("XLK", "Technology"),
    "ADI": ("XLK", "Technology"),
    "ANET": ("XLK", "Technology"),
    "CRWD": ("XLK", "Technology"),
    "PLTR": ("XLK", "Technology"),
    "JPM": ("XLF", "Financials"),
    "BRK.B": ("XLF", "Financials"),
    "V": ("XLF", "Financials"),
    "MA": ("XLF", "Financials"),
    "BAC": ("XLF", "Financials"),
    "WFC": ("XLF", "Financials"),
    "GS": ("XLF", "Financials"),
    "MS": ("XLF", "Financials"),
    "SPGI": ("XLF", "Financials"),
    "AXP": ("XLF", "Financials"),
    "PGR": ("XLF", "Financials"),
    "CB": ("XLF", "Financials"),
    "SCHW": ("XLF", "Financials"),
    "KKR": ("XLF", "Financials"),
    "MMC": ("XLF", "Financials"),
    "MCO": ("XLF", "Financials"),
    "LLY": ("XLV", "Healthcare"),
    "UNH": ("XLV", "Healthcare"),
    "JNJ": ("XLV", "Healthcare"),
    "ABBV": ("XLV", "Healthcare"),
    "MRK": ("XLV", "Healthcare"),
    "TMO": ("XLV", "Healthcare"),
    "ABT": ("XLV", "Healthcare"),
    "AMGN": ("XLV", "Healthcare"),
    "ISRG": ("XLV", "Healthcare"),
    "SYK": ("XLV", "Healthcare"),
    "REGN": ("XLV", "Healthcare"),
    "VRTX": ("XLV", "Healthcare"),
    "MDT": ("XLV", "Healthcare"),
    "PFE": ("XLV", "Healthcare"),
    "BSX": ("XLV", "Healthcare"),
    "HCA": ("XLV", "Healthcare"),
    "CI": ("XLV", "Healthcare"),
    "AMZN": ("XLY", "Consumer Discretionary"),
    "TSLA": ("XLY", "Consumer Discretionary"),
    "HD": ("XLY", "Consumer Discretionary"),
    "MCD": ("XLY", "Consumer Discretionary"),
    "NKE": ("XLY", "Consumer Discretionary"),
    "BKNG": ("XLY", "Consumer Discretionary"),
    "TJX": ("XLY", "Consumer Discretionary"),
    "ABNB": ("XLY", "Consumer Discretionary"),
    "GOOGL": ("XLC", "Communication Services"),
    "GOOG": ("XLC", "Communication Services"),
    "META": ("XLC", "Communication Services"),
    "NFLX": ("XLC", "Communication Services"),
    "DIS": ("XLC", "Communication Services"),
    "CMCSA": ("XLC", "Communication Services"),
    "VZ": ("XLC", "Communication Services"),
    "T": ("XLC", "Communication Services"),
    "XOM": ("XLE", "Energy"),
    "CVX": ("XLE", "Energy"),
    "COP": ("XLE", "Energy"),
    "EOG": ("XLE", "Energy"),
    "VLO": ("XLE", "Energy"),
    "GE": ("XLI", "Industrials"),
    "CAT": ("XLI", "Industrials"),
    "UNP": ("XLI", "Industrials"),
    "HON": ("XLI", "Industrials"),
    "RTX": ("XLI", "Industrials"),
    "LMT": ("XLI", "Industrials"),
    "DE": ("XLI", "Industrials"),
    "ETN": ("XLI", "Industrials"),
    "UPS": ("XLI", "Industrials"),
    "WM": ("XLI", "Industrials"),
    "PH": ("XLI", "Industrials"),
    "ADP": ("XLI", "Industrials"),
    "MSI": ("XLI", "Industrials"),
    "PG": ("XLP", "Consumer Staples"),
    "COST": ("XLP", "Consumer Staples"),
    "WMT": ("XLP", "Consumer Staples"),
    "KO": ("XLP", "Consumer Staples"),
    "PEP": ("XLP", "Consumer Staples"),
    "PM": ("XLP", "Consumer Staples"),
    "MDLZ": ("XLP", "Consumer Staples"),
    "LIN": ("XLB", "Materials"),
    "NEE": ("XLU", "Utilities"),
    "SO": ("XLU", "Utilities"),
    "DUK": ("XLU", "Utilities"),
    "PLD": ("XLRE", "Real Estate"),
    "AMT": ("XLRE", "Real Estate"),
    "EQIX": ("XLRE", "Real Estate"),
}


async def execute_sector_fundamentals_tool(limit: int = 11) -> str:
    """Aggregates S&P 500 constituents by GICS Sector ETF to compute sector P/E, Forward P/E, and beat rates."""
    try:
        client = get_supabase_client()
        res = (
            client.table("market_barometer_history")
            .select("date, pe_ratio, forward_pe, constituents_data")
            .order("date", desc=True)
            .limit(1)
            .execute()
        )

        if not res.data:
            return "No S&P 500 Market Health Barometer data found."

        row = res.data[0]
        date_str = row.get("date") or "N/A"
        constituents = row.get("constituents_data") or []

        if not constituents:
            return f"No constituent data found in market barometer for {date_str}."

        # Group constituents by sector ETF
        sectors: dict[str, dict] = {}

        for c in constituents:
            sym = (c.get("symbol") or "").upper().strip()
            sec_name_raw = (c.get("sector") or "").strip().lower()

            sector_tuple = None
            if sec_name_raw and sec_name_raw in GICS_TO_SECTOR_ETF:
                sector_tuple = GICS_TO_SECTOR_ETF[sec_name_raw]
            elif sym in TICKER_TO_SECTOR_ETF:
                sector_tuple = TICKER_TO_SECTOR_ETF[sym]

            if not sector_tuple:
                continue

            etf_sym, etf_name = sector_tuple
            if etf_sym not in sectors:
                sectors[etf_sym] = {
                    "name": etf_name,
                    "mcap": 0.0,
                    "sum_mcap_pe": 0.0,
                    "sum_income": 0.0,
                    "sum_mcap_fwd": 0.0,
                    "sum_fwd_income": 0.0,
                    "beats_count": 0,
                    "total_reporting": 0,
                    "constituents_count": 0,
                }

            sec = sectors[etf_sym]
            sec["constituents_count"] += 1
            mcap = float(c.get("market_cap") or 0.0)
            price = float(c.get("price") or 0.0)
            sec["mcap"] += mcap

            # Trailing P/E
            pe = c.get("pe")
            if pe is not None and float(pe) > 0 and mcap > 0:
                pe_val = float(pe)
                sec["sum_mcap_pe"] += mcap
                sec["sum_income"] += mcap / pe_val

            # Forward P/E
            next_eps = c.get("next_eps_est")
            if next_eps is not None and float(next_eps) > 0 and price > 0 and mcap > 0:
                shares = mcap / price
                fwd_income = float(next_eps) * shares
                if fwd_income > 0:
                    sec["sum_mcap_fwd"] += mcap
                    sec["sum_fwd_income"] += fwd_income

            # Earnings Beat
            beat = c.get("beat")
            if beat is not None:
                sec["total_reporting"] += 1
                if beat:
                    sec["beats_count"] += 1

        if not sectors:
            return f"No sector mapping could be determined for constituents on {date_str}."

        output = f"S&P 500 Sector Fundamentals & Earnings Breakdown (Date: {date_str}):\n"

        # Sort sectors by market cap descending
        sorted_sectors = sorted(sectors.items(), key=lambda x: x[1]["mcap"], reverse=True)[:limit]

        for etf_sym, data in sorted_sectors:
            pe_agg = (data["sum_mcap_pe"] / data["sum_income"]) if data["sum_income"] > 0 else None
            fwd_pe_agg = (data["sum_mcap_fwd"] / data["sum_fwd_income"]) if data["sum_fwd_income"] > 0 else None
            beat_rate = (data["beats_count"] / data["total_reporting"] * 100.0) if data["total_reporting"] > 0 else None

            pe_str = f"{pe_agg:.2f}" if pe_agg is not None else "N/A"
            fwd_pe_str = f"{fwd_pe_agg:.2f}" if fwd_pe_agg is not None else "N/A"
            beat_str = (
                f"{beat_rate:.1f}% ({data['beats_count']}/{data['total_reporting']} reporting)"
                if beat_rate is not None
                else "N/A"
            )

            output += (
                f"- {etf_sym} ({data['name']}): "
                f"Trailing P/E: {pe_str} | Forward P/E: {fwd_pe_str} | "
                f"Earnings Beat Rate: {beat_str}\n"
            )

        return output
    except Exception as e:
        logger.exception("Error executing get_sector_fundamentals tool")
        return f"Error retrieving sector fundamentals data: {str(e)}"


async def execute_financial_valuation_tool(
    ticker: str,
    growth_rate: float | None = None,
    discount_rate: float | None = None,
    terminal_growth: float = 0.025,
) -> str:
    """Executes the financial valuation audit tool and returns a markdown-formatted report."""
    ticker = ticker.upper()
    manager = MarketDataManager()

    try:
        # 1. Fetch market quote data (price, market cap)
        quote = await manager.get_quote(ticker)
        if not quote or not quote.exists:
            return f"Error: Ticker '{ticker}' not found or could not fetch price data."

        price = quote.price
        market_cap = quote.market_cap
        if price <= 0 or market_cap <= 0:
            return f"Error: Invalid pricing or market cap retrieved for {ticker} (Price: {price}, Market Cap: {market_cap})."

        # Calculate initial shares outstanding estimate
        shares_outstanding = market_cap / price

        # 2. Fetch key metrics history — try quarterly first for earnings-week relevance,
        # fall back to annual via the FMP provider's 402→annual fallback handler.
        key_metrics = await manager.get_key_metrics(ticker, period="quarter", limit=2)
        if not key_metrics:
            return f"Error: No key metrics data found for {ticker}."

        latest_metric = key_metrics[0]

        # Detect if we got annual fallback (FMP plan tier limits) so the report
        # can flag the degradation for the LLM.
        actual_period = str(latest_metric.get("period") or "")
        metrics_degradation_note = ""
        if "Q" not in actual_period.upper():
            metrics_degradation_note = (
                "\n> ⚠️ NOTE: FMP quarterly metrics unavailable on current plan "
                "(402 Payment Required). DCF using annual fallback metrics; "
                "earnings-week signals should be discounted accordingly.\n"
            )

        # 3. Fetch profile (for Beta)
        profile = await manager.get_company_profile(ticker)
        beta = 1.0
        company_name = ticker
        if profile and isinstance(profile, list) and len(profile) > 0:
            p = profile[0]
            company_name = p.get("companyName") or ticker
            try:
                beta = float(p.get("beta") or 1.0)
            except (ValueError, TypeError):
                beta = 1.0

        # 4. Fetch analyst consensus estimates
        estimates = await manager.get_analyst_estimates(ticker, period="annual", limit=5)

        # 5. Fetch financial growth history
        growth_history = await manager.get_financial_growth(ticker, period="annual", limit=5)

        # --- Calculate Forecast Growth Rate ---
        forecast_growth = None
        if estimates and len(estimates) >= 2:
            with contextlib.suppress(Exception):
                # Estimate growth YoY from estimates
                rev_y1 = float(estimates[0].get("estimatedRevenueAvg") or 0)
                rev_y2 = float(estimates[1].get("estimatedRevenueAvg") or 0)
                if rev_y1 > 0 and rev_y2 > 0:
                    forecast_growth = (rev_y2 / rev_y1) - 1.0

        if forecast_growth is None and growth_history and len(growth_history) >= 1:
            with contextlib.suppress(Exception):
                # Fallback to historical growth YoY
                forecast_growth = float(growth_history[0].get("revenueGrowth") or 0.08)

        if forecast_growth is None:
            forecast_growth = 0.08  # Default baseline 8%

        growth_rate_used = growth_rate if growth_rate is not None else forecast_growth
        growth_rate_used = max(-0.25, min(0.40, growth_rate_used))  # Clamp to safe boundaries

        # --- Calculate WACC (Discount Rate) ---
        rf = 0.042  # 10-Yr US Treasury yield baseline (4.2%)
        erp = 0.055  # Equity Risk Premium baseline (5.5%)
        cost_of_equity = rf + beta * erp

        # Capital Structure / Net Debt
        net_debt = 0.0
        with contextlib.suppress(ValueError, TypeError):
            val = latest_metric.get("netDebt")
            if val is not None:
                net_debt = float(val)

        # Calculate WACC weights
        total_value = market_cap + max(0.0, net_debt)
        if total_value > 0 and net_debt > 0:
            weight_equity = market_cap / total_value
            weight_debt = net_debt / total_value
            cost_of_debt = 0.05  # Pre-tax debt rate default (5%)
            tax_rate = 0.21  # Standard US corporate tax (21%)
            after_tax_debt = cost_of_debt * (1 - tax_rate)
            calculated_wacc = (cost_of_equity * weight_equity) + (after_tax_debt * weight_debt)
        else:
            # Net Cash firm or no debt: WACC equals Cost of Equity
            calculated_wacc = cost_of_equity

        wacc_used = discount_rate if discount_rate is not None else calculated_wacc
        wacc_used = max(0.05, min(0.18, wacc_used))  # Clamp WACC to safe range (5% - 18%)

        # --- Cash Flow Discounting ---
        # Estimate recent Free Cash Flow
        fcf_yield = latest_metric.get("freeCashFlowYield")
        fcf_per_share = latest_metric.get("freeCashFlowPerShare")
        if fcf_yield is not None:
            base_fcf = float(fcf_yield) * market_cap
        elif fcf_per_share is not None:
            base_fcf = float(fcf_per_share) * shares_outstanding
        else:
            net_income_ps = latest_metric.get("netIncomePerShare")
            if net_income_ps is not None:
                base_fcf = float(net_income_ps) * shares_outstanding * 0.8
            else:
                base_fcf = market_cap * 0.05  # Default to 5% FCF Yield

        # Safely clamp terminal growth below WACC
        tg_used = terminal_growth
        if tg_used >= wacc_used:
            tg_used = wacc_used - 0.02

        # 5-Year forecast schedule
        projected_fcfs = []
        discount_factors = []
        pv_fcfs = []

        current_fcf = base_fcf
        for yr in range(1, 6):
            current_fcf = current_fcf * (1 + growth_rate_used)
            projected_fcfs.append(current_fcf)

            # Mid-year convention discounting: (yr - 0.5)
            df = 1.0 / ((1 + wacc_used) ** (yr - 0.5))
            discount_factors.append(df)
            pv_fcfs.append(current_fcf * df)

        sum_pv_fcfs = sum(pv_fcfs)

        # Terminal Value calculation
        terminal_fcf = projected_fcfs[-1] * (1 + tg_used)
        terminal_value = terminal_fcf / (wacc_used - tg_used)
        # Discount terminal value at year 5
        pv_terminal_value = terminal_value / ((1 + wacc_used) ** 5.0)

        # Valuation bridge
        implied_ev = sum_pv_fcfs + pv_terminal_value
        implied_equity_val = implied_ev - net_debt
        implied_price = implied_equity_val / shares_outstanding
        implied_upside = (implied_price / price - 1.0) * 100

        # --- Comparable Peer Comps Analysis ---
        # Fetch S&P 500 barometer aggregates (PE: ~22.5, Forward PE: ~18.5, P/FCF: ~20.0)
        # We fetch the latest health barometer from DB if available, otherwise fallback to defaults
        barometer_pe = 22.5
        barometer_pfcf = 20.0
        try:
            from tools._compat import get_supabase_client

            client_db = get_supabase_client()
            res = (
                client_db.table("market_barometer_history")
                .select("pe_ratio, pfcf_ratio")
                .order("date", desc=True)
                .limit(1)
                .execute()
            )
            if res.data:
                barometer_pe = float(res.data[0].get("pe_ratio") or 22.5)
                barometer_pfcf = float(res.data[0].get("pfcf_ratio") or 20.0)
        except Exception as e:
            # Don't silently swallow — log so future schema drift surfaces.
            logger.warning(f"market_barometer_history query failed (using defaults 22.5/20.0): {e}")

        pe_ratio = latest_metric.get("peRatio")
        pfcf_ratio = latest_metric.get("priceToFreeCashFlowsRatio")
        ev_ebitda = latest_metric.get("enterpriseValueOverEBITDA")

        pe_str = f"{pe_ratio:.2f}x" if pe_ratio else "N/A"
        pfcf_str = f"{pfcf_ratio:.2f}x" if pfcf_ratio else "N/A"
        ev_ebitda_str = f"{ev_ebitda:.2f}x" if ev_ebitda else "N/A"

        # Determine valuation status
        status = "FAIR VALUE"
        reasons = []
        if implied_upside > 15.0:
            status = "UNDERVALUED"
            reasons.append("DCF implied price suggests >15% upside")
        elif implied_upside < -10.0:
            status = "OVERVALUED"
            reasons.append("DCF implied price suggests >10% downside")

        if pe_ratio and pe_ratio > barometer_pe * 1.3:
            reasons.append(f"PE multiple ({pe_str}) trades at >30% premium to S&P 500 average ({barometer_pe:.1f}x)")
        elif pe_ratio and pe_ratio < barometer_pe * 0.7:
            reasons.append(f"PE multiple ({pe_str}) trades at >30% discount to S&P 500 average ({barometer_pe:.1f}x)")

        # Create the markdown audit report
        pe_premium = f"{((pe_ratio / barometer_pe - 1) * 100):+.1f}%" if pe_ratio else "N/A"
        pfcf_premium = f"{((pfcf_ratio / barometer_pfcf - 1) * 100):+.1f}%" if pfcf_ratio else "N/A"

        output = (
            f"### 📊 Valuation & Intrinsic Value Audit Report: {ticker} ({company_name})\n\n"
            f"**Valuation Status:** `{status}`\n"
            f"**Current Price:** ${price:.2f} | **Implied Intrinsic Price:** ${implied_price:.2f} ({implied_upside:+.1f}% upside/downside)\n"
            f"{metrics_degradation_note}\n"
            f"#### 1. DCF Model Assumptions & Inputs\n"
            f"- **Forecast Growth Rate:** {growth_rate_used * 100:.1f}% (Base: {'analyst estimates' if forecast_growth == estimates else 'historical growth'})\n"
            f"- **Discount Rate (WACC):** {wacc_used * 100:.1f}% (CAPM Beta: {beta:.2f}, Cost of Equity: {cost_of_equity * 100:.1f}%)\n"
            f"- **Terminal perpetuity Growth (g):** {tg_used * 100:.1f}%\n"
            f"- **Diluted Shares Outstanding:** {shares_outstanding:.1f}M\n"
            f"- **Net Debt (Debt - Cash):** ${net_debt / 1e6:.1f}M\n\n"
            f"#### 2. Discounted Cash Flow (DCF) Bridge\n"
            f"| Metric | Year 1 | Year 2 | Year 3 | Year 4 | Year 5 | Terminal Value |\n"
            f"| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n"
            f"| **FCF ($M)** | ${projected_fcfs[0] / 1e6:.1f} | ${projected_fcfs[1] / 1e6:.1f} | ${projected_fcfs[2] / 1e6:.1f} | ${projected_fcfs[3] / 1e6:.1f} | ${projected_fcfs[4] / 1e6:.1f} | ${terminal_value / 1e6:.1f} |\n"
            f"| **Discount Factor** | {discount_factors[0]:.4f} | {discount_factors[1]:.4f} | {discount_factors[2]:.4f} | {discount_factors[3]:.4f} | {discount_factors[4]:.4f} | {1.0 / ((1 + wacc_used) ** 5.0):.4f} |\n"
            f"| **PV ($M)** | ${pv_fcfs[0] / 1e6:.1f} | ${pv_fcfs[1] / 1e6:.1f} | ${pv_fcfs[2] / 1e6:.1f} | ${pv_fcfs[3] / 1e6:.1f} | ${pv_fcfs[4] / 1e6:.1f} | ${pv_terminal_value / 1e6:.1f} |\n\n"
            f"- **Sum of PV of Explicit Cash Flows:** ${sum_pv_fcfs / 1e6:.1f}M\n"
            f"- **PV of perpetuity Terminal Value:** ${pv_terminal_value / 1e6:.1f}M\n"
            f"- **Implied Enterprise Value (EV):** ${implied_ev / 1e6:.1f}M\n"
            f"- **Implied Equity Value (EV - Net Debt):** ${implied_equity_val / 1e6:.1f}M\n\n"
            f"#### 3. Comparable Multiple Analysis\n"
            f"| Valuation Multiple | Ticker Value | S&P 500 Average | Premium / Discount |\n"
            f"| :--- | :--- | :--- | :--- |\n"
            f"| **P/E Ratio** | {pe_str} | {barometer_pe:.1f}x | {pe_premium} |\n"
            f"| **Price / FCF** | {pfcf_str} | {barometer_pfcf:.1f}x | {pfcf_premium} |\n"
            f"| **EV / EBITDA** | {ev_ebitda_str} | N/A | N/A |\n\n"
        )
        if reasons:
            output += "#### 4. Audit Observations & Key Concerns\n"
            for r in reasons:
                output += f"- {r}\n"

        return output.strip()

    except Exception as e:
        logger.exception(f"Error executing valuation audit for {ticker}: {str(e)}")
        return f"Error executing valuation audit for {ticker}: {str(e)}"
