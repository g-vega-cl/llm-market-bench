"""Tests verifying that .husky/pre-commit supports sequential execution via SEQUENTIAL=1."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
PRE_COMMIT_FILE = REPO_ROOT / ".husky" / "pre-commit"


def test_pre_commit_supports_sequential():
    assert PRE_COMMIT_FILE.exists(), ".husky/pre-commit must exist"
    content = PRE_COMMIT_FILE.read_text()

    # Must inspect SEQUENTIAL environment variable
    assert "SEQUENTIAL" in content, "pre-commit must check SEQUENTIAL environment variable"

    # Must run engine tests without -n auto when sequential
    assert "python3 -m pytest --cov=. --cov-config=.coveragerc" in content

    # Must run web tests with --maxWorkers=1 when sequential
    assert "--maxWorkers=1" in content

    # Must retain parallel execution as default
    assert "pytest -n auto" in content
