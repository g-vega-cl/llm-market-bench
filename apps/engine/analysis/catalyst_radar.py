"""Catalyst Radar: Combines high-velocity market concepts with calendar triggers.

Implements vector cosine matching and a 4-stage digestion lifecycle:
1. Upcoming (T+1 to T+14 days): Anticipation phase ("1 week from now", "in 3 days", "tomorrow")
2. Active (T+0): Live catalyst day ("today")
3. Digesting (T-1 to T-3 days): Post-event reaction settlement ("digesting, 1 day ago")
4. Expired (T <= -4 days): Historical post-mortem phase (archived)
"""

import json
import math
import re
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import Any

from core.config import logger
from core.db import get_supabase_client


@dataclass
class CatalystRadarItem:
    concept_id: str
    concept_name: str
    velocity_score: float
    catalyst_id: str
    catalyst_title: str
    target_date: str
    days_to_event: int
    stage: str  # "upcoming" | "active" | "digesting" | "expired"
    date_offset_label: str
    impact: str = "NEUTRAL"
    similarity: float = 0.0
    memory_content: str = ""
    related_tickers: list[str] = field(default_factory=list)


def parse_date(date_str: str | None) -> date | None:
    """Parses date from YYYY-MM-DD string or extracts it via regex."""
    if not date_str:
        return None
    match = re.search(r"(\d{4}-\d{2}-\d{2})", str(date_str))
    if not match:
        return None
    try:
        return datetime.strptime(match.group(1), "%Y-%m-%d").date()
    except ValueError:
        return None


def calculate_date_offset(target_date_str: str, ref_date: date | None = None) -> tuple[int, str, str]:
    """Calculates the date offset, stage, and user-facing relative label.

    Returns:
        (delta_days, stage, date_offset_label)
        stage: "upcoming" | "active" | "digesting" | "expired"
    """
    target = parse_date(target_date_str)
    if not target:
        return 0, "expired", "unknown"

    if ref_date is None:
        # Default to UTC/Eastern date
        ref_date = datetime.now(UTC).date()

    delta_days = (target - ref_date).days

    if delta_days > 0:
        stage = "upcoming"
        if delta_days == 1:
            label = "tomorrow"
        elif delta_days == 7:
            label = "1 week from now"
        elif delta_days == 14:
            label = "2 weeks from now"
        elif delta_days % 7 == 0 and delta_days > 14:
            label = f"{delta_days // 7} weeks from now"
        else:
            label = f"in {delta_days} days"
    elif delta_days == 0:
        stage = "active"
        label = "today"
    elif -3 <= delta_days < 0:
        stage = "digesting"
        abs_days = abs(delta_days)
        label = f"digesting, {abs_days} day{'s' if abs_days > 1 else ''} ago"
    else:
        stage = "expired"
        label = "expired"

    return delta_days, stage, label


def parse_vector(vec: Any) -> list[float] | None:
    """Parses a vector from either a JSON string, list of floats/ints, or None."""
    if not vec:
        return None
    if isinstance(vec, str):
        try:
            vec = json.loads(vec)
        except Exception:
            return None
    if isinstance(vec, (list, tuple)):
        try:
            return [float(x) for x in vec]
        except (ValueError, TypeError):
            return None
    return None


def cosine_similarity(vec_a: Any, vec_b: Any) -> float:
    """Computes cosine similarity between two float vectors (list or JSON string)."""
    a_list = parse_vector(vec_a)
    b_list = parse_vector(vec_b)
    if not a_list or not b_list or len(a_list) != len(b_list):
        return 0.0

    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0
    for a, b in zip(a_list, b_list, strict=False):
        dot += a * b
        norm_a += a * a
        norm_b += b * b

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    return dot / (math.sqrt(norm_a) * math.sqrt(norm_b))


