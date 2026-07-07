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

    # The third cron should be 18:00 UTC (2:00 PM EDT) to provide a safe buffer
    assert "0 18 * * 1-5" in cron_triggers, f"Expected 0 18 * * 1-5 in cron triggers, found: {cron_triggers}"
