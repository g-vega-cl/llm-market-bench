import json
from pathlib import Path
from unittest.mock import patch

from apps.engine.hotspots import (
    CommitRecord,
    HotspotReport,
    analyze_hotspots,
    calculate_coupling,
    calculate_hotspots,
    format_markdown_report,
    format_terminal_table,
    is_bug_fix_commit,
    is_excluded_path,
    parse_git_log,
)


def test_is_excluded_path():
    assert is_excluded_path("apps/web/src/routeTree.gen.ts")
    assert is_excluded_path("pnpm-lock.yaml")
    assert is_excluded_path("apps/engine/.venv/bin/pytest")
    assert is_excluded_path("wiki/concepts/overview.md")
    assert is_excluded_path("supabase/migrations/20260101_init.sql")
    assert is_excluded_path(".husky/pre-commit")

    # Valid application / package files
    assert not is_excluded_path("apps/engine/main.py")
    assert not is_excluded_path("apps/engine/core/llm/analysis.py")
    assert not is_excluded_path("apps/web/src/features/home/pages/HomePage.tsx")
    assert not is_excluded_path("packages/config/models.json")


def test_is_bug_fix_commit():
    assert is_bug_fix_commit("fix(engine): resolve timeout in LLM calls")
    assert is_bug_fix_commit("fix: correct null pointer check")
    assert is_bug_fix_commit("feat(engine): add retry mechanism for bug in provider")
    assert is_bug_fix_commit("refactor: fix broken prompt template")
    assert is_bug_fix_commit("Hotfix: patch trade order validation")

    assert not is_bug_fix_commit("feat(web): add dark mode toggle")
    assert not is_bug_fix_commit("docs: update README with setup instructions")
    assert not is_bug_fix_commit("chore: bump dependencies")


def test_parse_git_log_raw():
    raw_git_output = """COMMIT:abc1234:::feat(engine): add prompt loader
apps/engine/core/llm/prompts.py
apps/engine/core/llm/analysis.py

COMMIT:def5678:::fix(engine): fix broken prompt parsing in analysis
apps/engine/core/llm/analysis.py
apps/web/src/routeTree.gen.ts

COMMIT:9876543:::fix(engine): resolve prompt formatting bug
apps/engine/core/llm/prompts.py
apps/engine/core/llm/analysis.py
"""
    commits = parse_git_log(raw_git_output)
    assert len(commits) == 3

    assert commits[0].commit_hash == "abc1234"
    assert commits[0].subject == "feat(engine): add prompt loader"
    assert not commits[0].is_fix
    assert commits[0].files == [
        "apps/engine/core/llm/prompts.py",
        "apps/engine/core/llm/analysis.py",
    ]

    assert commits[1].commit_hash == "def5678"
    assert commits[1].is_fix
    # routeTree.gen.ts should be filtered out
    assert commits[1].files == ["apps/engine/core/llm/analysis.py"]

    assert commits[2].is_fix
    assert len(commits[2].files) == 2


def test_calculate_hotspots():
    commits = [
        CommitRecord("1", "feat: start", False, ["apps/engine/main.py", "apps/engine/core/config.py"]),
        CommitRecord("2", "fix: repair crash in main", True, ["apps/engine/main.py"]),
        CommitRecord("3", "fix: fix bug in main again", True, ["apps/engine/main.py"]),
        CommitRecord("4", "feat: config update", False, ["apps/engine/core/config.py"]),
    ]

    hotspots = calculate_hotspots(commits)
    assert len(hotspots) == 2

    # main.py: 3 churn, 2 bug fixes => score 6.0
    main_hs = hotspots[0]
    assert main_hs.path == "apps/engine/main.py"
    assert main_hs.churn == 3
    assert main_hs.bug_fixes == 2
    assert round(main_hs.fix_ratio, 3) == round(2 / 3, 3)
    assert main_hs.score == 6.0

    # config.py: 2 churn, 0 bug fixes => score 0.0
    cfg_hs = hotspots[1]
    assert cfg_hs.path == "apps/engine/core/config.py"
    assert cfg_hs.churn == 2
    assert cfg_hs.bug_fixes == 0
    assert cfg_hs.score == 0.0