def clean_catalyst_title(content: str) -> str:
    """Strips [CALENDAR EVENT] prefix, time tags, and extracts concise title."""
    title = re.sub(r"^\[CALENDAR EVENT\]\s*", "", content, flags=re.IGNORECASE)
    title = re.sub(r"^\([^)]*\)\s*", "", title)
    # If date was prepended like "2026-09-11: ", strip it
    title = re.sub(r"^\d{4}-\d{2}-\d{2}:\s*", "", title)
    # If impact / date suffix exists, split by pipe and take the first part
    if "|" in title:
        title = title.split("|")[0].strip()
    # Extract event headline if separated by colon from body description
    if ":" in title:
        parts = title.split(":", 1)
        if len(parts[0].strip()) > 3:
            title = parts[0].strip()
    return title.strip() or content.strip()


def match_concepts_to_catalysts(
    concepts: list[dict[str, Any]],
    calendar_memories: list[dict[str, Any]],
    ref_date: date | None = None,
    min_velocity: float = 1.2,
    min_similarity: float = 0.35,
    days_ahead: int = 14,
    include_digesting: bool = True,
) -> list[CatalystRadarItem]:
    """Matches active concepts to upcoming and digesting calendar catalysts using vector math."""
    if ref_date is None:
        ref_date = datetime.now(UTC).date()

    # 1. Filter concepts by velocity and vector presence
    valid_concepts = [
        c
        for c in concepts
        if (c.get("velocity_score") or 0.0) >= min_velocity and parse_vector(c.get("concept_vector")) is not None
    ]

    # 2. Filter calendar memories by date window and valid target_date
    valid_memories = []
    for m in calendar_memories:
        t_date = m.get("target_date") or parse_date(m.get("content"))
        if not t_date:
            continue
        delta, stage, label = calculate_date_offset(str(t_date), ref_date)

        # Gating: must not be expired, and within days_ahead forward limit
        if stage == "expired":
            continue
        if stage == "digesting" and not include_digesting:
            continue
        if delta > days_ahead:
            continue

        valid_memories.append((m, str(t_date), delta, stage, label))

    results: list[CatalystRadarItem] = []

    # 3. Compute cross-product similarity
    for c in valid_concepts:
        c_vec = c.get("concept_vector")
        c_name = c.get("concept_name", "")
        c_name_lower = c_name.lower()

        for m, t_date_str, delta, stage, label in valid_memories:
            m_vec = m.get("embedding")
            sim = cosine_similarity(c_vec, m_vec)

            # Keyword / entity overlap boost
            meta = m.get("metadata") or {}
            ticker = meta.get("ticker", "")
            if ticker and (ticker.lower() in c_name_lower or c_name_lower in ticker.lower()):
                sim += 0.15

            if sim >= min_similarity:
                content = m.get("content", "")
                title = clean_catalyst_title(content)
                impact = meta.get("impact") or "NEUTRAL"
                tickers = [ticker] if ticker else []
                if "tickers" in meta and isinstance(meta["tickers"], list):
                    tickers = meta["tickers"]

                results.append(
                    CatalystRadarItem(
                        concept_id=c.get("id", ""),
                        concept_name=c_name,
                        velocity_score=float(c.get("velocity_score", 0.0)),
                        catalyst_id=m.get("id", ""),
                        catalyst_title=title,
                        target_date=t_date_str,
                        days_to_event=delta,
                        stage=stage,
                        date_offset_label=label,
                        impact=impact,
                        similarity=round(sim, 3),
                        memory_content=content,
                        related_tickers=tickers,
                    )
                )

    # 4. Sort: Upcoming / Active / Digesting by chronological proximity, then velocity
    results.sort(key=lambda x: (abs(x.days_to_event), -x.velocity_score))
    return results


