"""Analyst personas and structural market forces: Warren Buffett/Munger audit, historical analogs, and future forces."""

from core.config import logger
from tools._compat import MarketDataManager, get_supabase_client
from tools.news_memories import (
    execute_add_thematic_flow_tool as execute_add_thematic_flow_tool,
)
from tools.news_memories import (
    execute_get_thematic_flows_tool as execute_get_thematic_flows_tool,
)


async def execute_analyze_thematic_beneficiaries_tool(
    anchor_ticker: str,
    theme: str | None = None,
    candidate_tickers: list[str] | None = None,
    candidate_industries: list[str] | None = None,
    candidate_sectors: list[str] | None = None,
    lookback_days: int = 60,
    options_top_n: int = 3,
    include_financials: bool = True,
    include_institutional: bool = False,
) -> str:
    """Executes the analyze_thematic_beneficiaries tool to identify related winners."""
    try:
        from analysis.thematic_beneficiaries import (
            compute_thematic_beneficiaries,
            format_thematic_beneficiaries_markdown,
        )

        result = await compute_thematic_beneficiaries(
            anchor_ticker=anchor_ticker,
            theme=theme,
            candidate_tickers=candidate_tickers,
            candidate_industries=candidate_industries,
            candidate_sectors=candidate_sectors,
            lookback_days=lookback_days,
            options_top_n=options_top_n,
            include_financials=include_financials,
            include_institutional=include_institutional,
        )
        return format_thematic_beneficiaries_markdown(result)
    except Exception as e:
        logger.exception("Error executing analyze_thematic_beneficiaries tool for %s: %s", anchor_ticker, e)
        return f"Error analyzing thematic beneficiaries for '{anchor_ticker}': {e}"


