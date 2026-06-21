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


async def get_active_prompt(prompt_name: str = "CORE_ANALYSIS_SYSTEM_PROMPT") -> str | None:
    cached = _active_cache.get(prompt_name)
    now = time.monotonic()
    if cached is not None and (now - cached[0]) < _CACHE_TTL_SECONDS:
        return cached[1]

    sb_client = await get_async_supabase_client()
    res = await (
        sb_client.table("prompt_experiments")
        .select("prompt_content")
        .eq("status", "active")
        .eq("prompt_name", prompt_name)
        .maybe_single()
        .execute()
    )
    if res is None:
        logger.warning(
            "Supabase returned None for active prompt query (prompt_name=%s). "
            "This usually means the table is empty or the row was deleted.",
            prompt_name,
        )
        return None

    content = res.data["prompt_content"] if res.data else None
    _active_cache[prompt_name] = (now, content)
    return content


async def get_active_variant(prompt_name: str = "CORE_ANALYSIS_SYSTEM_PROMPT") -> dict | None:
    """Retrieve the full database row/dictionary of the currently active variant."""
    sb_client = await get_async_supabase_client()
    res = await (
        sb_client.table("prompt_experiments")
        .select("*")
        .eq("status", "active")
        .eq("prompt_name", prompt_name)
        .maybe_single()
        .execute()
    )
    return res.data if res else None


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
) -> str:
    sb_client = await get_async_supabase_client()

    now = datetime.now(UTC)
    tag = f"v{now.strftime('%Y%m%d-%H%M%S')}"

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
    }

    # INSERT first — if this fails, nothing is lost.
    await sb_client.table("prompt_experiments").insert(insert_data).execute()

    # NOW update parent variant to baseline (if it exists), and demote other active/baseline variants to saved
    if parent_tag:
        await (
            sb_client.table("prompt_experiments").update({"status": "baseline"}).eq("variant_tag", parent_tag).execute()
        )
    # Demote all other active/baseline variants to saved
    await (
        sb_client.table("prompt_experiments")
        .update({"status": "saved"})
        .in_("status", ["active", "baseline"])
        .eq("prompt_name", prompt_name)
        .neq("variant_tag", tag)
        .neq("variant_tag", parent_tag or "")
        .execute()
    )

    clear_active_prompt_cache()
    logger.info("Saved prompt variant %s (type=%s)", tag, experiment_type)
    return tag


async def get_previous_variants(limit: int = 5, prompt_name: str = "CORE_ANALYSIS_SYSTEM_PROMPT") -> list[dict]:
    sb_client = await get_async_supabase_client()
    res = await (
        sb_client.table("prompt_experiments")
        .select("*")
        .eq("prompt_name", prompt_name)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    if res is None:
        return []
    return res.data or []


async def get_all_time_baseline(prompt_name: str = "CORE_ANALYSIS_SYSTEM_PROMPT") -> dict | None:
    """Return the prompt variant with the highest score achieved so far."""
    sb_client = await get_async_supabase_client()
    # Fetch all variants for this prompt name. Since it's a weekly loop,
    # the number of rows will remain small (e.g., 52 per year).
    res = await sb_client.table("prompt_experiments").select("*").eq("prompt_name", prompt_name).execute()

    if not res or not res.data:
        return None

    best_variant = None
    max_score = -float("inf")

    for v in res.data:
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


async def get_baseline_metrics(prompt_name: str = "CORE_ANALYSIS_SYSTEM_PROMPT") -> dict | None:
    """Legacy helper: now returns metrics of the all-time baseline."""
    baseline = await get_all_time_baseline(prompt_name)
    return baseline["metrics"] if baseline else None


async def revert_to_previous(prompt_name: str = "CORE_ANALYSIS_SYSTEM_PROMPT") -> str | None:
    sb_client = await get_async_supabase_client()
    await (
        sb_client.table("prompt_experiments")
        .update({"status": "crashed"})
        .eq("status", "active")
        .eq("prompt_name", prompt_name)
        .execute()
    )

    kept = await (
        sb_client.table("prompt_experiments")
        .select("variant_tag")
        .eq("prompt_name", prompt_name)
        .in_("status", ["baseline", "saved"])
        .order("created_at", desc=True)
        .limit(1)
        .maybe_single()
        .execute()
    )

    if kept and kept.data:
        tag = kept.data["variant_tag"]
        await (
            sb_client.table("prompt_experiments")
            .update({"status": "active"})
            .eq("prompt_name", prompt_name)
            .eq("variant_tag", tag)
            .execute()
        )
        clear_active_prompt_cache()
        logger.info("Reverted to previous prompt variant: %s", tag)
        return tag

    logger.warning("No previous baseline/saved variant to revert to (prompt_name=%s)", prompt_name)
    return None


async def revert_to_baseline(prompt_name: str = "CORE_ANALYSIS_SYSTEM_PROMPT") -> str | None:
    """Revert the active prompt to the all-time baseline (best score ever).

    Used when the current experiment underperforms vs the baseline.
    Marks the current active as 'discarded' (not 'crashed' — it didn't crash,
    it just failed to beat the baseline) and promotes the baseline variant
    to 'active'.

    Returns the baseline variant_tag, or None if no baseline exists.
    """
    baseline = await get_all_time_baseline(prompt_name)
    if baseline is None:
        logger.warning("No baseline to revert to (prompt_name=%s)", prompt_name)
        return None

    baseline_tag = baseline["variant_tag"]
    sb_client = await get_async_supabase_client()

    # Check if baseline is already active — nothing to do.
    active = await (
        sb_client.table("prompt_experiments")
        .select("variant_tag")
        .eq("prompt_name", prompt_name)
        .eq("status", "active")
        .maybe_single()
        .execute()
    )
    if active and active.data and active.data["variant_tag"] == baseline_tag:
        logger.info("Baseline %s is already active. No revert needed.", baseline_tag)
        return baseline_tag

    # Demote current active (if any) to 'discarded' — it wasn't a crash, just
    # an experiment that failed to beat the baseline.
    await (
        sb_client.table("prompt_experiments")
        .update({"status": "discarded"})
        .eq("status", "active")
        .eq("prompt_name", prompt_name)
        .execute()
    )

    # Promote the baseline to active.
    await (
        sb_client.table("prompt_experiments")
        .update({"status": "active"})
        .eq("prompt_name", prompt_name)
        .eq("variant_tag", baseline_tag)
        .execute()
    )

    clear_active_prompt_cache()
    logger.info("Reverted to baseline prompt variant: %s", baseline_tag)
    return baseline_tag
