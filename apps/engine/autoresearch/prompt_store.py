"""DB operations for prompt_experiments table.

Includes a small in-process cache for `get_active_prompt`, since it is hit
once per analysis batch on the trading hot path.
"""

import logging
import time
from datetime import datetime, timezone
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
            prompt_name
        )
        return None

    content = res.data["prompt_content"] if res.data else None
    _active_cache[prompt_name] = (now, content)
    return content


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

    now = datetime.now(timezone.utc)
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

    # NOW demote the previous active variants.
    # neq() ensures we don't demote the row we just inserted.
    await sb_client.table("prompt_experiments").update({"status": "kept"}).eq(
        "status", "active"
    ).eq("prompt_name", prompt_name).neq("variant_tag", tag).execute()

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


async def get_baseline_metrics(prompt_name: str = "CORE_ANALYSIS_SYSTEM_PROMPT") -> dict | None:
    sb_client = await get_async_supabase_client()
    res = await (
        sb_client.table("prompt_experiments")
        .select("metrics")
        .eq("prompt_name", prompt_name)
        .eq("experiment_type", "baseline")
        .order("created_at", desc=True)
        .limit(1)
        .maybe_single()
        .execute()
    )
    if res and res.data:
        return res.data["metrics"]
    return None


async def revert_to_previous(prompt_name: str = "CORE_ANALYSIS_SYSTEM_PROMPT") -> str | None:
    sb_client = await get_async_supabase_client()
    await sb_client.table("prompt_experiments").update({"status": "crashed"}).eq(
        "status", "active"
    ).eq("prompt_name", prompt_name).execute()

    kept = await (
        sb_client.table("prompt_experiments")
        .select("variant_tag")
        .eq("prompt_name", prompt_name)
        .eq("status", "kept")
        .order("created_at", desc=True)
        .limit(1)
        .maybe_single()
        .execute()
    )

    if kept and kept.data:
        tag = kept.data["variant_tag"]
        await sb_client.table("prompt_experiments").update({"status": "active"}).eq(
            "prompt_name", prompt_name
        ).eq("variant_tag", tag).execute()
        clear_active_prompt_cache()
        logger.info("Reverted to previous prompt variant: %s", tag)
        return tag

    logger.warning("No previous kept variant to revert to (prompt_name=%s)", prompt_name)
    return None