async def execute_call_warren_buffett_tool(
    ticker: str | None = None,
    action: str | None = None,
    proposed_thesis: str | None = None,
) -> str:
    """Executes the call_warren_buffett tool, synthesizing value investing, moat analysis, and Munger inversion."""
    try:
        # If no ticker provided, perform a macro valuation and asset allocation check
        if not ticker or not ticker.strip():
            from core.fred import fetch_fred_series_observations

            client = get_supabase_client()
            res = client.table("market_barometer_history").select("*").order("date", desc=True).limit(1).execute()

            pe_val_str = "N/A"
            fwd_pe_str = "N/A"
            pb_val_str = "N/A"
            ps_val_str = "N/A"
            pfcf_val_str = "N/A"
            t10_yield_str = "N/A"
            erp_str = "N/A"
            is_expensive = False

            fwd_pe_num = None
            if res.data:
                latest = res.data[0]
                if latest.get("pe_ratio") is not None:
                    pe_val_str = f"{float(latest['pe_ratio']):.2f}"
                if latest.get("forward_pe") is not None:
                    fwd_pe_num = float(latest["forward_pe"])
                    fwd_pe_str = f"{fwd_pe_num:.2f}"
                if latest.get("pb_ratio") is not None:
                    pb_val_str = f"{float(latest['pb_ratio']):.2f}"
                if latest.get("ps_ratio") is not None:
                    ps_val_str = f"{float(latest['ps_ratio']):.2f}"
                if latest.get("pfcf_ratio") is not None:
                    pfcf_val_str = f"{float(latest['pfcf_ratio']):.2f}"

            # Fetch 10-year Treasury yield
            latest_yield = None
            try:
                t10_data = await fetch_fred_series_observations("treasury_10y", lookback_periods=1)
                if t10_data and t10_data.get("latest_value") is not None:
                    latest_yield = float(t10_data["latest_value"])
                elif t10_data and t10_data.get("observations"):
                    obs = [o for o in t10_data["observations"] if o.get("value") is not None]
                    if obs:
                        latest_yield = float(obs[-1]["value"])
            except Exception as e:
                logger.debug("Could not fetch 10Y yield for Warren Buffett tool: %s", e)

            if latest_yield is not None:
                t10_yield_str = f"{latest_yield:.2f}%"
                if fwd_pe_num and fwd_pe_num > 0:
                    fwd_ey = 100.0 / fwd_pe_num
                    erp = fwd_ey - latest_yield
                    erp_str = f"{erp:+.2f}% (Forward Earnings Yield {fwd_ey:.2f}% minus 10Y Yield {latest_yield:.2f}%)"
                    if erp < 1.0 or fwd_pe_num > 21.0:
                        is_expensive = True
            elif fwd_pe_num and fwd_pe_num > 21.0:
                is_expensive = True

            if is_expensive:
                verdict = "PRUDENT CAUTION: Equity risk premium is compressed. Maintain strict valuation standards and hold dry powder."
                saying = (
                    '"The stock market is a device for transferring money from the impatient to the patient. '
                    "Be fearful when others are greedy, and greedy when others are fearful. When the tide goes out, "
                    'you find out who has been swimming naked."'
                )
            else:
                verdict = "SELECTIVE ACCUMULATION: Equities offer attractive earnings yields relative to bonds. Focus on durable moats."
                saying = (
                    '"Opportunities come infrequently. When it rains gold, put out the bucket, not the thimble. '
                    'Price is what you pay, value is what you get."'
                )

            lines = [
                "=== THE ORACLE OF OMAHA (WARREN BUFFETT & CHARLIE MUNGER AUDIT) ===",
                "[ MACRO VALUATION & CAPITAL ALLOCATION BRIEFING ]",
                f"- S&P 500 Trailing P/E: {pe_val_str}",
                f"- S&P 500 Forward P/E: {fwd_pe_str}",
                f"- S&P 500 P/B Ratio: {pb_val_str}",
                f"- S&P 500 P/S Ratio: {ps_val_str}",
                f"- S&P 500 Price/FCF: {pfcf_val_str}",
                f"- 10-Year US Treasury: {t10_yield_str}",
                f"- Equity Risk Premium (ERP): {erp_str}",
                "",
                "[ BUFFETT ALLOCATION PRINCIPLES ]",
                "- Cash & Short-Term Treasuries: Holding cash when valuations are stretched is not dead money; it is strategic patience.",
                "- Circle of Competence: Only allocate to businesses whose 10-year unit economics and competitive moats you understand.",
                "",
                f"[ ORACLE VERDICT ]\n{verdict}",
                f"[ ORACLE WISDOM ]\n{saying}",
            ]
            return "\n".join(lines)

        # Ticker evaluation branch
        ticker = ticker.strip().upper()
        manager = MarketDataManager()

        quote = await manager.get_quote(ticker)
        if not quote or not quote.exists or quote.price <= 0:
            return f"Error: Ticker '{ticker}' not found or no price data available."

        price = quote.price
        market_cap = quote.market_cap

        key_metrics = await manager.get_key_metrics(ticker, period="annual", limit=1)
        if not key_metrics:
            key_metrics = await manager.get_key_metrics(ticker, period="quarter", limit=1)

        metric = key_metrics[0] if key_metrics else {}

        pe_ratio = metric.get("peRatio")
        pb_ratio = metric.get("pbRatio")
        debt_to_equity = metric.get("debtToEquity")
        net_debt = metric.get("netDebt")
        roe = metric.get("roe")
        fcf_yield = metric.get("freeCashFlowYield")

        # 10Y yield for ERP
        latest_yield = 4.25
        try:
            from core.fred import fetch_fred_series_observations

            t10_data = await fetch_fred_series_observations("treasury_10y", lookback_periods=1)
            if t10_data and t10_data.get("latest_value") is not None:
                latest_yield = float(t10_data["latest_value"])
            elif t10_data and t10_data.get("observations"):
                obs = [o for o in t10_data["observations"] if o.get("value") is not None]
                if obs:
                    latest_yield = float(obs[-1]["value"])
        except Exception:
            pass

        # Moat & Capital Efficiency
        if roe is not None and float(roe) >= 0.15:
            moat_status = f"ROE: {float(roe) * 100:.1f}% (Superior capital efficiency and durable economic moat)"
            has_moat = True
        elif roe is not None and float(roe) > 0:
            moat_status = f"ROE: {float(roe) * 100:.1f}% (Average capital efficiency, modest competitive moat)"
            has_moat = False
        elif roe is not None:
            moat_status = f"ROE: {float(roe) * 100:.1f}% (Negative return on equity, capital dilutive)"
            has_moat = False
        else:
            moat_status = "ROE: N/A (Insufficient history to verify economic moat)"
            has_moat = False

        # Balance Sheet Sanity
        swimming_naked = False
        if debt_to_equity is not None and float(debt_to_equity) > 2.0:
            swimming_naked = True
        if net_debt is not None and market_cap > 0 and float(net_debt) > (market_cap * 0.75):
            swimming_naked = True

        if swimming_naked:
            de_str = f"{float(debt_to_equity):.2f}x" if debt_to_equity is not None else "High"
            balance_sheet_status = (
                f"SWIMMING NAKED WARNING: Debt-to-Equity is {de_str}. High debt burdens expose the business "
                "to severe refinancing friction if cash flows contract. Charlie Munger: There are only three ways "
                "a smart person can go broke: liquor, ladies, and leverage."
            )
        else:
            de_str = f"{float(debt_to_equity):.2f}x" if debt_to_equity is not None else "Low"
            balance_sheet_status = f"Conservative fortress balance sheet (Debt-to-Equity: {de_str}). Strong solvency and financial durability."

        # Margin of Safety & Valuation
        pe_num = float(pe_ratio) if pe_ratio is not None and float(pe_ratio) > 0 else None
        if pe_num:
            earnings_yield = 100.0 / pe_num
            erp = earnings_yield - latest_yield
            val_detail = (
                f"P/E: {pe_num:.1f}x | Earnings Yield: {earnings_yield:.2f}% vs 10Y Treasury: {latest_yield:.2f}% "
                f"(ERP: {erp:+.2f}%)"
            )
            if pe_num > 35.0:
                val_status = f"Stretched multiple ({val_detail}). Paying an aggressive growth premium with zero margin of safety."
            elif pe_num <= 18.0:
                val_status = (
                    f"Defensive valuation ({val_detail}). Substantial margin of safety against macro pullbacks."
                )
            else:
                val_status = f"Fair valuation ({val_detail}). Reasonable price for an established compounder."
        else:
            val_status = (
                f"P/E: N/A | P/B: {float(pb_ratio):.2f}x" if pb_ratio is not None else "Valuation ratios unavailable."
            )

        # Munger Inversion ("Stupid Person Test")
        inversion_lines = []
        action_str = (action or "EVALUATE").upper()
        inversion_lines.append(f"Proposed Action: {action_str}")
        if proposed_thesis:
            inversion_lines.append(f"Stated Thesis: {proposed_thesis}")

        inversion_lines.append("Munger Inversion Challenges:")
        inversion_lines.append(
            "1. What if industry growth turns negative for two consecutive years? Does this company survive without diluting equity?"
        )
        if swimming_naked:
            inversion_lines.append(
                "2. Invert: If interest rates remain restrictive, how much cash flow is consumed solely by debt service?"
            )
        else:
            inversion_lines.append(
                "2. Invert: Would a smart investor buy the entire business privately at this exact valuation?"
            )

        if pe_num and pe_num > 30.0:
            inversion_lines.append(
                "3. Invert: Are you buying because the underlying business is cheap, or because the price chart is going up?"
            )
        else:
            inversion_lines.append(
                "3. Invert: What is the primary single point of failure that could render your thesis worthless?"
            )

        # Verdict and Saying
        if swimming_naked:
            verdict = "REJECTED: Over-leveraged balance sheet. Violates Rule No. 1."
            saying = (
                '"Only when the tide goes out do you discover who has been swimming naked. '
                'Rule No. 1: Never lose money. Rule No. 2: Never forget rule No. 1."'
            )
        elif pe_num and pe_num > 35.0:
            verdict = "CAUTION: Premium valuation. Wonderful business, but minimal margin of safety."
            saying = (
                '"Price is what you pay. Value is what you get. It is far better to buy a wonderful company at a '
                'fair price than a fair company at a wonderful price, but overpaying leaves no room for disappointment."'
            )
        elif has_moat and (pe_num is None or pe_num <= 25.0):
            verdict = "APPROVED: Quality economic moat with attractive margin of safety."
            saying = (
                "\"If you aren't willing to own a stock for 10 years, don't even think about owning it for 10 minutes. "
                'Time is the friend of the wonderful business, the enemy of the mediocre."'
            )
        else:
            verdict = "NEUTRAL: Sound fundamentals, but wait for a more compelling entry price."
            saying = (
                "\"The stock market is a no-called-strike game. You don't have to swing at everything; you can wait "
                'for your pitch."'
            )

        report = [
            "=== THE ORACLE OF OMAHA (WARREN BUFFETT & CHARLIE MUNGER AUDIT) ===",
            f"Ticker: {ticker} | Price: ${price:.2f} | Market Cap: ${market_cap:,.0f}",
            "",
            f"[ 1. MOAT & CAPITAL EFFICIENCY ]\n- {moat_status}",
            f"- Free Cash Flow Yield: {float(fcf_yield) * 100:.2f}%"
            if fcf_yield is not None
            else "- Free Cash Flow Yield: N/A",
            "",
            f'[ 2. BALANCE SHEET SANITY ("SWIMMING NAKED" CHECK) ]\n- {balance_sheet_status}',
            "",
            f"[ 3. MARGIN OF SAFETY & VALUATION ]\n- {val_status}",
            "",
            '[ 4. MUNGER INVERSION ("WOULD A STUPID PERSON DO THIS?") ]',
            "\n".join(inversion_lines),
            "",
            f"[ 5. ORACLE VERDICT ]\n{verdict}",
            "",
            f"[ 6. ORACLE WISDOM ]\n{saying}",
        ]
        return "\n".join(report)

    except Exception as e:
        logger.exception("Error executing call_warren_buffett tool: %s", e)
        return f"Error executing call_warren_buffett: {str(e)}"


