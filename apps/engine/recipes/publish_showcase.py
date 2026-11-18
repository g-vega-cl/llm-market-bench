"""Publish a curated public showcase backtest for the read-only /recipes-demo page.

The showcase is a *pin*: one row in ``public.recipe_showcase`` naming the job the
public page renders, independent of which recipe rows happen to be public. The
recipe is also flagged ``is_public`` so the permissive SELECT policy covers the
run, but the pin — not that flag — decides what visitors see.

Usage::

    python3 -m recipes.publish_showcase --job <job-id> --headline "..."
    python3 -m recipes.publish_showcase --job <job-id> --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

# Ensure apps/engine is on sys.path when invoked directly as CLI script
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from recipes.push_schema import is_valid_single_stage_graph

SHOWCASE_PIN_ROW_ID = 1
SHOWCASE_URL = "https://www.benchify.dev/recipes-demo"
REQUIRED_DAY_STEPS = 30
ARCHIVE_DB_HOST = "benchify-archive-db.clvg.uk"
LOCAL_HOSTS = {"localhost", "127.0.0.1"}
# The worker bumps ``strategy_recipes.updated_at`` (trial_count) seconds after a
# run settles, so only an edit clearly after completion means the graph drifted.
GRAPH_EDIT_GRACE = timedelta(minutes=10)


class ShowcasePublishError(RuntimeError):
    """Raised when a job is not fit to be published as the public showcase."""


def _fetch_one(sb_client: Any, table: str, row_id: str) -> dict[str, Any] | None:
    res = sb_client.table(table).select("*").eq("id", row_id).limit(1).execute()
    rows = res.data or []
    return rows[0] if rows else None


def _parse_ts(value: Any) -> datetime | None:
    """Parse an ISO timestamp defensively; unparseable input yields ``None``."""
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def validate_showcase_job(
    job: dict[str, Any],
    recipe: dict[str, Any],
) -> dict[str, Any]:
    """Validate one candidate run and return its publish summary.

    Every check fails closed: a broken showcase is worse than the empty sign-in
    card, because the public page cannot tell a visitor the run was invalid.
    """
    if job.get("mode") != "backtest":
        raise ShowcasePublishError(f"Job {job.get('id')} is not a backtest run (mode={job.get('mode')!r})")
    if job.get("status") != "completed":
        raise ShowcasePublishError(f"Job {job.get('id')} is not completed (status={job.get('status')!r})")

    result = job.get("result_json") or {}
    day_steps = result.get("day_steps")
    steps_completed = len(day_steps) if isinstance(day_steps, list) else 0
    # ``days_completed`` alone is not evidence: the public timeline renders the
    # slot array, so a claim without slots must not be publishable.
    if steps_completed < REQUIRED_DAY_STEPS:
        raise ShowcasePublishError(
            f"Job {job.get('id')} only carries {steps_completed} day_steps; "
            f"a showcase needs the full {REQUIRED_DAY_STEPS}-slot window"
        )

    # The queue does not snapshot the graph, so the row we can validate is the
    # current one. Publish only while it still matches what ran.
    completed_at = _parse_ts(job.get("completed_at"))
    updated_at = _parse_ts(recipe.get("updated_at"))
    if completed_at and updated_at and updated_at - completed_at > GRAPH_EDIT_GRACE:
        raise ShowcasePublishError(
            f"Recipe {recipe.get('id')} was edited after job {job.get('id')} completed "
            f"({recipe.get('updated_at')} > {job.get('completed_at')}); "
            "re-run the backtest so the showcase matches the published graph"
        )

    if not is_valid_single_stage_graph(recipe.get("graph_json")):
        raise ShowcasePublishError(f"Recipe {recipe.get('id')} graph is not a single-stage Push v2 strategy")

    # A strategy the owner removed from My Strategies must not become the public
    # showcase: the recipe row still exists, so nothing else would stop this.
    if recipe.get("archived_at"):
        raise ShowcasePublishError(
            f"Recipe {recipe.get('id')} was removed from My Strategies; "
            "restore it in the studio before publishing its run"
        )

    return {
        "job_id": str(job.get("id")),
        "recipe_id": str(recipe.get("id")),
        "recipe_name": recipe.get("name"),
        "day_steps": steps_completed,
        "total_return_pct_net": result.get("total_return_pct_net"),
    }


def publish_showcase(
    sb_client: Any,
    job_id: str,
    headline: str = "",
    dry_run: bool = False,
) -> dict[str, Any]:
    """Pin ``job_id`` as the public showcase, marking its recipe public.

    The pin is written first. Flipping ``is_public`` in a separate statement
    means a failed pin would otherwise leave a public recipe with no pin, which
    the ``/recipes-demo`` fallback heuristic would serve to anonymous visitors.
    """
    job = _fetch_one(sb_client, "recipe_execution_queue", job_id)
    if not job:
        raise ShowcasePublishError(f"Job {job_id} not found")

    recipe_id = job.get("recipe_id")
    if not recipe_id:
        raise ShowcasePublishError(f"Job {job_id} has no recipe_id")

    recipe = _fetch_one(sb_client, "strategy_recipes", str(recipe_id))
    if not recipe:
        raise ShowcasePublishError(f"Recipe {recipe_id} not found")

    summary = validate_showcase_job(job, recipe)
    pin = {
        "id": SHOWCASE_PIN_ROW_ID,
        "job_id": summary["job_id"],
        "recipe_id": summary["recipe_id"],
        "headline": headline,
        "recipe_name": summary["recipe_name"] or "",
        "published_at": datetime.now(UTC).isoformat(),
    }

    if dry_run:
        return {**summary, "pin": pin, "url": SHOWCASE_URL, "dry_run": True}

    try:
        sb_client.table("recipe_showcase").upsert(pin, on_conflict="id").execute()
    except Exception as exc:  # noqa: BLE001 - any client/driver error must fail closed
        raise ShowcasePublishError(f"Failed to write the showcase pin for job {job_id}: {exc}") from exc

    sb_client.table("strategy_recipes").update({"is_public": True}).eq("id", summary["recipe_id"]).execute()

    # postgrest-py's update builder cannot return rows, so read the flag back:
    # a 0-row update (row deleted mid-run) must not be reported as published.
    verify = (
        sb_client.table("strategy_recipes").select("id, is_public").eq("id", summary["recipe_id"]).limit(1).execute()
    )
    row = (verify.data or [None])[0]
    if not row or not row.get("is_public"):
        raise ShowcasePublishError(
            f"Recipe {summary['recipe_id']} update matched 0 rows; "
            "the showcase pin was written but the recipe is not public"
        )

    return {**summary, "pin": pin, "url": SHOWCASE_URL, "dry_run": False}


def _build_client() -> Any:
    """Build the archive-DB client, refusing any ambiguous target.

    Falling back to the shared client would happily write a pin the web read
    path never looks at while still reporting success, so this fails closed.
    """
    url = os.getenv("ARCHIVE_DB_URL") or os.getenv("VITE_ARCHIVE_DB_URL")
    key = os.getenv("ARCHIVE_DB_SERVICE_ROLE_KEY")
    if not url or not key:
        raise ShowcasePublishError(
            "ARCHIVE_DB_URL and ARCHIVE_DB_SERVICE_ROLE_KEY must be set; "
            "refusing to guess which database the showcase lives in"
        )

    host = urlparse(url).hostname or ""
    if host != ARCHIVE_DB_HOST and host not in LOCAL_HOSTS:
        raise ShowcasePublishError(
            f"{url} is not the archive database (expected host {ARCHIVE_DB_HOST}); "
            "refusing to publish the showcase somewhere the site never reads"
        )

    from supabase import create_client

    return create_client(url, key)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Publish a public showcase backtest")
    parser.add_argument("--job", required=True, help="recipe_execution_queue job id")
    parser.add_argument("--headline", default="", help="Optional title shown on /recipes-demo")
    parser.add_argument("--dry-run", action="store_true", help="Validate without writing")
    args = parser.parse_args(argv)

    try:
        outcome = publish_showcase(
            _build_client(),
            args.job,
            headline=args.headline,
            dry_run=args.dry_run,
        )
    except ShowcasePublishError as exc:
        print(f"Refusing to publish: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(outcome, indent=2, default=str))
    if not outcome["dry_run"]:
        print(f"Showcase live at {outcome['url']}")
        # The page is served from a shared cache for 72h (see src/lib/showcase-cache.ts).
        print(
            "Note: the CDN caches /recipes-demo for 72h; re-deploy or clear the CDN "
            "cache to make this publish visible immediately."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
