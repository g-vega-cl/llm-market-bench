"""CLI sub-command router for daily predictions, postmortems, newsletters, and analogs."""

import argparse
import asyncio


def handle_daily_predictor(args: argparse.Namespace) -> None:
    """Run daily prediction pipeline for target ticker (SPY, TLT, or all)."""
    ticker = getattr(args, "ticker", "SPY") or "SPY"
    ticker_clean = ticker.strip().upper()

    if ticker_clean == "TLT":
        from tasks.bond_predictor import run_daily_bond_prediction

        asyncio.run(run_daily_bond_prediction(ticker="TLT", force=args.force))
    elif ticker_clean == "ALL":
        from tasks.bond_predictor import run_daily_bond_prediction
        from tasks.daily_predictor import run_daily_prediction

        asyncio.run(run_daily_prediction(ticker="SPY", force=args.force))
        asyncio.run(run_daily_bond_prediction(ticker="TLT", force=args.force))
    else:
        from tasks.daily_predictor import run_daily_prediction

        asyncio.run(run_daily_prediction(ticker=ticker, force=args.force))


def handle_evaluate_daily_predictions(args: argparse.Namespace) -> None:
    """Evaluate prediction accuracy against market outcome."""
    from tasks.evaluate_daily_predictions import evaluate_daily_predictions

    asyncio.run(evaluate_daily_predictions(target_date=args.target_date, force_recalc=args.force))


def handle_seed_daily_predictor(args: argparse.Namespace) -> None:
    """Seed daily predictor prompt baseline."""
    from tasks.daily_predictor import seed_daily_predictor_prompt

    asyncio.run(seed_daily_predictor_prompt())


def handle_daily_postmortem(args: argparse.Namespace) -> None:
    """Run daily postmortem analysis on trade decisions."""
    from analysis.daily_postmortem import run_daily_postmortem

    asyncio.run(run_daily_postmortem(target_date=args.target_date, force=args.force))


def handle_gainers_postmortem(args: argparse.Namespace) -> None:
    """Run postmortem audit on missed market gainers."""
    from analysis.gainers_postmortem import run_gainers_postmortem

    asyncio.run(
        run_gainers_postmortem(
            timeframe=args.timeframe,
            limit=args.limit,
            save_memory=not args.no_save_memory,
        )
    )


def handle_historical_analog(args: argparse.Namespace) -> None:
    """Research historical market analogs for current market regimes."""
    from analysis.historical_analogs import research_historical_market_analog

    situation_text = args.situation or "Unusual market movements across global asset classes"
    focus_list = [a.strip() for a in args.assets.split(",")] if args.assets else None

    async def _run_analog_cli():
        result = await research_historical_market_analog(
            situation=situation_text,
            focus_assets=focus_list,
            horizon=args.horizon,
        )
        print(result)

    asyncio.run(_run_analog_cli())


def handle_generate_newsletter(args: argparse.Namespace) -> None:
    """Generate daily market newsletter summary."""
    from tasks.newsletter_generator import generate_daily_newsletter

    target_date = getattr(args, "target_date", None)
    dispatch_research = getattr(args, "dispatch_research", False)
    asyncio.run(
        generate_daily_newsletter(
            session=args.session,
            target_date=target_date,
            dispatch_research=dispatch_research,
        )
    )


def handle_research_company(args: argparse.Namespace) -> None:
    """Run on-demand deep dive research for an individual ticker or extract from latest newsletter."""
    from tasks.research_newsletter_tickers import research_latest_newsletter, research_single_target
    from tasks.ticker_extractor import CompanyMention

    from_newsletter = getattr(args, "from_newsletter", False)
    if from_newsletter:
        session = getattr(args, "session", "open")
        target_date = getattr(args, "target_date", None)
        force = getattr(args, "force", False)
        results = asyncio.run(
            research_latest_newsletter(
                session=session,
                target_date=target_date,
                force_refresh=force,
            )
        )
        print(
            f"Newsletter company research completed for session '{session}': {len(results)} dossiers generated/linked."
        )
        return

    ticker = getattr(args, "ticker", None) or "NVDA"
    mention = CompanyMention(
        ticker=ticker,
        company_name=getattr(args, "name", None) or ticker,
        sector=getattr(args, "sector", None),
    )
    result = asyncio.run(
        research_single_target(
            mention=mention,
            session="on_demand",
            force_refresh=getattr(args, "force", False),
        )
    )
    print(
        f"Research completed for {ticker}: Verdict={result.get('verdict')} (Conviction: {result.get('conviction_score')}%)"
    )


def handle_earnings_predictor(args: argparse.Namespace) -> None:
    """Run earnings day-1 prediction pipeline across Luna, DeepSeek, and Jev."""
    from tasks.earnings_predictor import run_earnings_prediction

    target_date = getattr(args, "target_date", None)
    raw_ticker = getattr(args, "ticker", None)
    # SPY is an ETF and never reports quarterly earnings. If the default 'SPY' is present,
    # treat as None to enable automatic discovery of actual reporting stocks.
    ticker = None if raw_ticker and raw_ticker.upper() == "SPY" else raw_ticker
    force = getattr(args, "force", False)
    asyncio.run(run_earnings_prediction(target_date=target_date, ticker=ticker, force=force))


def handle_evaluate_earnings_predictions(args: argparse.Namespace) -> None:
    """Evaluate earnings predictions against RTH market outcomes."""
    from tasks.evaluate_earnings_predictions import evaluate_earnings_predictions

    target_date = getattr(args, "target_date", None)
    force = getattr(args, "force", False)
    asyncio.run(evaluate_earnings_predictions(target_date=target_date, force_recalc=force))


def handle_stock_picker(args: argparse.Namespace) -> None:
    """Run daily stock picker arena (3 Up, 3 Down) across models."""
    from tasks.stock_picker import run_daily_stock_picker

    target_date = getattr(args, "target_date", None)
    force = getattr(args, "force", False)
    asyncio.run(run_daily_stock_picker(target_date=target_date, force=force))


def handle_evaluate_stock_picks(args: argparse.Namespace) -> None:
    """Evaluate daily stock baskets and picks against actual RTH prices."""
    from tasks.evaluate_stock_picks import evaluate_stock_picks

    target_date = getattr(args, "target_date", None)
    force = getattr(args, "force", False)
    asyncio.run(evaluate_stock_picks(target_date=target_date, force_recalc=force))
