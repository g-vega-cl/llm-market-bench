import sys

import pytest
from apps.engine.commit_msg_lint import main, validate_commit_msg


def test_valid_commit_msg_with_body():
    msg = (
        "feat(web): add today dashboard news feed\n"
        "\n"
        "Implemented news summary time rendering in the card header and\n"
        "added full Vitest test coverage."
    )
    is_valid, errors = validate_commit_msg(msg)
    assert is_valid
    assert not errors


def test_valid_trivial_commit_no_body():
    msg = "chore: bump package dependency versions"
    is_valid, errors = validate_commit_msg(msg)
    assert is_valid
    assert not errors


def test_invalid_subject_format():
    msg = "feat - add today news card feed"
    is_valid, errors = validate_commit_msg(msg)
    assert not is_valid
    assert any("Conventional Commits format" in err for err in errors)


def test_invalid_type():
    msg = "unknown(web): add something\n\nSome descriptive body text here."
    is_valid, errors = validate_commit_msg(msg)
    assert not is_valid
    assert any("Invalid commit type" in err for err in errors)


def test_subject_too_short():
    msg = "fix: ok"
    is_valid, errors = validate_commit_msg(msg)
    assert not is_valid
    assert any("Subject description is too short" in err for err in errors)


def test_subject_too_long():
    msg = "feat: " + ("a" * 105)
    is_valid, errors = validate_commit_msg(msg)
    assert not is_valid
    assert any("Subject line is too long" in err for err in errors)


def test_missing_blank_line_before_body():
    msg = (
        "fix(engine): resolve minimax double buffering\nThis line should have been empty to separate subject and body."
    )
    is_valid, errors = validate_commit_msg(msg)
    assert not is_valid
    assert any("separated by a blank line" in err for err in errors)


def test_missing_required_body():
    msg = "feat(engine): resolve minimax double buffering"
    is_valid, errors = validate_commit_msg(msg)
    assert not is_valid
    assert any("requires a body" in err for err in errors)


def test_body_too_short():
    msg = "feat(engine): resolve minimax double buffering\n\nshort"
    is_valid, errors = validate_commit_msg(msg)
    assert not is_valid
    assert any("Commit body is too short" in err for err in errors)


def test_valid_merge_commit_whitelisted():
    msg = "Merge branch 'main' of github.com:anomalyco/llm-market-bench"
    is_valid, errors = validate_commit_msg(msg)
    assert is_valid
    assert not errors


def test_valid_revert_commit_whitelisted():
    msg = 'Revert "feat(web): add today dashboard news feed"'
    is_valid, errors = validate_commit_msg(msg)
    assert is_valid
    assert not errors


def test_main_missing_arguments(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["commit_msg_lint.py"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 1
    assert "Usage: commit_msg_lint.py" in capsys.readouterr().err


def test_main_file_not_found(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["commit_msg_lint.py", "/nonexistent/commit.txt"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 1
    assert "not found at" in capsys.readouterr().err


def test_main_valid_commit_file(tmp_path, monkeypatch, capsys):
    msg_file = tmp_path / "valid_msg.txt"
    msg_file.write_text(
        "feat(engine): add unit test for commit linter\n\n- Add test_main functions\n- Ensure zero regressions"
    )
    monkeypatch.setattr(sys, "argv", ["commit_msg_lint.py", str(msg_file)])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0
    assert "validation passed" in capsys.readouterr().out


def test_main_invalid_commit_file(tmp_path, monkeypatch, capsys):
    msg_file = tmp_path / "invalid_msg.txt"
    msg_file.write_text("bad commit format without type")
    monkeypatch.setattr(sys, "argv", ["commit_msg_lint.py", str(msg_file)])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 1
    captured = capsys.readouterr()
    assert "ERROR: Commit message validation failed!" in captured.err
