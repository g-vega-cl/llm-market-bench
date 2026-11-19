"""Tests verifying that .husky/pre-commit supports scoped execution and SEQUENTIAL=1."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
PRE_COMMIT_FILE = REPO_ROOT / ".husky" / "pre-commit"


def test_pre_commit_supports_sequential_and_capped_workers():
    assert PRE_COMMIT_FILE.exists(), ".husky/pre-commit must exist"
    content = PRE_COMMIT_FILE.read_text()

    # Must inspect SEQUENTIAL environment variable and git config toggle
    assert "SEQUENTIAL" in content, "pre-commit must check SEQUENTIAL environment variable"
    assert "benchify.sequential" in content, "pre-commit must check git config benchify.sequential"

    # Must cap workers instead of unbounded -n auto, and support 1-worker sequential mode
    assert "-n auto" not in content, "pre-commit must not use unbounded pytest -n auto"
    assert "-n 4" in content, "pre-commit must cap parallel engine workers at 4"
    assert "WEB_WORKERS=1" in content, "pre-commit must support 1-worker sequential mode for web"
    assert "--maxWorkers=" in content, "pre-commit must cap web Vitest workers"
    assert "test -- --maxWorkers" not in content, "pre-commit must not pass extra -- before --maxWorkers under pnpm"

    # Must scope checks to staged files and avoid exit-5 on empty test dirs
    assert "--diff-filter=ACMR" in content, "pre-commit must ignore deleted staged files"
    assert "vitest related" in content, "pre-commit must run vitest related for scoped web changes"