def compute_and_store_catalyst_radar(
    sb_client: Any | None = None,
    days_ahead: int = 30,
    min_velocity: float = 1.0,
    min_similarity: float = 0.35,
    ref_date: date | None = None,
) -> int:
    """Pre-computes vector collisions between concepts and calendar triggers, saving to catalyst_radar table."""
    if sb_client is None:
        sb_client = get_supabase_client()

    try:
        # 1. Fetch eligible concepts with velocity >= min_velocity
        concepts_resp = (
            sb_client.table("concept_metrics")
            .select("id, concept_name, concept_vector, velocity_score, mention_count")
            .gte("velocity_score", min_velocity)
            .order("velocity_score", desc=True)
            .limit(100)
            .execute()
        )
        concepts = concepts_resp.data or []

        # 2. Fetch active calendar memories
        memories_resp = (
            sb_client.table("memories")
            .select("id, content, target_date, importance_score, embedding, metadata")
            .eq("status", "ACTIVE")
            .gte("importance_score", 7)
            .not_.is_("target_date", "null")
            .order("created_at", desc=True)
            .limit(100)
            .execute()
        )
        calendar_memories = memories_resp.data or []

        if not concepts or not calendar_memories:
            logger.info("Catalyst radar compute: No concepts or calendar memories found to match.")
            return 0

        # 3. Match using vector cosine similarity
        matches = match_concepts_to_catalysts(
            concepts=concepts,
            calendar_memories=calendar_memories,
            ref_date=ref_date,
            min_velocity=min_velocity,
            min_similarity=min_similarity,
            days_ahead=days_ahead,
            include_digesting=True,
        )

        if not matches:
            logger.info("Catalyst radar compute: No matches met the similarity threshold.")
            return 0

        # 4. Prepare records for upsert
        now_iso = datetime.now(UTC).isoformat()
        records = []
        seen = set()
        for item in matches:
            key = (item.concept_id, item.catalyst_id)
            if key in seen:
                continue
            seen.add(key)
            records.append(
                {
                    "concept_id": item.concept_id,
                    "concept_name": item.concept_name,
                    "velocity_score": item.velocity_score,
                    "catalyst_id": item.catalyst_id,
                    "catalyst_title": item.catalyst_title,
                    "target_date": item.target_date,
                    "impact": item.impact,
                    "similarity": item.similarity,
                    "related_tickers": item.related_tickers,
                    "memory_content": item.memory_content,
                    "updated_at": now_iso,
                }
            )

        # 5. Clean expired entries (> 3 days past) from catalyst_radar
        if ref_date is None:
            ref_date = datetime.now(UTC).date()
        stale_cutoff = (ref_date - timedelta(days=3)).isoformat()
        try:
            sb_client.table("catalyst_radar").delete().lt("target_date", stale_cutoff).execute()
        except Exception as e:
            logger.warning("Could not prune stale catalyst_radar records: %s", e)

        # 6. Upsert records in chunks of 50
        chunk_size = 50
        for i in range(0, len(records), chunk_size):
            chunk = records[i : i + chunk_size]
            sb_client.table("catalyst_radar").upsert(chunk, on_conflict="concept_id,catalyst_id").execute()

        logger.info("Catalyst radar compute: Successfully stored %d collisions.", len(records))
        return len(records)
    except Exception as e:
        logger.exception("Error computing and storing catalyst radar: %s", e)
        return 0


