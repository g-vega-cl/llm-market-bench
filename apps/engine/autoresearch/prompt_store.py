"""DB operations for prompt_experiments table.

Includes a small in-process cache for `get_active_prompt`, since it is hit
once per analysis batch on the trading hot path.
"""

import logging
import time
from datetime import UTC, datetime
from typing import Any

from core.db import get_async_supabase_client

logger = logging.getLogger("engine")

# Active-prompt cache (per-process, TTL'd). Cleared on any save_variant /
# revert_to_previous so the running engine picks up the new variant.
_CACHE_TTL_SECONDS = 60
_active_cache: dict[str, tuple[float, str | None]] = {}


def clear_active_prompt_cache() -> None:
    """Drop the active-prompt cache.

    Called automatically after save_variant / revert_to_previous. Exposed for
    tests and for callers that need a fresh read.
    """
    _active_cache.clear()


async def get_active_prompt(
    prompt_name: str = "CORE_ANALYSIS_SYSTEM_PROMPT",
    is_backtest: bool = False,
    track_id: str = "track_default",
) -> str | None:
    cache_key = f"{prompt_name}:{track_id}:{is_backtest}"
    cached = _active_cache.get(cache_key)
    now = time.monotonic()
    if not is_backtest and cached is not None and (now - cached[0]) < _CACHE_TTL_SECONDS:
        return cached[1]

    sb_client = await get_async_supabase_client()
    query = (
        sb_client.table("prompt_experiments")
        .select("prompt_content")
        .eq("status", "active")
        .eq("prompt_name", prompt_name)
        .eq("is_backtest", is_backtest)
    )
    if track_id:
        query = query.eq("track_id", track_id)

    res = await query.maybe_single().execute()

    if not res or not hasattr(res, "data") or not res.data or isinstance(res.data, dict) and ("message" in res.data or "code" in res.data):
        logger.info("No active prompt found for track_id=%s, prompt_name=%s", track_id, prompt_name)
        return None

    content = res.data.get("prompt_content") if isinstance(res.data, dict) else None
    if not is_backtest:
        _active_cache[cache_key] = (now, content)
    return content


async def get_active_variant(
    prompt_name: str = "CORE_ANALYSIS_SYSTEM_PROMPT",
    is_backtest: bool = False,
    track_id: str = "track_default",
) -> dict | None:
    """Retrieve the full database row/dictionary of the currently active variant for a track."""
    sb_client = await get_async_supabase_client()
    query = (
        sb_client.table("prompt_experiments")
        .select("*")
        .eq("status", "active")
        .eq("prompt_name", prompt_name)
        .eq("is_backtest", is_backtest)
    )
    if track_id:
        query = query.eq("track_id", track_id)

    res = await query.maybe_single().execute()

    if not res or not hasattr(res, "data") or not res.data or isinstance(res.data, dict) and ("message" in res.data or "code" in res.data):
        return None

    return res.data if isinstance(res.data, dict) else None


async def update_variant_metrics(variant_tag: str, metrics: dict) -> None:
    """Update the metrics for a specific prompt variant by its variant tag."""
    sb_client = await get_async_supabase_client()
    await sb_client.table("prompt_experiments").update({"metrics": metrics}).eq("variant_tag", variant_tag).execute()
    logger.info("Updated variant %s metrics in the database", variant_tag)


