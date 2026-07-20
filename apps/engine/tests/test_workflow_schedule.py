"""Tests to verify GitHub Actions workflow schedule configurations."""

from pathlib import Path

import yaml


def test_workflow_schedule():
    """Verify that ingest.yml cron schedules are set correctly with the proper buffer."""
    root = Path(__file__).resolve().parent.parent.parent.parent
    ingest_yml_path = root / ".github" / "workflows" / "ingest.yml"

    assert ingest_yml_path.exists(), f"Could not find workflow file at {ingest_yml_path}"

    with open(ingest_yml_path) as f:
        config = yaml.safe_load(f)

    # PyYAML safe_load parses 'on' as boolean True
    on_key = "on" if "on" in config else True
    schedule = config.get(on_key, {}).get("schedule", [])
    cron_triggers = [trigger.get("cron") for trigger in schedule if isinstance(trigger, dict) and "cron" in trigger]

    # Verify ingest.yml covers both EDT (UTC-4) and EST (UTC-5) offset runs
    assert "35 13,14,15,16 * * 1-5" in cron_triggers, (
        f"Expected 35 13,14,15,16 * * 1-5 in cron triggers, found: {cron_triggers}"
    )
    assert "0 18,19 * * 1-5" in cron_triggers, f"Expected 0 18,19 * * 1-5 in cron triggers, found: {cron_triggers}"


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