def test_calculate_coupling():
    commits = [
        CommitRecord("1", "c1", False, ["apps/engine/a.py", "apps/engine/b.py"]),
        CommitRecord("2", "c2", False, ["apps/engine/a.py", "apps/engine/b.py"]),
        CommitRecord("3", "c3", False, ["apps/engine/a.py", "apps/engine/b.py"]),
        CommitRecord("4", "c4", False, ["apps/engine/a.py", "apps/engine/c.py"]),
        CommitRecord("5", "c5", False, ["apps/engine/b.py"]),
    ]

    couplings = calculate_coupling(commits, min_co_commits=3, min_ratio=0.5)
    assert len(couplings) == 1
    c = couplings[0]
    assert c.file_a == "apps/engine/a.py"
    assert c.file_b == "apps/engine/b.py"
    assert c.co_commits == 3
    assert c.ratio_a == 0.75  # 3 out of 4 commits of a.py
    assert c.ratio_b == 0.75  # 3 out of 4 commits of b.py


def test_format_terminal_table_and_markdown():
    report = HotspotReport(
        since="90 days ago",
        total_commits=10,
        hotspots=calculate_hotspots(
            [
                CommitRecord("1", "feat: start", False, ["apps/engine/main.py"]),
                CommitRecord("2", "fix: main fix", True, ["apps/engine/main.py"]),
            ]
        ),
        couplings=[],
    )

    table_output = format_terminal_table(report)
    assert "apps/engine/main.py" in table_output
    assert "90 days ago" in table_output

    md_output = format_markdown_report(report)
    assert "# Code Hotspots & Architectural Friction" in md_output
    assert "apps/engine/main.py" in md_output
    assert "tags: [architecture, code-quality, metrics]" in md_output


@patch("apps.engine.hotspots.run_git_log")
def test_analyze_hotspots(mock_run_git_log, tmp_path: Path):
    mock_run_git_log.return_value = """COMMIT:111:::fix(engine): resolve issue
apps/engine/main.py

COMMIT:222:::feat(engine): init feature
apps/engine/main.py
"""
    report = analyze_hotspots(since="30 days ago", top_n=5)
    assert report.total_commits == 2
    assert len(report.hotspots) == 1
    assert report.hotspots[0].path == "apps/engine/main.py"
    assert report.hotspots[0].churn == 2
    assert report.hotspots[0].bug_fixes == 1

    # Test JSON dump
    data = json.loads(report.to_json())
    assert data["since"] == "30 days ago"
    assert data["total_commits"] == 2
    assert len(data["hotspots"]) == 1


@patch("apps.engine.hotspots.analyze_hotspots")
def test_main_cli_json(mock_analyze, capsys):
    mock_analyze.return_value = HotspotReport(
        since="90 days ago",
        total_commits=1,
        hotspots=[],
        couplings=[],
    )
    with patch("sys.argv", ["hotspots.py", "--json"]):
        from apps.engine.hotspots import main

        exit_code = main()
        assert exit_code == 0
        captured = capsys.readouterr()
        assert '"total_commits": 1' in captured.out


@patch("apps.engine.hotspots.analyze_hotspots")
def test_main_cli_write_wiki(mock_analyze, tmp_path, capsys):
    wiki_dest = tmp_path / "code-hotspots.md"
    mock_analyze.return_value = HotspotReport(
        since="90 days ago",
        total_commits=1,
        hotspots=[],
        couplings=[],
    )
    with patch("sys.argv", ["hotspots.py", "--write-wiki"]), patch("apps.engine.hotspots.WIKI_FILE", wiki_dest):
        from apps.engine.hotspots import main

        exit_code = main()
        assert exit_code == 0
        assert wiki_dest.exists()
        assert "# Code Hotspots & Architectural Friction" in wiki_dest.read_text()


def test_determine_risk_level_and_loc():
    from apps.engine.hotspots import determine_risk_level, get_file_loc

    assert determine_risk_level(150, 10, 0.5) == "CRITICAL"
    assert determine_risk_level(20, 15, 0.4) == "CRITICAL"
    assert determine_risk_level(35, 5, 0.1) == "HIGH"
    assert determine_risk_level(15, 10, 0.3) == "HIGH"
    assert determine_risk_level(10, 2, 0.0) == "MEDIUM"
    assert determine_risk_level(2, 10, 0.0) == "MEDIUM"
    assert determine_risk_level(1, 2, 0.0) == "LOW"

    # Non-existent file LOC
    assert get_file_loc("non/existent/file.py") == 0


@patch("apps.engine.hotspots.analyze_hotspots")
def test_main_cli_error(mock_analyze, capsys):
    import subprocess

    mock_analyze.side_effect = subprocess.CalledProcessError(1, ["git"])
    with patch("sys.argv", ["hotspots.py"]):
        from apps.engine.hotspots import main

        exit_code = main()
        assert exit_code == 1
