"""Double-Ratchet Tournament Orchestrator for Strata (Qwen Two-Pass Architecture).

Co-evolves:
- Prompt 1: Ingestion / Distillation Prompt for Qwen Pass 1 via Strata (:8080)
- Prompt 2: Directional Arbiter Criteria & Min Conviction Gate for Qwen Pass 2 via Strata (:8080)
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import random
import sqlite3
import sys
import uuid
from contextlib import closing
from typing import Any

import httpx

# Ensure apps/engine root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import logger
from local_autoresearch.document_builder import (
    DEFAULT_INGESTION_SYSTEM_PROMPT,
    generate_daily_document,
    get_point_in_time_memories,
)
from local_autoresearch.jev_evaluator import calculate_metrics
from local_autoresearch.manifest import (
    DoubleRatchetMutation,
    JevCriteriaConfig,
)
from local_autoresearch.qwen_predictor_client import (
    evaluate_with_qwen_predictor,
)
from local_autoresearch.strata_client import (
    DEFAULT_STRATA_URL,
    generate_double_ratchet_mutation_with_strata,
)

DEFAULT_LAYA_URL = os.getenv("LAYA_SERVER_URL", "http://127.0.0.1:8081/v1/systemone")


class SqliteDocumentCache:
    """Persistent thread-safe document cache stored in SQLite."""

    def __init__(self, db_path: str = ".local_autoresearch_cache.db") -> None:
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        with closing(sqlite3.connect(self.db_path)) as conn, conn:
            conn.execute(
                """
                    CREATE TABLE IF NOT EXISTS double_ratchet_documents (
                        target_date TEXT NOT NULL,
                        prompt_hash TEXT NOT NULL,
                        document TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        PRIMARY KEY (target_date, prompt_hash)
                    )
                    """
            )

    def get(self, target_date: str, prompt_hash: str) -> str | None:
        with closing(sqlite3.connect(self.db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT document FROM double_ratchet_documents WHERE target_date = ? AND prompt_hash = ?",
                (target_date, prompt_hash),
            )
            row = cursor.fetchone()
            return row[0] if row else None

    def put(self, target_date: str, prompt_hash: str, document: str) -> None:
        with closing(sqlite3.connect(self.db_path)) as conn, conn:
            conn.execute(
                """
                    INSERT OR REPLACE INTO double_ratchet_documents (target_date, prompt_hash, document, created_at)
                    VALUES (?, ?, ?, datetime('now'))
                    """,
                (target_date, prompt_hash, document),
            )

    def __contains__(self, key: str) -> bool:
        parts = key.split(":", 1)
        if len(parts) == 2:
            return self.get(parts[0], parts[1]) is not None
        return False

    def __getitem__(self, key: str) -> str:
        parts = key.split(":", 1)
        if len(parts) == 2:
            val = self.get(parts[0], parts[1])
            if val is not None:
                return val
        raise KeyError(key)

    def __setitem__(self, key: str, value: str) -> None:
        parts = key.split(":", 1)
        if len(parts) == 2:
            self.put(parts[0], parts[1], value)


DEFAULT_DOUBLE_RATCHET_CRITERIA = JevCriteriaConfig(
    criteria_up=(
        "Overnight tape shows SPY gap >= +0.15% with QQQ confirmation, "
        "Treasury yields flat/falling, rolling 5D return positive or stabilizing, "
        "and positive institutional sentiment."
    ),
    criteria_down=(
        "Overnight tape shows gap rejection or SPY gap <= -0.15% with tech weakness, "
        "rising bond yields, rolling 5D trend exhaustion/divergence, or negative macro risk."
    ),
    min_confidence=0.0,
)


def partition_dataset(
    all_days: list[dict[str, Any]],
    held_out_ratio: float = 0.15,
    seed: int = 42,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Deterministically partition historical days into Active Ratchet pool (85%) and Sequestered Held-Out slice (15%)."""
    if not all_days:
        return [], []

    # Sort deterministically by target_date first
    sorted_days = sorted(all_days, key=lambda d: str(d.get("target_date", "")))

    rng = random.Random(seed)
    shuffled_indices = list(range(len(sorted_days)))
    rng.shuffle(shuffled_indices)

    held_out_count = max(1, int(len(sorted_days) * held_out_ratio))
    held_out_idx_set = set(shuffled_indices[:held_out_count])

    active_days: list[dict[str, Any]] = []
    held_out_days: list[dict[str, Any]] = []

    for idx, day in enumerate(sorted_days):
        if idx in held_out_idx_set:
            held_out_days.append(day)
        else:
            active_days.append(day)

    return active_days, held_out_days


def partition_curriculum_weeks(
    all_weeks: dict[str, list[dict[str, Any]]],
    test_ratio: float = 0.10,
    seed: int = 42,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, list[dict[str, Any]]]]:
    """Partition calendar weeks into active training weeks and a sequestered 10% test set.

    Filters for complete trading weeks (>= 4 sessions). Deterministically sequesters
    test_ratio (default 10%) of weeks for post-autoresearch testing. Autoresearch never trains on stashed weeks.
    """
    eligible_keys = sorted([w for w, days in all_weeks.items() if len(days) >= 4])
    if not eligible_keys:
        eligible_keys = sorted(all_weeks.keys())

    num_test = max(1, int(len(eligible_keys) * test_ratio))
    rng = random.Random(seed)
    stashed_keys = set(rng.sample(eligible_keys, num_test))

    active_weeks: dict[str, list[dict[str, Any]]] = {}
    stashed_weeks: dict[str, list[dict[str, Any]]] = {}

    for k, days in all_weeks.items():
        if k in stashed_keys:
            stashed_weeks[k] = days
        else:
            active_weeks[k] = days

    return active_weeks, stashed_weeks


