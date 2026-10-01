"""CLI sub-command router for daily predictions, postmortems, newsletters, and analogs."""

import argparse
import asyncio


def handle_daily_predictor(args: argparse.Namespace) -> None:
    """Run daily prediction pipeline for target ticker."""
    from tasks.daily_predictor import run_daily_prediction

    asyncio.run(run_daily_prediction(ticker=args.ticker, force=args.force))


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

    asyncio.run(generate_daily_newsletter(session=args.session))
