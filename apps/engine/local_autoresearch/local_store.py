"""Sandboxed SQLite storage for Local Autoresearch experiments and memories."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime
from typing import Any

from apps.engine.local_autoresearch.manifest import DataManifest, JevCriteriaConfig

DEFAULT_LOCAL_DB = ".local_autoresearch.db"


def init_local_store(db_path: str = DEFAULT_LOCAL_DB) -> None:
    """Initialize local SQLite database for sandboxed autoresearch tracking."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS local_experiments (
            variant_tag TEXT PRIMARY KEY,
            parent_tag TEXT,
            criteria_up TEXT NOT NULL,
            criteria_down TEXT NOT NULL,
            min_confidence REAL NOT NULL,
            manifest_json TEXT NOT NULL,
            train_score REAL,
            test_score REAL,
            overfit_penalty REAL,
            effective_score REAL,
            is_baseline_beat INTEGER DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'active',
            hypothesis TEXT,
            created_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS local_memories (
            id TEXT PRIMARY KEY,
            iteration INTEGER NOT NULL,
            variant_tag TEXT NOT NULL,
            hypothesis TEXT,
            insight TEXT,
            test_score REAL,
            is_baseline_beat INTEGER NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


def save_local_experiment(
    variant_tag: str,
    criteria: JevCriteriaConfig,
    manifest: DataManifest,
    parent_tag: str | None = None,
    train_score: float | None = None,
    test_score: float | None = None,
    overfit_penalty: float | None = None,
    effective_score: float | None = None,
    is_baseline_beat: bool = False,
    status: str = "active",
    hypothesis: str = "",
    db_path: str = DEFAULT_LOCAL_DB,
) -> None:
    """Save or update an experiment record in the sandboxed local database."""
    init_local_store(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    now_iso = datetime.now(UTC).isoformat()
    manifest_json = json.dumps(manifest.model_dump())

    cursor.execute(
        """
        INSERT OR REPLACE INTO local_experiments (
            variant_tag, parent_tag, criteria_up, criteria_down, min_confidence,
            manifest_json, train_score, test_score, overfit_penalty, effective_score,
            is_baseline_beat, status, hypothesis, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            variant_tag,
            parent_tag,
            criteria.criteria_up,
            criteria.criteria_down,
            criteria.min_confidence,
            manifest_json,
            train_score,
            test_score,
            overfit_penalty,
            effective_score,
            1 if is_baseline_beat else 0,
            status,
            hypothesis,
            now_iso,
        ),
    )
    conn.commit()
    conn.close()


def get_active_baseline(db_path: str = DEFAULT_LOCAL_DB) -> dict[str, Any] | None:
    """Retrieve the current active baseline experiment with the highest ratchet score."""
    init_local_store(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM local_experiments
        WHERE status = 'baseline'
        ORDER BY effective_score DESC, created_at DESC
        LIMIT 1
    """)
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    data = dict(row)
    data["manifest"] = json.loads(data["manifest_json"])
    return data


def save_local_memory(
    iteration: int,
    variant_tag: str,
    hypothesis: str,
    insight: str,
    test_score: float,
    is_baseline_beat: bool,
    db_path: str = DEFAULT_LOCAL_DB,
) -> str:
    """Record a local causal insight into the sandboxed memories table."""
    init_local_store(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    mem_id = str(uuid.uuid4())
    now_iso = datetime.now(UTC).isoformat()

    cursor.execute(
        """
        INSERT INTO local_memories (
            id, iteration, variant_tag, hypothesis, insight,
            test_score, is_baseline_beat, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            mem_id,
            iteration,
            variant_tag,
            hypothesis,
            insight,
            test_score,
            1 if is_baseline_beat else 0,
            now_iso,
        ),
    )
    conn.commit()
    conn.close()
    return mem_id


def get_recent_memories(limit: int = 5, db_path: str = DEFAULT_LOCAL_DB) -> list[dict[str, Any]]:
    """Retrieve recent causal memories, prioritizing baseline-beating discoveries."""
    init_local_store(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT * FROM local_memories
        ORDER BY is_baseline_beat DESC, created_at DESC
        LIMIT ?
        """,
        (limit,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def format_memories_for_prompt(memories: list[dict[str, Any]]) -> str:
    """Format local memories into markdown for injection into Qwen's meta-prompt."""
    if not memories:
        return "No prior local research memories recorded yet."

    lines = ["### PRIOR LOCAL AUTORESEARCH LESSONS:"]
    for m in memories:
        status = "WINNER" if m.get("is_baseline_beat") else "EXPLORATORY"
        score = m.get("test_score", 0.0)
        hyp = m.get("hypothesis", "No hypothesis stated")
        ins = m.get("insight", "No insight")
        lines.append(f"- [{status} | Test Score: {score:.2f}] Hypothesis: {hyp}\n  Takeaway: {ins}")

    return "\n".join(lines)
