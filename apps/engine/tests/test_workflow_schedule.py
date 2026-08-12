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
    """Verify daily-predictor.yml relies on Cloudflare Worker workflow_dispatch and does not have native schedule."""
    root = Path(__file__).resolve().parent.parent.parent.parent
    predictor_yml_path = root / ".github" / "workflows" / "daily-predictor.yml"

    assert predictor_yml_path.exists(), f"Could not find workflow file at {predictor_yml_path}"

    with open(predictor_yml_path) as f:
        config = yaml.safe_load(f)

    on_key = "on" if "on" in config else True
    schedule = config.get(on_key, {}).get("schedule", [])
    assert not schedule, f"Expected no native schedule in daily-predictor.yml, found: {schedule}"


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


def test_cron_dispatcher_915_schedule():
    """Verify apps/cron-dispatcher/src/index.ts targets 9:15 AM ET for daily-predictor & newsletter."""
    root = Path(__file__).resolve().parent.parent.parent.parent
    index_ts_path = root / "apps" / "cron-dispatcher" / "src" / "index.ts"

    assert index_ts_path.exists(), f"Could not find index.ts file at {index_ts_path}"

    content = index_ts_path.read_text()
    assert "nyHour === 9 && nyMinute === 15" in content, (
        "Expected index.ts to check for nyHour === 9 && nyMinute === 15"
    )
    assert "nyHour === 9 && nyMinute === 0" not in content, (
        "Did not expect index.ts to check for 9:00 AM (nyMinute === 0)"
    )


def test_cron_dispatcher_wrangler_triggers():
    """Verify apps/cron-dispatcher/wrangler.jsonc includes minute 15 cron trigger for 9:15 AM ET (13:15 / 14:15 UTC)."""
    root = Path(__file__).resolve().parent.parent.parent.parent
    wrangler_path = root / "apps" / "cron-dispatcher" / "wrangler.jsonc"

    assert wrangler_path.exists(), f"Could not find wrangler.jsonc at {wrangler_path}"

    content = wrangler_path.read_text()
    assert "15 13,14,21 * * MON-FRI" in content or ("15 13,14" in content and "15 21" in content), (
        "Expected wrangler.jsonc to include 15 minute cron triggers for 13:00/14:00 UTC hours"
    )