def fetch_catalyst_radar(
    sb_client: Any | None = None,
    days_ahead: int = 14,
    include_digesting: bool = True,
    min_velocity: float = 1.2,
    min_similarity: float = 0.35,
    ref_date: date | None = None,
) -> list[CatalystRadarItem]:
    """Fetches catalyst collisions from Supabase and calculates date lifecycle offsets."""
    if sb_client is None:
        sb_client = get_supabase_client()

    if ref_date is None:
        ref_date = datetime.now(UTC).date()

    try:
        # 1. Try reading from pre-computed catalyst_radar table
        resp = (
            sb_client.table("catalyst_radar")
            .select("*")
            .gte("velocity_score", min_velocity)
            .gte("similarity", min_similarity)
            .order("velocity_score", desc=True)
            .limit(100)
            .execute()
        )
        rows = resp.data or []

        if rows:
            results = []
            for r in rows:
                t_date_str = str(r.get("target_date", ""))
                delta, stage, label = calculate_date_offset(t_date_str, ref_date)

                if stage == "expired":
                    continue
                if stage == "digesting" and not include_digesting:
                    continue
                if delta > days_ahead:
                    continue

                tickers = r.get("related_tickers") or []
                if not isinstance(tickers, list):
                    tickers = []

                results.append(
                    CatalystRadarItem(
                        concept_id=str(r.get("concept_id", "")),
                        concept_name=str(r.get("concept_name", "")),
                        velocity_score=float(r.get("velocity_score", 0.0)),
                        catalyst_id=str(r.get("catalyst_id", "")),
                        catalyst_title=str(r.get("catalyst_title", "")),
                        target_date=t_date_str,
                        days_to_event=delta,
                        stage=stage,
                        date_offset_label=label,
                        impact=str(r.get("impact", "NEUTRAL")),
                        similarity=float(r.get("similarity", 0.0)),
                        memory_content=str(r.get("memory_content", "")),
                        related_tickers=tickers,
                    )
                )

            results.sort(key=lambda x: (abs(x.days_to_event), -x.velocity_score))
            return results

        # 2. Fallback: on-the-fly calculation if catalyst_radar table is empty
        concepts_resp = (
            sb_client.table("concept_metrics")
            .select("id, concept_name, concept_vector, velocity_score, mention_count")
            .gte("velocity_score", min_velocity)
            .order("velocity_score", desc=True)
            .limit(40)
            .execute()
        )
        concepts = concepts_resp.data or []

        memories_resp = (
            sb_client.table("memories")
            .select("id, content, target_date, importance_score, embedding, metadata")
            .eq("status", "ACTIVE")
            .gte("importance_score", 7)
            .not_.is_("target_date", "null")
            .order("created_at", desc=True)
            .limit(60)
            .execute()
        )
        calendar_memories = memories_resp.data or []

        return match_concepts_to_catalysts(
            concepts=concepts,
            calendar_memories=calendar_memories,
            ref_date=ref_date,
            min_velocity=min_velocity,
            min_similarity=min_similarity,
            days_ahead=days_ahead,
            include_digesting=include_digesting,
        )
    except Exception as e:
        logger.exception(f"Error fetching catalyst radar: {e}")
        return []


def format_catalyst_radar_context(
    radar_items: list[CatalystRadarItem],
    detail: bool = False,
    max_items: int = 25,
) -> str:
    """Formats catalyst radar items for LLM consumption."""
    if not radar_items:
        return "No active concept-catalyst collisions found within the specified date range."

    if not detail:
        visible_items = radar_items[:max_items]
        lines = [
            "### Catalyst Radar (Keep an Eye)",
            "Active high-velocity market concepts paired with upcoming or digesting calendar triggers.",
            "",
            "| Concept | Velocity | Catalyst Event | Target Date | Status | Impact |",
            "| :--- | :--- | :--- | :--- | :--- | :--- |",
        ]
        for item in visible_items:
            stage_str = item.stage.capitalize()
            lines.append(
                f"| {item.concept_name} | {item.velocity_score:.1f} | {item.catalyst_title} | "
                f"{item.target_date} ({item.date_offset_label}) | {stage_str} | {item.impact} |"
            )
        if len(radar_items) > max_items:
            lines.append(
                f"\n*(Showing top {max_items} of {len(radar_items)} active collisions sorted by proximity and velocity)*"
            )
        return "\n".join(lines)

    # Detailed view (cap at max 10 to avoid bloating context)
    max_detail = min(max_items, 10)
    visible_items = radar_items[:max_detail]
    blocks = [
        "### Catalyst Radar (Keep an Eye) - Detailed Intelligence",
        "Full context for high-velocity concepts and matched calendar events.",
        "",
    ]
    for item in visible_items:
        stage_str = item.stage.capitalize()
        tickers_str = ", ".join(item.related_tickers) if item.related_tickers else "Broad market"
        blocks.extend(
            [
                f"#### [{stage_str}] {item.concept_name} (Velocity: {item.velocity_score:.1f})",
                f"- **Catalyst**: {item.catalyst_title}",
                f"- **Target Date**: {item.target_date} ({item.date_offset_label})",
                f"- **Stage**: {stage_str} (Days offset: {item.days_to_event})",
                f"- **Expected Impact**: {item.impact} (Similarity: {item.similarity:.2f})",
                f"- **Related Tickers**: {tickers_str}",
                f"- **Source Context**: {item.memory_content}",
                "",
            ]
        )
    if len(radar_items) > max_detail:
        blocks.append(
            f"*(Showing top {max_detail} of {len(radar_items)} detailed collisions. Use lean mode or narrower filters for more)*"
        )
    return "\n".join(blocks)
