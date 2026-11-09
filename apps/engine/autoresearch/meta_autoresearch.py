"""Monthly Meta-Autoresearcher (Mutation Yield Ratchet)."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger("engine")

META_PROMPT_NAME = "META_AUTORESEARCH_PROGRAM"
META_TRACK_ID = "meta_autoresearch"
TRACKED_PROMPT_NAMES = ["CORE_ANALYSIS_SYSTEM_PROMPT", "DAILY_PREDICTOR_PROMPT"]

DEFAULT_META_MUTATION_DIRECTIVES = (
    "## How to Improve the Prompt\n"
    "- **The Ratchet Principle**: Build upon the Baseline Prompt (All-Time Best) and isolate regressions.\n"
    "- **Anti-Whiplash Symmetry**: Never over-correct to single-week directional noise; require symmetric hurdles.\n"
    "- **Empirical Block Discipline**: Prioritize modular prompt blocks with verified positive Beat Rates in the 30-day leaderboard.\n"
    "- **Causal Postmortem Grounding**: Target systemic failure modes confirmed across multiple sessions.\n"
)

# 24-hour in-memory cache for active directives and empirical leaderboard
_META_DIRECTIVES_CACHE: dict[str, Any] = {"timestamp": 0.0, "value": None, "ttl_seconds": 86400.0}


def clear_meta_directives_cache() -> None:
    """Clear in-memory cached active meta directives and empirical leaderboard."""
    global _META_DIRECTIVES_CACHE
    _META_DIRECTIVES_CACHE = {"timestamp": 0.0, "value": None, "ttl_seconds": 86400.0}


class MetaAutoresearchResponse(BaseModel):
    """Structured output returned by the monthly meta-autoresearcher LLM."""

    new_meta_directives: str = Field(..., description="Updated meta-researcher mutation instructions.")
    change_description: str = Field(..., description="One sentence explaining what changed and why.")
    research_insight: str = Field(..., description="Durable meta-lesson on blocks or mutation habits.")
    confidence: int = Field(ge=0, le=100, description="Confidence in this meta-directive update (0-100).")


def _parse_json_field(val: Any) -> dict[str, Any]:
    if isinstance(val, dict):
        return val
    if isinstance(val, str):
        try:
            parsed = json.loads(val)
            return parsed if isinstance(parsed, dict) else {}
        except (json.JSONDecodeError, TypeError):
            logger.exception("Failed to parse JSON field in meta_autoresearch.")
            return {}
    return {}


def compute_monthly_mutation_yield(experiments: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute Mutation Yield metrics across 30-day evaluated weekly prompt experiments."""
    score_by_tag: dict[str, float] = {}
    for row in experiments:
        m = _parse_json_field(row.get("metrics"))
        sc = m.get("score", m.get("composite"))
        if row.get("variant_tag") and isinstance(sc, (int, float)):
            score_by_tag[str(row["variant_tag"])] = float(sc)

    evaluated_mutations: list[dict[str, Any]] = []
    beat_count = discarded_count = crash_count = 0
    clamped_deltas: list[float] = []

    for row in experiments:
        parent_tag = row.get("parent_tag")
        status = str(row.get("status") or "").lower()
        if row.get("is_backtest") or not parent_tag:
            continue
        metrics = _parse_json_field(row.get("metrics"))
        ro = _parse_json_field(row.get("research_output"))
        raw_score = metrics.get("score", metrics.get("composite"))
        if raw_score is None and status == "active":
            continue

        score_val = float(raw_score) if raw_score is not None else (-15.0 if status == "crashed" else 0.0)
        parent_score = metrics.get("baseline_score", ro.get("baseline_score", score_by_tag.get(str(parent_tag))))
        is_crashed = status == "crashed"

        if is_crashed:
            is_beat = False
            crash_count += 1
        elif status == "discarded":
            is_beat = False
            discarded_count += 1
        elif status == "baseline":
            is_beat = True
            beat_count += 1
        elif parent_score is not None:
            is_beat = score_val >= float(parent_score)
            beat_count += 1 if is_beat else 0
            discarded_count += 0 if is_beat else 1
        else:
            continue

        fallback_d = 5.0 if is_beat else (-15.0 if is_crashed else -5.0)
        raw_delta = (score_val - float(parent_score)) if parent_score is not None else fallback_d
        clamped_delta = max(-15.0, min(15.0, raw_delta))
        clamped_deltas.append(clamped_delta)
        insight = ro.get("research_insight") or row.get("change_description") or ""
        blocks = ro.get("selected_prompt_blocks") or []
        evaluated_mutations.append(
            {
                "variant_tag": row.get("variant_tag"),
                "prompt_name": row.get("prompt_name"),
                "track_id": row.get("track_id"),
                "experiment_type": row.get("experiment_type") or "incremental",
                "is_beat": is_beat,
                "is_crashed": is_crashed,
                "score": round(score_val, 4),
                "clamped_delta": round(clamped_delta, 4),
                "selected_prompt_blocks": blocks,
                "research_insight": insight,
            }
        )

    total = len(evaluated_mutations)
    beat_rate_pct = (beat_count / total) * 100.0 if total else 0.0
    mean_delta = sum(clamped_deltas) / total if total else 0.0
    norm_delta_score = ((mean_delta + 15.0) / 30.0) * 100.0 if total else 0.0
    non_crash_rate_pct = ((total - crash_count) / total) * 100.0 if total else 0.0
    yield_score = ((0.50 * beat_rate_pct) + (0.35 * norm_delta_score) + (0.15 * non_crash_rate_pct)) if total else 0.0
    return {
        "score": round(float(yield_score), 4),
        "total_evaluated": total,
        "beat_count": beat_count,
        "discarded_count": discarded_count,
        "crash_count": crash_count,
        "beat_rate_pct": round(float(beat_rate_pct), 2),
        "mean_clamped_delta": round(float(mean_delta), 4),
        "non_crash_rate_pct": round(float(non_crash_rate_pct), 2),
        "evaluated_mutations": evaluated_mutations,
    }