async def save_variant(
    prompt_content: str,
    prompt_name: str,
    week_start: str,
    week_end: str,
    metrics: dict,
    change_description: str,
    experiment_type: str,
    research_output: dict | None = None,
    parent_tag: str | None = None,
    is_backtest: bool = False,
    track_id: str = "track_default",
) -> str:
    sb_client = await get_async_supabase_client()

    now = datetime.now(UTC)
    tag = f"v{now.strftime('%Y%m%d-%H%M%S')}"
    if is_backtest:
        tag = f"backtest-{tag}"

    insert_data: dict[str, Any] = {
        "variant_tag": tag,
        "prompt_name": prompt_name,
        "prompt_content": prompt_content,
        "week_start": week_start,
        "week_end": week_end,
        "metrics": metrics,
        "status": "active",
        "experiment_type": experiment_type,
        "parent_tag": parent_tag,
        "change_description": change_description,
        "research_output": research_output,
        "is_backtest": is_backtest,
        "track_id": track_id,
    }

    # INSERT first — if this fails, nothing is lost.
    await sb_client.table("prompt_experiments").insert(insert_data).execute()

    # NOW update parent variant to baseline (if it exists) scoped to track_id
    if parent_tag:
        parent_query = (
            sb_client.table("prompt_experiments")
            .update({"status": "baseline"})
            .eq("variant_tag", parent_tag)
            .eq("is_backtest", is_backtest)
        )
        if track_id:
            parent_query = parent_query.eq("track_id", track_id)
        await parent_query.execute()

    # Demote all other active/baseline variants for this track to saved
    demote_query = (
        sb_client.table("prompt_experiments")
        .update({"status": "saved"})
        .in_("status", ["active", "baseline"])
        .eq("prompt_name", prompt_name)
        .eq("is_backtest", is_backtest)
        .neq("variant_tag", tag)
        .neq("variant_tag", parent_tag or "")
    )
    if track_id:
        demote_query = demote_query.eq("track_id", track_id)
    await demote_query.execute()

    clear_active_prompt_cache()
    logger.info("Saved prompt variant %s for track %s (type=%s, is_backtest=%s)", tag, track_id, experiment_type, is_backtest)
    return tag


async def get_previous_variants(
    limit: int = 5,
    prompt_name: str = "CORE_ANALYSIS_SYSTEM_PROMPT",
    is_backtest: bool = False,
    track_id: str = "track_default",
) -> list[dict]:
    sb_client = await get_async_supabase_client()
    query = (
        sb_client.table("prompt_experiments")
        .select("*")
        .eq("prompt_name", prompt_name)
        .eq("is_backtest", is_backtest)
    )
    if track_id:
        query = query.eq("track_id", track_id)

    res = await query.order("created_at", desc=True).limit(limit).execute()

    if not res or not hasattr(res, "data") or isinstance(res.data, dict):
        return []
    return res.data or []


async def get_all_time_baseline(
    prompt_name: str = "CORE_ANALYSIS_SYSTEM_PROMPT",
    is_backtest: bool = False,
    track_id: str = "track_default",
) -> dict | None:
    """Return the prompt variant with the highest score achieved so far among pull-based variants for a track."""
    sb_client = await get_async_supabase_client()
    query = (
        sb_client.table("prompt_experiments")
        .select("*")
        .eq("prompt_name", prompt_name)
        .eq("is_backtest", is_backtest)
    )
    if track_id:
        query = query.eq("track_id", track_id)

    res = await query.execute()

    if not res or not hasattr(res, "data") or not res.data or isinstance(res.data, dict):
        return None

    best_variant = None
    max_score = -float("inf")

    for v in res.data:
        # Require variant to be pull-native (has research_output containing selected_tools)
        ro = v.get("research_output")
        if isinstance(ro, str):
            import json

            try:
                ro = json.loads(ro)
            except (json.JSONDecodeError, TypeError):
                ro = {}

        if not isinstance(ro, dict) or not ro.get("selected_tools"):
            continue

        m = v.get("metrics", {})
        if isinstance(m, str):
            import json

            try:
                m = json.loads(m)
            except (json.JSONDecodeError, TypeError):
                m = {}
        score = m.get("score")
        if score is not None and (best_variant is None or score > max_score):
            max_score = score
            best_variant = v

    return best_variant


async def get_baseline_metrics(
    prompt_name: str = "CORE_ANALYSIS_SYSTEM_PROMPT", is_backtest: bool = False, track_id: str = "track_default"
) -> dict | None:
    """Legacy helper: now returns metrics of the all-time baseline for a given track."""
    baseline = await get_all_time_baseline(prompt_name, is_backtest=is_backtest, track_id=track_id)
    return baseline["metrics"] if baseline else None


