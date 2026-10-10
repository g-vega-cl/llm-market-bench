"""Unit tests for local_autoresearch.local_store."""

import os
import tempfile

import pytest
from apps.engine.local_autoresearch.local_store import (
    format_memories_for_prompt,
    get_active_baseline,
    get_recent_memories,
    init_local_store,
    save_local_experiment,
    save_local_memory,
)
from apps.engine.local_autoresearch.manifest import DataManifest, JevCriteriaConfig


@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_local_store(path)
    yield path
    if os.path.exists(path):
        os.remove(path)


def test_save_and_retrieve_baseline(temp_db):
    assert get_active_baseline(temp_db) is None

    criteria1 = JevCriteriaConfig(criteria_up="UP rules 1", criteria_down="DOWN rules 1")
    manifest1 = DataManifest(include_currency_uup=False)

    save_local_experiment(
        variant_tag="v1",
        criteria=criteria1,
        manifest=manifest1,
        train_score=60.0,
        test_score=55.0,
        effective_score=55.0,
        status="baseline",
        db_path=temp_db,
    )

    baseline = get_active_baseline(temp_db)
    assert baseline is not None
    assert baseline["variant_tag"] == "v1"
    assert baseline["effective_score"] == 55.0
    assert baseline["manifest"]["include_currency_uup"] is False

    # Save higher scoring baseline
    criteria2 = JevCriteriaConfig(criteria_up="UP rules 2", criteria_down="DOWN rules 2")
    manifest2 = DataManifest(include_currency_uup=True)

    save_local_experiment(
        variant_tag="v2",
        criteria=criteria2,
        manifest=manifest2,
        train_score=75.0,
        test_score=70.0,
        effective_score=70.0,
        status="baseline",
        db_path=temp_db,
    )

    new_baseline = get_active_baseline(temp_db)
    assert new_baseline["variant_tag"] == "v2"
    assert new_baseline["effective_score"] == 70.0


def test_save_and_format_local_memories(temp_db):
    save_local_memory(
        iteration=1,
        variant_tag="v1",
        hypothesis="Remove currency to reduce noise",
        insight="Accuracy improved by 8% on volatile weeks",
        test_score=65.0,
        is_baseline_beat=True,
        db_path=temp_db,
    )

    save_local_memory(
        iteration=2,
        variant_tag="v2",
        hypothesis="Drop options skew",
        insight="False signals increased during OPEX",
        test_score=42.0,
        is_baseline_beat=False,
        db_path=temp_db,
    )

    mems = get_recent_memories(limit=5, db_path=temp_db)
    assert len(mems) == 2
    # Winner should be prioritized
    assert mems[0]["is_baseline_beat"] == 1
    assert mems[0]["variant_tag"] == "v1"

    prompt_text = format_memories_for_prompt(mems)
    assert "PRIOR LOCAL AUTORESEARCH LESSONS" in prompt_text
    assert "WINNER | Test Score: 65.00" in prompt_text
    assert "EXPLORATORY | Test Score: 42.00" in prompt_text
