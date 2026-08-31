"""Tests to verify GitHub Actions workflow schedule configurations."""

from pathlib import Path

import yaml


def test_workflow_schedule():
    """Verify that ingest.yml relies on Cloudflare Worker workflow_dispatch and does not have native schedule."""
    root = Path(__file__).resolve().parent.parent.parent.parent
    ingest_yml_path = root / ".github" / "workflows" / "ingest.yml"

    assert ingest_yml_path.exists(), f"Could not find workflow file at {ingest_yml_path}"

    with open(ingest_yml_path) as f:
        config = yaml.safe_load(f)

    # PyYAML safe_load parses 'on' as boolean True
    on_key = "on" if "on" in config else True
    schedule = config.get(on_key, {}).get("schedule", [])
    assert not schedule, f"Expected no native schedule in ingest.yml, found: {schedule}"


def test_update_prices_workflow_schedule():
    """Verify that update-prices.yml covers 13:00-21:00 UTC to support EDT 9:30 AM open."""
    root = Path(__file__).resolve().parent.parent.parent.parent
    prices_yml_path = root / ".github" / "workflows" / "update-prices.yml"

    assert prices_yml_path.exists(), f"Could not find workflow file at {prices_yml_path}"

    with open(prices_yml_path) as f:
        config = yaml.safe_load(f)

    on_key = "on" if "on" in config else True
    schedule = config.get(on_key, {}).get("schedule", [])
    cron_triggers = [trigger.get("cron") for trigger in schedule if isinstance(trigger, dict) and "cron" in trigger]

    assert "0,30 13-21 * * 1-5" in cron_triggers, (
        f"Expected 0,30 13-21 * * 1-5 in cron triggers, found: {cron_triggers}"
    )


def test_daily_predictor_workflow_schedule():
    """Verify daily-predictor.yml has native Sunday 10 PM UTC schedule for autoresearch."""
    root = Path(__file__).resolve().parent.parent.parent.parent
    predictor_yml_path = root / ".github" / "workflows" / "daily-predictor.yml"

    assert predictor_yml_path.exists(), f"Could not find workflow file at {predictor_yml_path}"

    with open(predictor_yml_path) as f:
        config = yaml.safe_load(f)

    on_key = "on" if "on" in config else True
    schedule = config.get(on_key, {}).get("schedule", [])
    cron_triggers = [trigger.get("cron") for trigger in schedule if isinstance(trigger, dict) and "cron" in trigger]
    assert "0 22 * * SUN" in cron_triggers, (
        f"Expected '0 22 * * SUN' in cron triggers for daily-predictor.yml, found: {cron_triggers}"
    )


def test_daily_predictor_workflow_env_keys():
    """Verify daily-predictor.yml includes MINIMAX_API_KEY for the MiniMax model arena runner."""
    root = Path(__file__).resolve().parent.parent.parent.parent
    predictor_yml_path = root / ".github" / "workflows" / "daily-predictor.yml"

    assert predictor_yml_path.exists(), f"Could not find workflow file at {predictor_yml_path}"

    with open(predictor_yml_path) as f:
        config = yaml.safe_load(f)

    jobs = config.get("jobs", {})
    predictor_job = jobs.get("run-daily-predictor", {})
    steps = predictor_job.get("steps", [])

    run_step = next((s for s in steps if s.get("name") == "Run Daily Predictor Command"), None)
    assert run_step is not None, "Could not find 'Run Daily Predictor Command' step in daily-predictor.yml"

    step_env = run_step.get("env", {})
    assert "MINIMAX_API_KEY" in step_env, f"Expected MINIMAX_API_KEY in step env, found: {list(step_env.keys())}"
    assert step_env["MINIMAX_API_KEY"] == "${{ secrets.MINIMAX_API_KEY }}"


def test_generate_newsletter_workflow_schedule():
    """Verify generate-newsletter.yml relies on Cloudflare Worker workflow_dispatch and does not have native schedule."""
    root = Path(__file__).resolve().parent.parent.parent.parent
    newsletter_yml_path = root / ".github" / "workflows" / "generate-newsletter.yml"

    assert newsletter_yml_path.exists(), f"Could not find workflow file at {newsletter_yml_path}"

    with open(newsletter_yml_path) as f:
        config = yaml.safe_load(f)

    on_key = "on" if "on" in config else True
    schedule = config.get(on_key, {}).get("schedule", [])
    assert not schedule, f"Expected no native schedule in generate-newsletter.yml, found: {schedule}"