async def revert_to_previous(
    prompt_name: str = "CORE_ANALYSIS_SYSTEM_PROMPT", is_backtest: bool = False, track_id: str = "track_default"
) -> str | None:
    sb_client = await get_async_supabase_client()
    query = (
        sb_client.table("prompt_experiments")
        .update({"status": "crashed"})
        .eq("status", "active")
        .eq("prompt_name", prompt_name)
        .eq("is_backtest", is_backtest)
    )
    if track_id:
        await query.eq("track_id", track_id).execute()
    else:
        await query.execute()

    select_query = (
        sb_client.table("prompt_experiments")
        .select("variant_tag")
        .eq("prompt_name", prompt_name)
        .eq("is_backtest", is_backtest)
        .in_("status", ["baseline", "saved"])
    )
    if track_id:
        select_query = select_query.eq("track_id", track_id)

    kept = await select_query.order("created_at", desc=True).limit(1).maybe_single().execute()

    if kept and kept.data:
        tag = kept.data["variant_tag"]
        await (
            sb_client.table("prompt_experiments")
            .update({"status": "active"})
            .eq("prompt_name", prompt_name)
            .eq("variant_tag", tag)
            .eq("is_backtest", is_backtest)
            .execute()
        )
        clear_active_prompt_cache()
        logger.info("Reverted to previous prompt variant: %s", tag)
        return tag

    logger.warning("No previous baseline/saved variant to revert to (prompt_name=%s)", prompt_name)
    return None


async def revert_to_baseline(
    prompt_name: str = "CORE_ANALYSIS_SYSTEM_PROMPT", is_backtest: bool = False, track_id: str = "track_default"
) -> str | None:
    """Revert the active prompt to the all-time baseline (best score ever).

    Used when the current experiment underperforms vs the baseline.
    Marks the current active as 'discarded' (not 'crashed' — it didn't crash,
    it just failed to beat the baseline) and promotes the baseline variant
    to 'active'.

    Returns the baseline variant_tag, or None if no baseline exists.
    """
    baseline = await get_all_time_baseline(prompt_name, is_backtest=is_backtest, track_id=track_id)
    if baseline is None:
        logger.warning("No baseline to revert to (prompt_name=%s, track_id=%s)", prompt_name, track_id)
        return None

    baseline_tag = baseline["variant_tag"]
    sb_client = await get_async_supabase_client()

    # Check if baseline is already active — nothing to do.
    active_query = (
        sb_client.table("prompt_experiments")
        .select("variant_tag")
        .eq("prompt_name", prompt_name)
        .eq("status", "active")
        .eq("is_backtest", is_backtest)
    )
    if track_id:
        active = await active_query.eq("track_id", track_id).maybe_single().execute()
    else:
        active = await active_query.maybe_single().execute()

    if active and active.data and active.data["variant_tag"] == baseline_tag:
        logger.info("Baseline %s is already active. No revert needed.", baseline_tag)
        return baseline_tag

    # Demote current active (if any) to 'discarded' — it wasn't a crash, just
    # an experiment that failed to beat the baseline.
    demote_query = (
        sb_client.table("prompt_experiments")
        .update({"status": "discarded"})
        .eq("status", "active")
        .eq("prompt_name", prompt_name)
        .eq("is_backtest", is_backtest)
    )
    if track_id:
        await demote_query.eq("track_id", track_id).execute()
    else:
        await demote_query.execute()

    # Promote the baseline to active.
    promote_query = (
        sb_client.table("prompt_experiments")
        .update({"status": "active"})
        .eq("prompt_name", prompt_name)
        .eq("variant_tag", baseline_tag)
        .eq("is_backtest", is_backtest)
    )
    if track_id:
        await promote_query.eq("track_id", track_id).execute()
    else:
        await promote_query.execute()

    clear_active_prompt_cache()
    logger.info("Reverted to baseline prompt variant: %s", baseline_tag)
    return baseline_tag