def sample_curriculum_weeks(
    all_weeks: dict[str, list[dict[str, Any]]],
    num_weeks: int = 10,
    seed: int | None = None,
) -> list[tuple[str, list[dict[str, Any]]]]:
    """Sample representative calendar weeks chronologically for curriculum training.

    Filters for complete trading weeks (>= 4 sessions) and samples num_weeks.
    If seed is None, sampling is randomized across runs. Preserves chronological
    order so historical lessons compound point-in-time.
    """
    eligible_keys = [w for w, days in all_weeks.items() if len(days) >= 4]
    eligible_keys.sort()

    if not eligible_keys:
        eligible_keys = sorted(all_weeks.keys())

    if len(eligible_keys) <= num_weeks:
        selected_keys = eligible_keys
    else:
        rng = random.Random(seed) if seed is not None else random.Random()
        selected_keys = sorted(rng.sample(eligible_keys, num_weeks))

    result: list[tuple[str, list[dict[str, Any]]]] = []
    for k in selected_keys:
        days = sorted(all_weeks[k], key=lambda d: str(d.get("target_date", "")))
        result.append((k, days))

    return result


def partition_into_curriculum_batches(
    all_weeks: dict[str, list[dict[str, Any]]],
    num_batches: int = 10,
    weeks_per_batch: int | None = None,
    stashed_ratio: float = 0.10,
    seed: int | None = 42,
    shuffle_weeks: bool = True,
) -> tuple[list[list[tuple[str, list[dict[str, Any]]]]], dict[str, list[dict[str, Any]]]]:
    """Partition calendar weeks into a stashed test set and N curriculum batches.

    1. Stashes test_ratio (default 10%) of complete weeks (>= 4 sessions) as a sequestered test set.
    2. If shuffle_weeks is True (default), active weeks are pseudo-randomly shuffled before batching
       so each batch is a multi-regime cross-section spanning disparate market conditions across
       the entire multi-year timeline (rather than a single contiguous month).
       If shuffle_weeks is False, active weeks are batched chronologically in contiguous blocks.
    3. Partitions active weeks into num_batches batches of weeks_per_batch weeks.
       Within each batch, the weeks are sorted chronologically so point-in-time Friday mini-cycle
       lessons compound consistently.
    """
    eligible_keys = sorted([w for w, days in all_weeks.items() if len(days) >= 4])
    if not eligible_keys:
        eligible_keys = sorted(all_weeks.keys())

    num_test = max(1, int(len(eligible_keys) * stashed_ratio))
    rng = random.Random(seed) if seed is not None else random.Random()
    stashed_keys = set(rng.sample(eligible_keys, num_test))

    active_keys = [k for k in eligible_keys if k not in stashed_keys]
    if shuffle_weeks:
        rng.shuffle(active_keys)
    else:
        active_keys.sort()

    stashed_weeks: dict[str, list[dict[str, Any]]] = {
        k: sorted(all_weeks[k], key=lambda d: str(d.get("target_date", ""))) for k in sorted(stashed_keys)
    }

    n_active = len(active_keys)
    n_batches = max(1, min(num_batches, n_active))

    batches: list[list[tuple[str, list[dict[str, Any]]]]] = []
    for i in range(n_batches):
        if weeks_per_batch is not None:
            start = i * weeks_per_batch
            end = min(start + weeks_per_batch, n_active)
        else:
            start = i * n_active // n_batches
            end = (i + 1) * n_active // n_batches
        batch_keys = active_keys[start:end]
        if not batch_keys:
            continue
        # Ensure chronological order within the batch for forward mini-cycle lesson compounding
        batch_weeks = [
            (k, sorted(all_weeks[k], key=lambda d: str(d.get("target_date", "")))) for k in sorted(batch_keys)
        ]
        batches.append(batch_weeks)

    return batches, stashed_weeks


async def run_weekly_mini_autoresearch(
    week_key: str,
    week_results: list[dict[str, Any]],
    strata_url: str = DEFAULT_STRATA_URL,
    db_path: str = ".local_autoresearch_cache.db",
    run_id: str | None = None,
    client: httpx.AsyncClient | None = None,
) -> list[str]:
    """Execute weekly mini-autoresearch at Friday close.

    Analyzes the week's daily predictions vs actuals, synthesizes 1-2 actionable lessons
    using Strata, and persists them into SQLite cached_memories timestamped at Friday 20:00 UTC.
    """
    if not week_results:
        return []

    sorted_res = sorted(week_results, key=lambda r: str(r.get("target_date", "")))
    friday_date = sorted_res[-1].get("target_date", "UNKNOWN_DATE")
    friday_timestamp = f"{friday_date}T20:00:00Z"

    lines = [f"Week: {week_key} (Ended {friday_date})"]
    for r in sorted_res:
        t_date = r.get("target_date")
        pred = r.get("predicted_direction", "UNKNOWN")
        act = r.get("actual_direction", "UNKNOWN")
        conf = r.get("confidence", 0.0)
        corr = r.get("is_correct", False)
        traded = r.get("is_traded", True)
        lines.append(
            f"- {t_date}: Predicted={pred} ({conf:.1f}%), Actual={act} | {'✓' if corr else '✗'}{' [NO_TRADE]' if not traded else ''}"
        )

    week_summary = "\n".join(lines)
    prompt = (
        "You are an expert quantitative trading post-mortem analyst.\n"
        "Review the following week of intraday SPY directional predictions against actual market outcomes:\n\n"
        f"{week_summary}\n\n"
        "Identify the primary failure mode or predictive success this week (e.g. fading unconfirmed gap-ups, bond yield divergence, overbought exhaustion).\n"
        "Formulate 1 to 2 dense, actionable tactical lessons learned (<80 words total).\n"
        "Format your response as 1-2 bullet points starting with '- Lesson: '."
    )

    should_close = False
    if client is None:
        client = httpx.AsyncClient(timeout=60.0)
        should_close = True

    lessons: list[str] = []
    try:
        url = f"{strata_url.rstrip('/')}/chat/completions"
        payload = {
            "model": "Qwen/Qwen2.5-32B-Instruct",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a quantitative post-mortem audit engine. Be dense, concise, and factual.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "max_tokens": 512,
        }
        resp = await client.post(url, json=payload, headers={"Content-Type": "application/json"})
        if resp.status_code == 200:
            raw_json = resp.json()
            data = await raw_json if hasattr(raw_json, "__await__") else raw_json
            msg = data.get("choices", [{}])[0].get("message", {})
            raw_content = msg.get("content") or msg.get("reasoning_content") or ""
            for line in (raw_content or "").split("\n"):
                clean_l = line.strip()
                if clean_l.startswith("- Lesson:") or clean_l.startswith("Lesson:"):
                    lesson_text = clean_l.split("Lesson:", 1)[1].strip()
                    if lesson_text:
                        lessons.append(lesson_text)
                elif clean_l.startswith("- ") and len(clean_l) > 10:
                    lessons.append(clean_l[2:].strip())

        if not lessons:
            lessons = [f"Week {week_key} review: verify macro yield confirmation when SPY gaps opposite to tape."]

        # Persist into SQLite cached_memories
        if os.path.exists(db_path):
            mem_prefix = f"mini_{run_id}_" if run_id else "mini_"
            with closing(sqlite3.connect(db_path)) as conn, conn:
                for l_text in lessons:
                    mem_id = f"{mem_prefix}{uuid.uuid4().hex[:8]}"
                    labeled_content = (
                        l_text if l_text.startswith("[Local Autoresearch]") else f"[Local Autoresearch] {l_text}"
                    )
                    conn.execute(
                        """
                            INSERT OR REPLACE INTO cached_memories (id, content, memory_type, importance_score, created_at)
                            VALUES (?, ?, 'LOCAL_AUTORESEARCH_LESSON', 90, ?)
                            """,
                        (mem_id, labeled_content, friday_timestamp),
                    )

        return lessons
    except Exception as e:
        logger.warning(f"Weekly mini-autoresearch failed for {week_key}: {e}")
        return []
    finally:
        if should_close:
            await client.aclose()


