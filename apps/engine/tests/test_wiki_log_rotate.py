from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from apps.engine.scripts.wiki_log_rotate import rotate_log


@pytest.fixture
def temp_wiki_dir():
    with TemporaryDirectory() as tmpdir:
        wiki_dir = Path(tmpdir) / "wiki"
        wiki_dir.mkdir()
        (wiki_dir / "log").mkdir()
        yield wiki_dir


def test_rotate_log_under_threshold(temp_wiki_dir):
    log_file = temp_wiki_dir / "log.md"
    content = "## [2026-05-18] test | First entry\n\nSome text.\n"
    log_file.write_text(content)

    # Threshold is large, should not rotate
    rotated = rotate_log(temp_wiki_dir, threshold_bytes=1000)
    assert not rotated
    assert log_file.read_text() == content


def test_rotate_log_over_threshold_with_keep_count(temp_wiki_dir):
    log_file = temp_wiki_dir / "log.md"
    content = """## [2026-04-10] old | April entry

April text.

## [2026-04-15] old | Mid-April entry

More April text.

## [2026-05-01] new | May entry

May text.

## [2026-05-18] new | Today entry

Today text.
"""
    log_file.write_text(content)

    # Force rotation (threshold 10 bytes), keep only the last 2 entries
    rotated = rotate_log(temp_wiki_dir, threshold_bytes=10, keep_count=2)
    assert rotated is True

    active_content = log_file.read_text()
    assert "## [2026-05-01]" in active_content
    assert "## [2026-05-18]" in active_content
    assert "## [2026-04-10]" not in active_content

    archive_file = temp_wiki_dir / "log" / "2026-04.md"
    assert archive_file.exists()
    archive_content = archive_file.read_text()
    assert "## [2026-04-10]" in archive_content
    assert "## [2026-04-15]" in archive_content
    assert "## [2026-05-01]" not in archive_content


def test_rotate_log_appends_to_existing_archive(temp_wiki_dir):
    log_file = temp_wiki_dir / "log.md"
    log_file.write_text("## [2026-04-20] old | Late April\n\nText.\n## [2026-05-01] new | keep\n\nkeep.")

    archive_file = temp_wiki_dir / "log" / "2026-04.md"
    archive_file.write_text("## [2026-04-05] older | Early April\n\nOld text.\n\n")

    # Keep 1 entry in active log
    rotate_log(temp_wiki_dir, threshold_bytes=5, keep_count=1)

    archive_content = archive_file.read_text()
    assert "## [2026-04-05]" in archive_content
    assert "## [2026-04-20]" in archive_content
    assert "## [2026-05-01]" in log_file.read_text()
