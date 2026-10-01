"""CLI sub-command router for audit, portfolio reconciliation, and database cleanup."""

import argparse
import asyncio


def handle_audit(args: argparse.Namespace) -> None:
    """Run LLM and SQL pipeline integrity audit."""
    from core.audit import run_audit
    from core.audit.analyzer import configure as configure_analyzer
    from core.audit.runner import configure as configure_audit
    from core.config import DEEPSEEK_API_KEY, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_URL

    configure_audit(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    configure_analyzer(DEEPSEEK_API_KEY)
    asyncio.run(run_audit(dry_run=args.dry_run))


def handle_audit_alpaca(args: argparse.Namespace) -> None:
    """Reconcile simulated trade decisions against Alpaca broker executions."""
    from audit.alpaca_audit import run_alpaca_audit

    asyncio.run(run_alpaca_audit(model_name=args.model, days=args.days, json_output=args.json))


def handle_audit_portfolios(args: argparse.Namespace) -> None:
    """Audit portfolio holdings, equity drift, and heal missing trades."""
    from audit.portfolio_auditor import run_portfolio_auditor_cli

    asyncio.run(
        run_portfolio_auditor_cli(
            target_date=args.target_date,
            lookback_days=args.lookback_days or 5,
            fix=args.fix,
        )
    )


def handle_cleanup(args: argparse.Namespace) -> None:
    """Run database log retention and table cleanup routine."""
    from core.cleanup import run_cleanup

    asyncio.run(run_cleanup())