def cleanup_mini_cycle_memories(db_path: str = ".local_autoresearch_cache.db", run_id: str | None = None) -> None:
    """Clean up temporary mini-cycle lessons from a specific run or discarded candidate."""
    if not os.path.exists(db_path):
        return
    try:
        with closing(sqlite3.connect(db_path)) as conn, conn:
            if run_id:
                conn.execute("DELETE FROM cached_memories WHERE id LIKE ?", (f"mini_{run_id}_%",))
            else:
                conn.execute("DELETE FROM cached_memories WHERE id LIKE 'mini_%'")
    except Exception as e:
        logger.debug(f"Error cleaning up mini-cycle memories: {e}")


def query_memories_for_autoresearch(db_path: str = ".local_autoresearch_cache.db", limit: int = 15) -> str:
    """Query Supabase/local memories database for top post-mortems and lessons learned."""
    if not os.path.exists(db_path):
        return ""
    try:
        with closing(sqlite3.connect(db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT memory_type, content, importance_score, created_at
                FROM cached_memories
                WHERE memory_type IN ('LOCAL_AUTORESEARCH_LESSON', 'LESSON_LEARNED', 'POST_MORTEM', 'MARKET_REGIME')
                ORDER BY importance_score DESC, created_at DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = cursor.fetchall()
            if not rows:
                return ""
            lines = ["### HISTORICAL MEMORIES & LESSONS (FROM DATABASE):"]
            for r in rows:
                m_type = r["memory_type"]
                m_content = r["content"].strip()
                clean_content = " ".join(m_content.split())
                lines.append(f"- [{m_type}] {clean_content}")
            return "\n".join(lines)
    except Exception as e:
        logger.debug(f"Could not query memories for autoresearch: {e}")
        return ""


def summarize_recent_errors(results: list[dict[str, Any]], limit: int = 8) -> str:
    """Summarize recent predictive failures and false signals to guide Prompt 2 mutation."""
    if not results:
        return ""
    misses = []
    for r in results:
        t_date = r.get("target_date", "")
        pred = r.get("predicted_direction", "NO_TRADE")
        act = r.get("actual_direction", "")
        conf = r.get("confidence", 0.0)
        corr = r.get("is_correct", False)
        traded = r.get("is_traded", True)
        if not corr:
            if not traded:
                misses.append(f"- {t_date}: NO_TRADE ({conf:.1f}%) | Actual was {act} (Missed trend move)")
            else:
                misses.append(f"- {t_date}: Predicted {pred} ({conf:.1f}%) | Actual was {act} (False signal)")
        if len(misses) >= limit:
            break

    if not misses:
        return ""

    return "### RECENT PREDICTIVE FAILURES / FALSE SIGNALS TO ELIMINATE:\n" + "\n".join(misses)


def _compute_cache_key(day_date: str, prompt_text: str) -> str:
    """Compute deterministic MD5 hash for day + prompt combination."""
    prompt_hash = hashlib.md5(prompt_text.encode("utf-8")).hexdigest()[:12]
    return f"{day_date}:{prompt_hash}"


async def evaluate_single_day_double_ratchet(
    day_record: dict[str, Any],
    ingestion_prompt: str,
    criteria: JevCriteriaConfig,
    strata_url: str = DEFAULT_STRATA_URL,
    laya_url: str = DEFAULT_LAYA_URL,
    document_cache: dict[str, str] | None = None,
    client: httpx.AsyncClient | None = None,
    api_key: str | None = None,
    db_path: str = ".local_autoresearch_cache.db",
) -> dict[str, Any]:
    """Execute two-step evaluation for a single day: Qwen Pass 1 Ingestion -> Qwen Pass 2 Prediction."""
    target_date = str(day_record.get("target_date", "UNKNOWN_DATE"))
    ticker = str(day_record.get("ticker", "SPY")).upper()
    actual_dir = str(day_record.get("actual_direction", "UP")).upper()

    cache_key = _compute_cache_key(target_date, ingestion_prompt)
    daily_doc: str | None = None

    if document_cache is not None and cache_key in document_cache:
        daily_doc = document_cache[cache_key]
    else:
        daily_doc = await generate_daily_document(
            day_record=day_record,
            ingestion_prompt=ingestion_prompt,
            base_url=strata_url,
            client=client,
            allow_fallback=False,
            db_path=db_path,
        )
        if document_cache is not None:
            document_cache[cache_key] = daily_doc

    day_memories = get_point_in_time_memories(target_date, db_path=db_path, limit=5)
    pred_res = await evaluate_with_qwen_predictor(
        briefing=daily_doc,
        criteria=criteria,
        ticker=ticker,
        actual_direction=actual_dir,
        memories=day_memories,
        strata_url=strata_url,
        client=client,
    )

    open_p = float(day_record.get("open_price", 0.0))
    close_p = float(day_record.get("close_price", 0.0))

    return {
        "target_date": target_date,
        "ticker": ticker,
        "predicted_direction": pred_res["predicted_direction"],
        "gated_action": pred_res["gated_action"],
        "actual_direction": actual_dir,
        "confidence": pred_res["confidence"],
        "probabilities": pred_res.get("probabilities", {}),
        "is_correct": pred_res["is_correct"],
        "is_traded": pred_res["is_traded"],
        "brier_score": pred_res["brier_score"],
        "rationale": pred_res.get("rationale", ""),
        "open_price": open_p,
        "close_price": close_p,
        "document_len": len(daily_doc),
        "model_backend": pred_res.get("model_backend", "qwen-predictor-local"),
    }


async def evaluate_double_ratchet_batch(
    days: list[dict[str, Any]],
    ingestion_prompt: str,
    criteria: JevCriteriaConfig,
    max_concurrency: int = 1,
    strata_url: str = DEFAULT_STRATA_URL,
    laya_url: str = DEFAULT_LAYA_URL,
    document_cache: Any = None,
    api_key: str | None = None,
    db_path: str = ".local_autoresearch_cache.db",
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Concurrently evaluate a list of days across the two-step Qwen+Laya pipeline."""
    sem = asyncio.Semaphore(max_concurrency)
    total_days = len(days)
    completed = 0

    async with httpx.AsyncClient(timeout=180.0) as client:

        async def _eval(d: dict[str, Any]) -> dict[str, Any]:
            nonlocal completed
            async with sem:
                res = await evaluate_single_day_double_ratchet(
                    day_record=d,
                    ingestion_prompt=ingestion_prompt,
                    criteria=criteria,
                    strata_url=strata_url,
                    laya_url=laya_url,
                    document_cache=document_cache,
                    client=client,
                    api_key=api_key,
                    db_path=db_path,
                )
                completed += 1
                if completed % 10 == 0 or completed == total_days or completed == 1:
                    doc_len = res.get("document_len", 0)
                    conf = res.get("confidence", 0.0)
                    action = res.get("gated_action", "NO_TRADE")
                    corr = res.get("is_correct", False)
                    logger.info(
                        f"[{completed:03d}/{total_days:03d}] {res.get('target_date', 'UNKNOWN')}: "
                        f"doc={doc_len} chars | Pred: {action} ({conf:.1f}%) | "
                        f"{'✓ Correct' if corr else '✗ Incorrect'}"
                    )
                return res

        tasks = [_eval(d) for d in days]
        results = await asyncio.gather(*tasks)

    metrics = calculate_metrics(results)
    return metrics, results


async def evaluate_curriculum_batch(
    curriculum_weeks: list[tuple[str, list[dict[str, Any]]]],
    ingestion_prompt: str,
    criteria: JevCriteriaConfig,
    strata_url: str = DEFAULT_STRATA_URL,
    laya_url: str = DEFAULT_LAYA_URL,
    db_path: str = ".local_autoresearch_cache.db",
    document_cache: Any = None,
    api_key: str | None = None,
    run_id: str | None = None,
    run_mini_cycles: bool = True,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    """Evaluate a multi-week curriculum sequentially, executing mini-autoresearch at each Friday close."""
    all_results: list[dict[str, Any]] = []
    all_lessons: list[str] = []
    total_weeks = len(curriculum_weeks)

    async with httpx.AsyncClient(timeout=180.0) as client:
        for w_idx, (week_key, week_days) in enumerate(curriculum_weeks, 1):
            logger.info(
                f"--- Curriculum Week [{w_idx:02d}/{total_weeks:02d}] {week_key} ({len(week_days)} sessions) ---"
            )
            week_res: list[dict[str, Any]] = []
            for d in week_days:
                day_res = await evaluate_single_day_double_ratchet(
                    day_record=d,
                    ingestion_prompt=ingestion_prompt,
                    criteria=criteria,
                    strata_url=strata_url,
                    laya_url=laya_url,
                    document_cache=document_cache,
                    client=client,
                    api_key=api_key,
                    db_path=db_path,
                )
                week_res.append(day_res)
                all_results.append(day_res)
                corr = day_res.get("is_correct", False)
                logger.info(
                    f"  [{day_res.get('target_date')}]: Pred={day_res.get('gated_action')} ({day_res.get('confidence', 0):.1f}%) | "
                    f"Actual={day_res.get('actual_direction')} | {'✓' if corr else '✗'}"
                )

            # Weekly mini-autoresearch at Friday close
            if run_mini_cycles and len(week_res) >= 2:
                lessons = await run_weekly_mini_autoresearch(
                    week_key=week_key,
                    week_results=week_res,
                    strata_url=strata_url,
                    db_path=db_path,
                    run_id=run_id,
                    client=client,
                )
                if lessons:
                    all_lessons.extend(lessons)
                    logger.info(f"  📝 Friday Mini-Cycle Lessons ({len(lessons)}): {lessons}")

    metrics = calculate_metrics(all_results)
    return metrics, all_results, all_lessons


async def run_double_ratchet_curriculum_tournament(
    all_weeks: dict[str, list[dict[str, Any]]],
    num_curriculum_weeks: int = 10,
    iterations: int = 3,
    strata_url: str = DEFAULT_STRATA_URL,
    laya_url: str = DEFAULT_LAYA_URL,
    seed: int | None = None,
    initial_ingestion_prompt: str = DEFAULT_INGESTION_SYSTEM_PROMPT,
    initial_criteria: JevCriteriaConfig = DEFAULT_DOUBLE_RATCHET_CRITERIA,
    api_key: str | None = None,
    cache_db_path: str = ".local_autoresearch_cache.db",
    no_cache: bool = True,
    stashed_test_ratio: float = 0.10,
    state_path: str | None = None,
    shuffle_weeks: bool = True,
) -> dict[str, Any]:
    """Execute iterative double-ratchet tournament across walk-forward batches with Friday mini-cycles.

    1. Sequesters 10% of weeks into a stashed test set (never seen by autoresearch).
    2. Partitions active weeks into N walk-forward batches (e.g. 10 batches x ~10 weeks = 100 weeks).
       If shuffle_weeks is True (default), batches sample multi-regime cross-sections across all years.
    3. Batch 0 evaluates baseline prompts, creating point-in-time memories and Friday lessons.
    4. Iterations 1..N-1 mutate Prompt 1 & Prompt 2 using accumulated memories and evaluate on Batch 1..N-1.
    5. Evaluates champion on stashed test set after tournament completion.
    """
    n_batches = max(iterations, 1)
    batches, stashed_weeks = partition_into_curriculum_batches(
        all_weeks,
        num_batches=n_batches,
        weeks_per_batch=num_curriculum_weeks,
        stashed_ratio=stashed_test_ratio,
        seed=seed if seed is not None else 42,
        shuffle_weeks=shuffle_weeks,
    )
    stashed_eval_days = sum(len(days) for _, days in stashed_weeks.items())
    total_active_days = sum(len(days) for b in batches for _, days in b)

    logger.info(
        f"Starting Walk-Forward Double-Ratchet Tournament: {len(batches)} batches "
        f"({total_active_days} trading sessions total across batches, "
        f"distribution={'randomized multi-regime' if shuffle_weeks else 'sequential calendar blocks'}), "
        f"{len(stashed_weeks)} stashed test weeks ({stashed_eval_days} sessions, {stashed_test_ratio * 100:.0f}%), "
        f"{iterations} iterations (fresh live generation per day: {no_cache})."
    )

    doc_cache: Any = None if no_cache else (SqliteDocumentCache(cache_db_path) if cache_db_path else {})
    baseline_run_id = "batch_0_baseline"

    checkpoint_file = state_path or os.getenv(
        "DOUBLE_RATCHET_CURRICULUM_STATE", ".double_ratchet_curriculum_state.json"
    )

    def save_checkpoint(last_it: int) -> None:
        chk = {
            "last_completed_iteration": last_it,
            "total_iterations": iterations,
            "champion_score": champion_score,
            "champion_ingestion_prompt": champion_prompt,
            "champion_criteria": champion_criteria.model_dump(),
            "champion_metrics": champion_metrics,
            "history": history,
        }
        try:
            with open(checkpoint_file, "w", encoding="utf-8") as f:
                json.dump(chk, f, indent=2)
        except Exception as err:
            logger.warning(f"Failed to save tournament checkpoint: {err}")

    start_it = 1
    # Check if a valid checkpoint exists to resume
    if os.path.exists(checkpoint_file):
        try:
            with open(checkpoint_file, encoding="utf-8") as f:
                saved_chk = json.load(f)
            last_done = saved_chk.get("last_completed_iteration", 0)
            if 0 < last_done < iterations:
                start_it = last_done + 1
                champion_score = saved_chk["champion_score"]
                champion_prompt = saved_chk["champion_ingestion_prompt"]
                champion_criteria = JevCriteriaConfig(**saved_chk["champion_criteria"])
                champion_metrics = saved_chk["champion_metrics"]
                history = saved_chk.get("history", [])
                champion_results = []
                baseline_metrics = history[0].get("metrics", champion_metrics) if history else champion_metrics
                baseline_results = []
                baseline_lessons = []
                logger.info(
                    f"Resuming Double-Ratchet Curriculum Tournament from iteration {start_it} "
                    f"(Champion Score: {champion_score:.2f}, history steps: {len(history)})"
                )
        except Exception as err:
            logger.warning(f"Failed to load checkpoint from {checkpoint_file}: {err}")

    if start_it == 1:
        # 1. Baseline Evaluation on Batch 0
        curriculum_batch_0 = batches[0]
        batch_0_days = sum(len(days) for _, days in curriculum_batch_0)
        logger.info(
            f"\n=== Evaluating Baseline on Batch 0 "
            f"({len(curriculum_batch_0)} weeks, {batch_0_days} sessions, {curriculum_batch_0[0][0]} to {curriculum_batch_0[-1][0]}) ==="
        )
        baseline_metrics, baseline_results, baseline_lessons = await evaluate_curriculum_batch(
            curriculum_weeks=curriculum_batch_0,
            ingestion_prompt=initial_ingestion_prompt,
            criteria=initial_criteria,
            strata_url=strata_url,
            laya_url=laya_url,
            db_path=cache_db_path,
            document_cache=doc_cache,
            api_key=api_key,
            run_id=baseline_run_id,
            run_mini_cycles=True,
        )
        champion_score = baseline_metrics["score"]
        champion_prompt = initial_ingestion_prompt
        champion_criteria = initial_criteria
        champion_metrics = baseline_metrics
        champion_results = baseline_results

        logger.info(
            f"Baseline Batch 0 Score: {champion_score:.2f} | "
            f"Win Rate: {baseline_metrics['traded_win_rate_pct']:.1f}% | "
            f"Traded: {baseline_metrics['traded_days']}/{baseline_metrics['total_days']} | "
            f"Generated Lessons: {len(baseline_lessons)}"
        )

        history = [
            {
                "iteration": 0,
                "batch_index": 0,
                "batch_weeks_count": len(curriculum_batch_0),
                "score": champion_score,
                "metrics": baseline_metrics,
                "accepted": True,
                "hypothesis": "Initial Baseline Pair",
                "lessons_count": len(baseline_lessons),
            }
        ]

        save_checkpoint(0)

        # If iterations <= 1, this was a single dry run pass!
        if iterations <= 1:
            return {
                "iterations_run": iterations,
                "baseline_score": champion_score,
                "champion_score": champion_score,
                "champion_ingestion_prompt": champion_prompt,
                "champion_criteria": champion_criteria.model_dump(),
                "champion_metrics": champion_metrics,
                "stashed_test_weeks_count": len(stashed_weeks),
                "history": history,
                "results": baseline_results,
                "lessons": baseline_lessons,
            }

    # 2. Tournament Iteration Loop Across Batches start_it..iterations-1
    for it in range(start_it, iterations):
        batch_idx = it % len(batches)
        curriculum_batch = batches[batch_idx]
        cand_run_id = f"batch_{it}_{uuid.uuid4().hex[:6]}"
        batch_days = sum(len(days) for _, days in curriculum_batch)
        cycle_str = f" [Cycle {it // len(batches)}]" if it >= len(batches) else ""
        logger.info(
            f"\n--- Walk-Forward Iteration {it}/{iterations - 1} "
            f"(Batch {batch_idx}{cycle_str}: {len(curriculum_batch)} weeks, {batch_days} sessions, "
            f"{curriculum_batch[0][0]} to {curriculum_batch[-1][0]}, run_id: {cand_run_id}) ---"
        )

        # Query database memories (Supabase/local SQLite) and champion errors to improve Prompt 2
        memories_ctx = query_memories_for_autoresearch(db_path=cache_db_path, limit=12)
        errors_summary = summarize_recent_errors(champion_results, limit=8)

        try:
            mutation: DoubleRatchetMutation = await generate_double_ratchet_mutation_with_strata(
                baseline_ingestion_prompt=champion_prompt,
                baseline_criteria=champion_criteria,
                baseline_score=champion_score,
                train_score=champion_score,
                test_score=champion_score,
                memories_context=memories_ctx,
                recent_errors_summary=errors_summary,
                base_url=strata_url,
            )
            logger.info(f"Iteration {it} Hypothesis: {mutation.hypothesis}")
            logger.info(f"Iteration {it} Criteria UP: {mutation.criteria.criteria_up}")
            logger.info(f"Iteration {it} Criteria DOWN: {mutation.criteria.criteria_down}")
        except Exception as e:
            logger.error(
                f"Strata mutation failed on iteration {it} after retries: {e}. Falling back to champion prompts for batch {it}."
            )
            mutation = DoubleRatchetMutation(
                ingestion_prompt=champion_prompt,
                criteria=champion_criteria,
                hypothesis=f"Fallback to champion prompt pair on batch {it} due to mutation synthesis error: {e}",
            )

        # Dynamic catalyst re-generation: candidate Prompt 1 re-generates catalyst across new batch
        cand_doc_cache = None if (no_cache or mutation.ingestion_prompt != champion_prompt) else doc_cache
        cand_metrics, cand_results, cand_lessons = await evaluate_curriculum_batch(
            curriculum_weeks=curriculum_batch,
            ingestion_prompt=mutation.ingestion_prompt,
            criteria=mutation.criteria,
            strata_url=strata_url,
            laya_url=laya_url,
            db_path=cache_db_path,
            document_cache=cand_doc_cache,
            api_key=api_key,
            run_id=cand_run_id,
            run_mini_cycles=True,
        )

        cand_score = cand_metrics["score"]
        is_accepted = cand_score > champion_score

        logger.info(
            f"Candidate Batch {it} Score: {cand_score:.2f} (Delta: {cand_score - champion_score:+.2f}) | "
            f"Win Rate: {cand_metrics['traded_win_rate_pct']:.1f}% | "
            f"Traded: {cand_metrics['traded_days']}/{cand_metrics['total_days']} | "
            f"{'🏆 ACCEPTED' if is_accepted else '❌ DISCARDED'}"
        )

        if is_accepted:
            champion_score = cand_score
            champion_prompt = mutation.ingestion_prompt
            champion_criteria = mutation.criteria
            champion_metrics = cand_metrics
            champion_results = cand_results
        else:
            cleanup_mini_cycle_memories(db_path=cache_db_path, run_id=cand_run_id)

        history.append(
            {
                "iteration": it,
                "batch_index": it,
                "batch_weeks_count": len(curriculum_batch),
                "score": cand_score,
                "metrics": cand_metrics,
                "accepted": is_accepted,
                "hypothesis": mutation.hypothesis,
                "lessons_count": len(cand_lessons),
            }
        )
        save_checkpoint(it)

    # 3. Post-Autoresearch Evaluation on Stashed 10% Test Weeks
    test_metrics = None
    if stashed_weeks and iterations > 1:
        logger.info(
            f"\n=== POST-AUTORESEARCH EVALUATION ON STASHED TEST WEEKS "
            f"({len(stashed_weeks)} weeks, {stashed_eval_days} sessions) ==="
        )
        test_weeks_list = [
            (k, sorted(days, key=lambda d: str(d.get("target_date", "")))) for k, days in sorted(stashed_weeks.items())
        ]
        test_metrics, _, _ = await evaluate_curriculum_batch(
            curriculum_weeks=test_weeks_list,
            ingestion_prompt=champion_prompt,
            criteria=champion_criteria,
            strata_url=strata_url,
            laya_url=laya_url,
            db_path=cache_db_path,
            document_cache=None,
            api_key=api_key,
            run_id="post_autoresearch_test",
            run_mini_cycles=False,
        )
        logger.info(
            f"Stashed Test Score: {test_metrics['score']:.2f} | "
            f"Win Rate: {test_metrics['traded_win_rate_pct']:.1f}% | "
            f"Traded: {test_metrics['traded_days']}/{test_metrics['total_days']}"
        )
        save_checkpoint(iterations)

    return {
        "iterations_run": iterations,
        "baseline_score": baseline_metrics["score"],
        "champion_score": champion_score,
        "champion_ingestion_prompt": champion_prompt,
        "champion_criteria": champion_criteria.model_dump(),
        "champion_metrics": champion_metrics,
        "stashed_test_metrics": test_metrics,
        "stashed_test_weeks_count": len(stashed_weeks),
        "history": history,
    }


async def run_double_ratchet_tournament(
    all_days: list[dict[str, Any]],
    iterations: int = 3,
    strata_url: str = DEFAULT_STRATA_URL,
    laya_url: str = DEFAULT_LAYA_URL,
    held_out_ratio: float = 0.15,
    seed: int = 42,
    initial_ingestion_prompt: str = DEFAULT_INGESTION_SYSTEM_PROMPT,
    initial_criteria: JevCriteriaConfig = DEFAULT_DOUBLE_RATCHET_CRITERIA,
    max_concurrency: int = 1,
    api_key: str | None = None,
    cache_db_path: str | None = ".local_autoresearch_cache.db",
    no_cache: bool = False,
    state_path: str | None = None,
) -> dict[str, Any]:
    """Execute iterative double-ratchet tournament co-evolving Qwen Ingestion and Laya Criteria."""
    active_days, held_out_slice = partition_dataset(all_days, held_out_ratio=held_out_ratio, seed=seed)

    logger.info(
        f"Starting Double-Ratchet Tournament: {len(active_days)} active days, "
        f"{len(held_out_slice)} held-out sequestered days ({held_out_ratio * 100:.0f}%), "
        f"{iterations} iterations (fresh generation per day: {no_cache})."
    )

    doc_cache: Any = None if no_cache else (SqliteDocumentCache(cache_db_path) if cache_db_path else {})

    # Configure Strategy C: Multi-Fidelity Early Pruning
    filter_size = int(os.getenv("DOUBLE_RATCHET_FILTER_SIZE", "80"))
    early_reject_margin = float(os.getenv("DOUBLE_RATCHET_EARLY_REJECT_MARGIN", "1.50"))
    use_multi_fidelity = 0 < filter_size < len(active_days)

    if use_multi_fidelity:
        filter_days = active_days[:filter_size]
        remaining_days = active_days[filter_size:]
        logger.info(
            f"Strategy C Enabled: Multi-Fidelity Filter Slice = {len(filter_days)} days | "
            f"Confirmation Slice = {len(remaining_days)} days | "
            f"Early Rejection Margin = -{early_reject_margin:.2f} delta."
        )
    else:
        filter_days = active_days
        remaining_days = []

    # 1. Baseline Evaluation
    logger.info("Evaluating baseline (Prompt 1 + Prompt 2) on active dataset...")
    baseline_metrics, baseline_results = await evaluate_double_ratchet_batch(
        days=active_days,
        ingestion_prompt=initial_ingestion_prompt,
        criteria=initial_criteria,
        max_concurrency=max_concurrency,
        strata_url=strata_url,
        laya_url=laya_url,
        document_cache=doc_cache,
        api_key=api_key,
    )
    champion_score = baseline_metrics["score"]
    champion_prompt = initial_ingestion_prompt
    champion_criteria = initial_criteria
    champion_metrics = baseline_metrics
    champion_results = baseline_results

    if use_multi_fidelity:
        champion_filter_score = calculate_metrics(baseline_results[:filter_size])["score"]
        logger.info(
            f"Baseline Score: {champion_score:.2f} (Filter Slice Score: {champion_filter_score:.2f}) | "
            f"Win Rate: {baseline_metrics['traded_win_rate_pct']:.1f}% | "
            f"Traded: {baseline_metrics['traded_days']}/{baseline_metrics['total_days']}"
        )
    else:
        champion_filter_score = champion_score
        logger.info(
            f"Baseline Score: {champion_score:.2f} | "
            f"Win Rate: {baseline_metrics['traded_win_rate_pct']:.1f}% | "
            f"Traded: {baseline_metrics['traded_days']}/{baseline_metrics['total_days']}"
        )

    history = [
        {
            "iteration": 0,
            "score": champion_score,
            "metrics": baseline_metrics,
            "accepted": True,
            "hypothesis": "Initial Baseline Pair",
        }
    ]

    # 2. Iteration Loop
    for it in range(1, iterations + 1):
        cand_run_id = f"cand_{it}_{uuid.uuid4().hex[:6]}"
        logger.info(f"\n--- Double Ratchet Iteration {it}/{iterations} (run_id: {cand_run_id}) ---")

        memories_ctx = query_memories_for_autoresearch(
            db_path=cache_db_path or ".local_autoresearch_cache.db", limit=12
        )
        errors_summary = summarize_recent_errors(champion_results, limit=8)

        try:
            mutation: DoubleRatchetMutation = await generate_double_ratchet_mutation_with_strata(
                baseline_ingestion_prompt=champion_prompt,
                baseline_criteria=champion_criteria,
                baseline_score=champion_score,
                train_score=champion_score,
                test_score=champion_score,
                memories_context=memories_ctx,
                recent_errors_summary=errors_summary,
                base_url=strata_url,
            )
            logger.info(f"Iteration {it} Hypothesis: {mutation.hypothesis}")
            logger.info(f"Iteration {it} Criteria UP: {mutation.criteria.criteria_up}")
            logger.info(f"Iteration {it} Criteria DOWN: {mutation.criteria.criteria_down}")
        except Exception as e:
            logger.error(f"Strata mutation failed on iteration {it}: {e}")
            continue

        cand_doc_cache = None if (no_cache or mutation.ingestion_prompt != champion_prompt) else doc_cache
        if use_multi_fidelity:
            logger.info(f"Running Stage 1 Filter Slice ({len(filter_days)} days)...")
            stage1_metrics, stage1_results = await evaluate_double_ratchet_batch(
                days=filter_days,
                ingestion_prompt=mutation.ingestion_prompt,
                criteria=mutation.criteria,
                max_concurrency=max_concurrency,
                strata_url=strata_url,
                laya_url=laya_url,
                document_cache=cand_doc_cache,
                api_key=api_key,
            )
            stage1_score = stage1_metrics["score"]
            stage1_delta = stage1_score - champion_filter_score

            if stage1_delta < -early_reject_margin:
                logger.info(
                    f"Candidate {it} Early Rejected at Day {len(filter_days)}/{len(active_days)}: "
                    f"Stage 1 Score: {stage1_score:.2f} (Delta: {stage1_delta:+.2f} < -{early_reject_margin:.2f}) | "
                    f"Win Rate: {stage1_metrics['traded_win_rate_pct']:.1f}% | "
                    f"⏩ Compute Saved: ~{round((len(remaining_days) * 17) / 60, 1)} mins | ❌ DISCARDED"
                )
                history.append(
                    {
                        "iteration": it,
                        "score": stage1_score,
                        "metrics": stage1_metrics,
                        "accepted": False,
                        "pruned_early": True,
                        "hypothesis": mutation.hypothesis,
                    }
                )
                continue

            logger.info(
                f"Candidate {it} passed Stage 1 Filter (Score: {stage1_score:.2f}, Delta: {stage1_delta:+.2f}). "
                f"Evaluating remaining {len(remaining_days)} days..."
            )
            stage2_metrics, stage2_results = await evaluate_double_ratchet_batch(
                days=remaining_days,
                ingestion_prompt=mutation.ingestion_prompt,
                criteria=mutation.criteria,
                max_concurrency=max_concurrency,
                strata_url=strata_url,
                laya_url=laya_url,
                document_cache=cand_doc_cache,
                api_key=api_key,
            )
            all_cand_results = stage1_results + stage2_results
            cand_metrics = calculate_metrics(all_cand_results)
            cand_final_results = all_cand_results
        else:
            cand_metrics, cand_results = await evaluate_double_ratchet_batch(
                days=active_days,
                ingestion_prompt=mutation.ingestion_prompt,
                criteria=mutation.criteria,
                max_concurrency=max_concurrency,
                strata_url=strata_url,
                laya_url=laya_url,
                document_cache=cand_doc_cache,
                api_key=api_key,
            )
            stage1_score = cand_metrics["score"]
            cand_final_results = cand_results

        cand_score = cand_metrics["score"]
        is_accepted = cand_score > champion_score

        logger.info(
            f"Candidate Score: {cand_score:.2f} (Delta: {cand_score - champion_score:+.2f}) | "
            f"Win Rate: {cand_metrics['traded_win_rate_pct']:.1f}% | "
            f"Traded: {cand_metrics['traded_days']}/{cand_metrics['total_days']} | "
            f"{'🏆 ACCEPTED' if is_accepted else '❌ DISCARDED'}"
        )

        if is_accepted:
            champion_score = cand_score
            champion_filter_score = stage1_score
            champion_prompt = mutation.ingestion_prompt
            champion_criteria = mutation.criteria
            champion_metrics = cand_metrics
            champion_results = cand_final_results

        history.append(
            {
                "iteration": it,
                "score": cand_score,
                "metrics": cand_metrics,
                "accepted": is_accepted,
                "hypothesis": mutation.hypothesis,
            }
        )

        # Persist checkpoint to disk
        checkpoint_data = {
            "last_completed_iteration": it,
            "champion_score": champion_score,
            "champion_ingestion_prompt": champion_prompt,
            "champion_criteria": champion_criteria.model_dump(),
            "champion_metrics": champion_metrics,
            "history": history,
        }
        checkpoint_path = state_path or os.getenv("DOUBLE_RATCHET_STATE_PATH", ".double_ratchet_state.json")
        try:
            with open(checkpoint_path, "w", encoding="utf-8") as f:
                json.dump(checkpoint_data, f, indent=2)
        except Exception as save_err:
            logger.warning(f"Failed to persist tournament checkpoint: {save_err}")

    # 3. Post-Ratchet Sequestered Held-Out Evaluation
    logger.info("\n=== POST-RATCHET EVALUATION ON SEQUESTERED HELD-OUT SLICE ===")
    held_out_metrics, _ = await evaluate_double_ratchet_batch(
        days=held_out_slice,
        ingestion_prompt=champion_prompt,
        criteria=champion_criteria,
        max_concurrency=max_concurrency,
        strata_url=strata_url,
        laya_url=laya_url,
        document_cache=doc_cache,
        api_key=api_key,
    )

    logger.info(
        f"Held-Out Score: {held_out_metrics['score']:.2f} | "
        f"Held-Out Win Rate: {held_out_metrics['traded_win_rate_pct']:.1f}% | "
        f"Held-Out Traded: {held_out_metrics['traded_days']}/{held_out_metrics['total_days']}"
    )

    return {
        "iterations_run": iterations,
        "baseline_score": baseline_metrics["score"],
        "champion_score": champion_score,
        "champion_ingestion_prompt": champion_prompt,
        "champion_criteria": champion_criteria.model_dump(),
        "champion_metrics": champion_metrics,
        "held_out_metrics": held_out_metrics,
        "history": history,
    }