def _summarize_bucket(
    stats_map: dict[str, dict[str, Any]], key_name: str, shrink_k: float = 4.0
) -> list[dict[str, Any]]:
    rows = []
    for k, st in stats_map.items():
        uses = st["uses"]
        beats = st["beats"]
        raw_rate = round((beats / uses) * 100.0, 1) if uses > 0 else 0.0
        # Bayesian shrinkage toward 50.0% prior: shrunk = 50.0 + (raw - 50.0) * (uses / (uses + k))
        shrunk_rate = round(50.0 + (raw_rate - 50.0) * (uses / (uses + shrink_k)), 1) if uses > 0 else 50.0
        mean_delta = round(sum(st["deltas"]) / uses, 2) if uses > 0 else 0.0
        rows.append(
            {
                key_name: k,
                "uses": uses,
                "beats": beats,
                "beat_rate_pct": raw_rate,
                "shrunk_beat_rate_pct": shrunk_rate,
                "mean_score_delta": mean_delta,
            }
        )
    rows.sort(key=lambda x: (x["shrunk_beat_rate_pct"], x["mean_score_delta"], x["uses"]), reverse=True)
    return rows


def compute_block_and_type_leaderboard(experiments: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate 30-day empirical beat rates and score deltas per prompt block and experiment type."""
    yield_summary = compute_monthly_mutation_yield(experiments)
    block_stats: dict[str, dict[str, Any]] = {}
    type_stats: dict[str, dict[str, Any]] = {}

    for m in yield_summary["evaluated_mutations"]:
        is_beat, delta = bool(m["is_beat"]), float(m["clamped_delta"])
        exp_type = str(m.get("experiment_type") or "incremental").lower()
        t_entry = type_stats.setdefault(exp_type, {"uses": 0, "beats": 0, "deltas": []})
        t_entry["uses"] += 1
        t_entry["beats"] += 1 if is_beat else 0
        t_entry["deltas"].append(delta)

        for b_id in m.get("selected_prompt_blocks") or []:
            if b_id:
                b_entry = block_stats.setdefault(str(b_id), {"uses": 0, "beats": 0, "deltas": []})
                b_entry["uses"] += 1
                b_entry["beats"] += 1 if is_beat else 0
                b_entry["deltas"].append(delta)

    return {
        "blocks": _summarize_bucket(block_stats, "block_id"),
        "experiment_types": _summarize_bucket(type_stats, "experiment_type"),
        "yield_summary": {k: v for k, v in yield_summary.items() if k != "evaluated_mutations"},
    }


def format_empirical_meta_leaderboard(leaderboard: dict[str, Any]) -> str:
    """Format empirical 30-day block and mutation-type performance as Markdown."""
    ys = leaderboard.get("yield_summary") or {}
    blocks = leaderboard.get("blocks") or []
    exp_types = leaderboard.get("experiment_types") or []
    if not blocks and not exp_types:
        return ""

    lines = [
        "### EMPIRICAL 30-DAY META-AUTORESEARCH LEADERBOARD",
        f"- **Cross-Track Mutation Yield Score**: {ys.get('score', 0.0):.2f} "
        f"(Beat Rate: {ys.get('beat_rate_pct', 0.0):.1f}%, "
        f"Mean Clamped Δ: {ys.get('mean_clamped_delta', 0.0):+.2f}, "
        f"Non-Crash Rate: {ys.get('non_crash_rate_pct', 0.0):.1f}%)",
    ]
    if exp_types:
        parts = [
            f"`{t['experiment_type']}`: {t['beat_rate_pct']:.1f}% beat rate ({t['beats']}/{t['uses']}, Δ {t['mean_score_delta']:+.2f})"
            for t in exp_types
        ]
        lines.append("- **Mutation Mode Yield**: " + " | ".join(parts))
    if blocks:
        lines.append("\n| Prompt Block ID | Uses | Baseline Beats | Beat Rate % | Shrunk Rate % | Mean Score Δ |")
        lines.append("|---|---:|---:|---:|---:|---:|")
        for b in blocks:
            lines.append(
                f"| `{b['block_id']}` | {b['uses']} | {b['beats']} | {b['beat_rate_pct']:.1f}% | {b.get('shrunk_beat_rate_pct', b['beat_rate_pct']):.1f}% | {b['mean_score_delta']:+.2f} |"
            )
    return "\n".join(lines)


def split_research_program(program_text: str) -> tuple[str, str, str]:
    """Split `program.md` into (frozen_header, mutable_heuristics, frozen_footer)."""
    start_marker, end_marker = "## How to Improve the Prompt", "## Toolbox: Available Trading Agent Tools"
    if start_marker in program_text and end_marker in program_text:
        before_start, rest = program_text.split(start_marker, 1)
        mutable_body, after_end = rest.split(end_marker, 1)
        return before_start, f"{start_marker}{mutable_body}".strip(), f"{end_marker}{after_end}"
    return program_text, DEFAULT_META_MUTATION_DIRECTIVES, ""


def splice_research_program(program_text: str, meta_directives: str) -> str:
    """Replace the mutable heuristics section in program.md with active meta-directives."""
    before_start, _, after_end = split_research_program(program_text)
    clean_directives = meta_directives.strip()
    if after_end:
        return f"{before_start}{clean_directives}\n\n{after_end}"
    return f"{program_text}\n\n{clean_directives}"


def should_run_monthly_meta_autoresearch(
    today: date, existing_meta_variants: list[dict[str, Any]], force: bool = False
) -> bool:
    """Return True on the first weekly cycle of the calendar month (days 1..7) if not yet run this month."""
    if force:
        return True
    if today.day > 7:
        return False
    month_prefix = f"{today.year:04d}-{today.month:02d}"
    return all(
        str(v.get("week_start") or v.get("created_at") or "")[:7] != month_prefix for v in existing_meta_variants
    )


def get_active_meta_directives_sync(client: Any = None, lookback_days: int = 30) -> str:
    """Synchronously fetch active monthly meta-directives and 30-day empirical block leaderboard (cached)."""
    import time

    now = time.time()
    if (
        _META_DIRECTIVES_CACHE["value"] is not None
        and (now - _META_DIRECTIVES_CACHE["timestamp"]) < _META_DIRECTIVES_CACHE["ttl_seconds"]
    ):
        return str(_META_DIRECTIVES_CACHE["value"])

    if client is None:
        try:
            from core.db import get_supabase_client

            client = get_supabase_client()
        except Exception:
            logger.exception("Could not initialize Supabase client for meta directives; using default directives.")
            return DEFAULT_META_MUTATION_DIRECTIVES

    directives, leaderboard_md = DEFAULT_META_MUTATION_DIRECTIVES, ""
    try:
        q = client.table("prompt_experiments").select("prompt_content").eq("prompt_name", META_PROMPT_NAME)
        resp = q.eq("track_id", META_TRACK_ID).eq("status", "active").order("created_at", desc=True).limit(1).execute()
        if resp and resp.data and isinstance(resp.data, list) and resp.data[0].get("prompt_content"):
            directives = str(resp.data[0]["prompt_content"]).strip()
    except Exception:
        logger.exception("Error querying active META_AUTORESEARCH_PROGRAM; falling back to default meta directives.")

    try:
        cutoff = (datetime.now(UTC).date() - timedelta(days=lookback_days)).isoformat()
        cols = "variant_tag,prompt_name,track_id,parent_tag,status,experiment_type,metrics,research_output,is_backtest"
        eq = client.table("prompt_experiments").select(cols).in_("prompt_name", TRACKED_PROMPT_NAMES)
        exp_resp = eq.gte("week_start", cutoff).execute()
        if exp_resp and isinstance(exp_resp.data, list) and exp_resp.data:
            leaderboard_md = format_empirical_meta_leaderboard(compute_block_and_type_leaderboard(exp_resp.data))
    except Exception:
        logger.exception("Error computing 30-day empirical meta leaderboard; continuing with directives only.")

    result = f"{directives}\n\n{leaderboard_md}" if leaderboard_md else directives
    _META_DIRECTIVES_CACHE["timestamp"] = now
    _META_DIRECTIVES_CACHE["value"] = result
    return result


async def run_monthly_meta_autoresearch(
    client: Any = None,
    meta_llm_client: Any = None,
    today: date | None = None,
    lookback_days: int = 30,
    dry_run: bool = False,
    force: bool = False,
) -> dict[str, Any] | None:
    """Execute the monthly meta-autoresearcher ratchet over the past 30 days of weekly prompt experiments."""
    today = today or datetime.now(UTC).date()
    if client is None:
        from core.db import get_supabase_client

        client = get_supabase_client()

    meta_q = client.table("prompt_experiments").select("*").eq("prompt_name", META_PROMPT_NAME)
    meta_resp = meta_q.eq("track_id", META_TRACK_ID).order("created_at", desc=True).execute()
    meta_variants = meta_resp.data if (meta_resp and isinstance(meta_resp.data, list)) else []
    if not should_run_monthly_meta_autoresearch(today, meta_variants, force=force):
        return None

    cutoff_date = (today - timedelta(days=lookback_days)).isoformat()
    exp_q = client.table("prompt_experiments").select("*").in_("prompt_name", TRACKED_PROMPT_NAMES)
    exp_resp = exp_q.gte("week_start", cutoff_date).execute()
    experiments = exp_resp.data if (exp_resp and isinstance(exp_resp.data, list)) else []
    yield_metrics = compute_monthly_mutation_yield(experiments)
    if yield_metrics["total_evaluated"] == 0:
        return None

    leaderboard_md = format_empirical_meta_leaderboard(compute_block_and_type_leaderboard(experiments))
    current_score = yield_metrics["score"]

    active_meta = next((v for v in meta_variants if v.get("status") == "active"), None)
    best_baseline, best_baseline_score = None, -float("inf")
    for v in meta_variants:
        if active_meta and v.get("variant_tag") == active_meta.get("variant_tag"):
            continue
        sc = _parse_json_field(v.get("metrics")).get("score")
        if sc is not None and float(sc) > best_baseline_score:
            best_baseline_score, best_baseline = float(sc), v

    current_directives = str((active_meta or {}).get("prompt_content") or DEFAULT_META_MUTATION_DIRECTIVES).strip()
    parent_tag = active_meta["variant_tag"] if active_meta else None
    ratchet_action = "promoted_to_baseline"
    pe_tbl = client.table("prompt_experiments")

    if active_meta and not dry_run:
        pe_tbl.update({"metrics": yield_metrics}).eq("variant_tag", active_meta["variant_tag"]).execute()

    if best_baseline is not None and current_score < best_baseline_score:
        ratchet_action = "reverted_to_baseline"
        if active_meta and not dry_run:
            pe_tbl.update({"status": "discarded"}).eq("variant_tag", active_meta["variant_tag"]).execute()
        current_directives = str(best_baseline.get("prompt_content") or DEFAULT_META_MUTATION_DIRECTIVES).strip()
        parent_tag = best_baseline["variant_tag"]
    elif active_meta and not dry_run:
        pe_tbl.update({"status": "baseline"}).eq("variant_tag", active_meta["variant_tag"]).execute()

    owns_llm = meta_llm_client is None
    if owns_llm:
        from core.llm.clients import get_deepseek_client

        meta_llm_client = get_deepseek_client()

    insights = [
        f"- [{m['prompt_name']}:{m['track_id']}] ({'BEAT' if m['is_beat'] else 'MISS'}, Δ {m['clamped_delta']:+.2f}): {m['research_insight']}"
        for m in yield_metrics["evaluated_mutations"][:12]
        if m.get("research_insight")
    ]
    meta_prompt = (
        "You are the Monthly Meta-Autoresearcher supervising the weekly Portfolio and Daily S&P Predictor autoresearchers.\n"
        "Maximize **Mutation Yield** (share of weekly mutations beating their track baseline without crashing or whiplash).\n\n"
        f"### CURRENT META-AUTORESEARCH DIRECTIVES:\n```markdown\n{current_directives}\n```\n\n"
        f"{leaderboard_md}\n\n"
        f"### 30-DAY TRACK MUTATION OUTCOMES:\n{chr(10).join(insights) or 'No track insights recorded.'}\n\n"
        "Rewrite `new_meta_directives` to highlight high-yield prompt blocks and mutation modes while enforcing anti-whiplash symmetry."
    )

    try:
        from core.config import AUTORESEARCH_MODEL

        call = meta_llm_client.chat.completions.create(
            model=AUTORESEARCH_MODEL,
            response_model=MetaAutoresearchResponse,
            messages=[{"role": "user", "content": meta_prompt}],
        )
        resp = await call if asyncio.iscoroutine(call) or hasattr(call, "__await__") else call
    except Exception:
        logger.exception("Monthly meta-autoresearch LLM call failed.")
        return None
    finally:
        if owns_llm:
            from core.llm.clients import close_client

            await close_client(meta_llm_client, "deepseek")

    new_directives = resp.new_meta_directives.strip()
    new_tag = f"meta-ar-{today.strftime('%Y%m')}-{uuid.uuid4().hex[:6]}"
    if not dry_run:
        demote_q = pe_tbl.update({"status": "saved"}).eq("prompt_name", META_PROMPT_NAME)
        demote_q.eq("track_id", META_TRACK_ID).eq("status", "active").execute()
        row_payload = {
            "variant_tag": new_tag,
            "prompt_name": META_PROMPT_NAME,
            "prompt_content": new_directives,
            "track_id": META_TRACK_ID,
            "week_start": today.isoformat(),
            "week_end": (today + timedelta(days=30)).isoformat(),
            "metrics": {},
            "status": "active",
            "experiment_type": "incremental",
            "parent_tag": parent_tag,
            "change_description": resp.change_description,
            "research_output": {
                "research_insight": resp.research_insight,
                "confidence": resp.confidence,
                "selected_tools": ["meta_audit"],
                "prior_mutation_yield": yield_metrics,
            },
        }
        pe_tbl.insert(row_payload).execute()
        clear_meta_directives_cache()

    return {
        "variant_tag": new_tag,
        "parent_tag": parent_tag,
        "ratchet_action": ratchet_action,
        "mutation_yield": yield_metrics,
        "new_meta_directives": new_directives,
        "research_insight": resp.research_insight,
    }
