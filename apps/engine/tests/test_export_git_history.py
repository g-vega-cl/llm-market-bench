from unittest.mock import patch

from apps.engine.export_git_history import ensure_gitignore, export_git_history

# Sample git log output block matching the format:
# COMMIT_START|%H|%ad|%an|%s%n%b%nCOMMIT_FILES
MOCK_GIT_LOG = (
    "__GIT_HISTORY_COMMIT_START__|f33a1cdf97c4929fd39eb73c6ba98bea2eb2fe30|2026-07-15|g-vega-cl|"
    "refactor(engine/models): add case normalization\n"
    "Improve resilience of structured extractions against minor LLM discrepancies.\n"
    "\n"
    "__GIT_HISTORY_COMMIT_FILES__\n"
    "M\tapps/engine/core/models.py\n"
    "A\tapps/engine/tests/test_model_resilience.py\n"
    "\n"
    "__GIT_HISTORY_COMMIT_START__|77368d53de186c05c3d6c46985139d7d9acf2bcc|2026-06-22|other-user|"
    "fix(engine/minimax): flatten tool loop history\n"
    "Resolved schema validation failures by collapsing multi-turn tool loops.\n"
    "\n"
    "__GIT_HISTORY_COMMIT_FILES__\n"
    "M\tapps/engine/core/llm/analysis.py\n"
)


def test_ensure_gitignore(tmp_path):
    gitignore = tmp_path / ".gitignore"
    gitignore.write_text("node_modules/\ndist/", encoding="utf-8")

    ensure_gitignore(target_gitignore=gitignore)

    content = gitignore.read_text(encoding="utf-8")
    assert "git-history/" in content
    assert "# Git History Cache" in content


def test_export_git_history(tmp_path):
    # Setup directories
    history_dir = tmp_path / "git-history"
    history_dir.mkdir(exist_ok=True)

    with patch("apps.engine.export_git_history.run_cmd", return_value=MOCK_GIT_LOG):
        export_git_history(target_dir=history_dir)

        # Assert files exist
        file_07 = history_dir / "2026-07.md"
        file_06 = history_dir / "2026-06.md"

        assert file_07.exists()
        assert file_06.exists()

        # Verify content of 2026-07 file
        content_07 = file_07.read_text(encoding="utf-8")
        assert "---" in content_07
        assert "category: history" in content_07
        assert "Git History — July 2026" in content_07
        assert "Commit: f33a1cdf97c4" in content_07
        assert "Author:** g-vega-cl" in content_07
        assert "Subject:** refactor(engine/models): add case normalization" in content_07
        assert "Improve resilience of structured extractions" in content_07
        assert "`apps/engine/core/models.py` (Modified)" in content_07
        assert "`apps/engine/tests/test_model_resilience.py` (Added)" in content_07

        # Verify content of 2026-06 file
        content_06 = file_06.read_text(encoding="utf-8")
        assert "Git History — June 2026" in content_06
        assert "Commit: 77368d53de18" in content_06
        assert "Author:** other-user" in content_06
        assert "`apps/engine/core/llm/analysis.py` (Modified)" in content_06
