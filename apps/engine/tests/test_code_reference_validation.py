from apps.engine.wiki_lint import validate_codebase_references


def test_validate_codebase_references_success(tmp_path):
    # Create mock repo root
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Create a valid file
    valid_file = repo_root / "apps" / "engine" / "wiki_lint.py"
    valid_file.parent.mkdir(parents=True)
    valid_file.touch()

    # Text with valid reference
    content = "Check out the linter at `apps/engine/wiki_lint.py` for rules."

    errors = validate_codebase_references(content, repo_root, "some-page.md")
    assert len(errors) == 0


def test_validate_codebase_references_failure(tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Text with invalid reference
    content = "Check out the linter at `apps/engine/missing_file.py` for rules."

    errors = validate_codebase_references(content, repo_root, "some-page.md")
    assert len(errors) == 1
    assert "Broken code reference" in errors[0]


def test_validate_codebase_references_exclusions(tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Text with invalid reference but inside an excluded page
    content = "Check out the linter at `apps/engine/missing_file.py` for rules."

    # SCHEMA.md is excluded
    errors = validate_codebase_references(content, repo_root, "SCHEMA.md")
    assert len(errors) == 0

    # concepts/code-reference-validation.md is excluded
    errors = validate_codebase_references(content, repo_root, "concepts/code-reference-validation.md")
    assert len(errors) == 0


def test_validate_codebase_references_placeholders(tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Text with a path containing a wildcard/placeholder YYYY-MM
    content = "See `wiki/log/YYYY-MM.md` for historical logs."

    errors = validate_codebase_references(content, repo_root, "some-page.md")
    assert len(errors) == 0


def test_validate_codebase_references_runtime_env_paths(tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Text referencing gitignored runtime env paths (.env, .venv) that do not exist on disk
    content = "See `apps/engine/.env` and `./apps/engine/.venv/bin/` for runtime configuration."

    errors = validate_codebase_references(content, repo_root, "some-page.md")
    assert len(errors) == 0
