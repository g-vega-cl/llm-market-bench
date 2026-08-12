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