async def execute_research_historical_market_analog_tool(
    situation: str,
    focus_assets: list[str] | None = None,
    horizon: str = "1m",
    model_name: str | None = None,
) -> str:
    """Executes the research_historical_market_analog tool."""
    try:
        from analysis.historical_analogs import research_historical_market_analog

        return await research_historical_market_analog(
            situation=situation,
            focus_assets=focus_assets,
            horizon=horizon or "1m",
            model_name=model_name,
        )
    except Exception as e:
        logger.exception("Error executing research_historical_market_analog tool: %s", e)
        return f"Error executing research_historical_market_analog: {str(e)}"


async def execute_get_future_forces_tool(
    archetype: str | None = None,
    max_horizon_months: int = 24,
    limit: int = 5,
) -> str:
    """Executes the get_future_forces tool."""
    from analytics.future_forces import execute_get_future_forces_tool as _get_forces

    return await _get_forces(archetype=archetype, max_horizon_months=max_horizon_months, limit=limit)


async def execute_research_future_force_tool(
    force_title: str,
    archetype: str,
    thesis: str,
    catalyst_event: str,
    invalidation_triggers: str,
    transmission_mechanism: str,
    tickers: list[str] | None = None,
    horizon_months: int = 3,
    model_name: str | None = None,
) -> str:
    """Executes the research_future_force tool."""
    from analytics.future_forces import execute_research_future_force_tool as _res_force

    return await _res_force(
        force_title=force_title,
        archetype=archetype,
        thesis=thesis,
        catalyst_event=catalyst_event,
        invalidation_triggers=invalidation_triggers,
        transmission_mechanism=transmission_mechanism,
        tickers=tickers,
        horizon_months=horizon_months,
        model_name=model_name,
    )