def test_generate_newsletter_chains_daily_predictor():
    """Verify generate-newsletter.yml triggers daily-predictor.yml upon completion."""
    root = Path(__file__).resolve().parent.parent.parent.parent
    newsletter_yml_path = root / ".github" / "workflows" / "generate-newsletter.yml"

    assert newsletter_yml_path.exists(), f"Could not find workflow file at {newsletter_yml_path}"

    with open(newsletter_yml_path) as f:
        config = yaml.safe_load(f)

    jobs = config.get("jobs", {})
    job = jobs.get("generate-newsletter", {})
    permissions = job.get("permissions", {})
    assert permissions.get("actions") == "write", f"Expected actions: write in job permissions, found: {permissions}"

    steps = job.get("steps", [])

    trigger_step = next(
        (
            s
            for s in steps
            if "daily-predictor" in s.get("name", "").lower() or "daily predictor" in s.get("name", "").lower()
        ),
        None,
    )
    assert trigger_step is not None, "Could not find step triggering daily-predictor in generate-newsletter.yml"
    assert "daily-predictor" in trigger_step.get("run", "")


def test_cron_dispatcher_912_schedule():
    """Verify apps/cron-dispatcher/src/index.ts targets 9:12 AM ET for open newsletter synthesis and no longer has 9:20 or 5:15 branches."""
    root = Path(__file__).resolve().parent.parent.parent.parent
    index_ts_path = root / "apps" / "cron-dispatcher" / "src" / "index.ts"

    assert index_ts_path.exists(), f"Could not find index.ts file at {index_ts_path}"

    content = index_ts_path.read_text()
    assert "nyHour === 9 && nyMinute === 12" in content, (
        "Expected index.ts to check for nyHour === 9 && nyMinute === 12"
    )
    assert "nyHour === 9 && nyMinute === 20" not in content, (
        "Did not expect index.ts to have standalone 9:20 AM check (now chained from newsletter)"
    )
    assert "nyHour === 17 && nyMinute === 15" not in content, (
        "Did not expect index.ts to have standalone 5:15 PM check (now chained from close newsletter)"
    )


def test_cron_dispatcher_wrangler_triggers():
    """Verify apps/cron-dispatcher/wrangler.jsonc has <= 5 triggers including 9:12 AM ET (13:12 / 14:12 UTC)."""
    root = Path(__file__).resolve().parent.parent.parent.parent
    wrangler_path = root / "apps" / "cron-dispatcher" / "wrangler.jsonc"

    assert wrangler_path.exists(), f"Could not find wrangler.jsonc at {wrangler_path}"

    with open(wrangler_path) as f:
        # wrangler.jsonc is JSON with comments/schema, but loads cleanly as yaml
        config = yaml.safe_load(f)

    crons = config.get("triggers", {}).get("crons", [])
    assert len(crons) <= 5, f"Expected at most 5 cron triggers for Workers Free plan, found {len(crons)}: {crons}"
    assert "12 13,14 * * MON-FRI" in crons, f"Expected '12 13,14 * * MON-FRI' in crons, found: {crons}"
    assert "0 21,22 * * MON-FRI" in crons, f"Expected '0 21,22 * * MON-FRI' in crons, found: {crons}"
    assert "35 13-16 * * MON-FRI" in crons, f"Expected '35 13-16 * * MON-FRI' in crons, found: {crons}"
    assert "30 19,20 * * MON-FRI" in crons, f"Expected '30 19,20 * * MON-FRI' in crons, found: {crons}"


def test_autoresearch_workflow_env_keys():
    """Verify autoresearch.yml includes MINIMAX_API_KEY for track_openai meta-evaluator LLM routing."""
    root = Path(__file__).resolve().parent.parent.parent.parent
    autoresearch_yml_path = root / ".github" / "workflows" / "autoresearch.yml"

    assert autoresearch_yml_path.exists(), f"Could not find workflow file at {autoresearch_yml_path}"

    with open(autoresearch_yml_path) as f:
        config = yaml.safe_load(f)

    jobs = config.get("jobs", {})
    autoresearch_job = jobs.get("auto-research", {})
    steps = autoresearch_job.get("steps", [])

    run_step = next((s for s in steps if s.get("name") == "Run auto-research cycle"), None)
    assert run_step is not None, "Could not find 'Run auto-research cycle' step in autoresearch.yml"

    step_env = run_step.get("env", {})
    assert "MINIMAX_API_KEY" in step_env, f"Expected MINIMAX_API_KEY in step env, found: {list(step_env.keys())}"
    assert step_env["MINIMAX_API_KEY"] == "${{ secrets.MINIMAX_API_KEY }}"
