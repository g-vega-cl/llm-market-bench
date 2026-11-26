"""Tests for wiki SCHEMA conventions and auto_wiki page-deletion enforcement."""

import pathlib

import pytest

REPO_ROOT = pathlib.Path(__file__).parents[3]
WIKI_DIR = REPO_ROOT / "wiki"
SCHEMA_PATH = WIKI_DIR / "SCHEMA.md"


# ---------------------------------------------------------------------------
# SCHEMA.md rule tests
# ---------------------------------------------------------------------------


def test_schema_contains_page_deletion_rule():
    """SCHEMA.md must document the page-deletion-on-scope-removal rule."""
    content = SCHEMA_PATH.read_text()
    assert "Page Deletion on Scope Removal" in content, (
        "wiki/SCHEMA.md is missing the 'Page Deletion on Scope Removal' "
        "maintenance rule. Add it under ## Maintenance Rules."
    )


def test_schema_deletion_log_format():
    """SCHEMA.md must document that page deletions are tracked via Git history."""
    content = SCHEMA_PATH.read_text()
    assert "git commit history" in content.lower(), (
        "wiki/SCHEMA.md must document that page deletions are tracked via Git commit history."
    )


# ---------------------------------------------------------------------------
# apply_page_deletions() unit tests
# ---------------------------------------------------------------------------


def _make_wiki(tmp_path: pathlib.Path) -> pathlib.Path:
    """Create a minimal fake wiki directory structure."""
    wiki = tmp_path / "wiki"
    wiki.mkdir()

    # Create a page to be deleted
    (wiki / "entities").mkdir()
    page = wiki / "entities" / "old-module.md"
    page.write_text("---\ntags: [old]\ncategory: entity\n---\n\n# Old Module\n\nStale page.\n")

    # Create index.md referencing the page
    (wiki / "index.md").write_text(
        "# Index\n\n## Entities\n\n"
        "- [[entities/old-module]] — old module description\n"
        "- [[entities/active]] — active component\n"
    )

    return wiki


def test_apply_page_deletions_removes_file(tmp_path, monkeypatch):
    """apply_page_deletions must delete the physical file."""
    import apps.engine.auto_wiki as aw

    wiki = _make_wiki(tmp_path)
    monkeypatch.setattr(aw, "WIKI_DIR", wiki)

    page_path = wiki / "entities" / "old-module.md"
    assert page_path.exists(), "precondition: page should exist before deletion"

    aw.apply_page_deletions(["entities/old-module.md"])

    assert not page_path.exists(), "apply_page_deletions must delete the file"


def test_apply_page_deletions_removes_index_entry(tmp_path, monkeypatch):
    """apply_page_deletions must remove the [[link]] line from index.md."""
    import apps.engine.auto_wiki as aw

    wiki = _make_wiki(tmp_path)
    monkeypatch.setattr(aw, "WIKI_DIR", wiki)

    aw.apply_page_deletions(["entities/old-module.md"])

    index_content = (wiki / "index.md").read_text()
    assert "old-module" not in index_content, "apply_page_deletions must remove the deleted page's entry from index.md"
    # Active entry must be preserved
    assert "[[entities/active]]" in index_content, "apply_page_deletions must not remove other index entries"


def test_apply_page_deletions_rejects_path_traversal(tmp_path, monkeypatch, capsys):
    """apply_page_deletions must reject paths that escape WIKI_DIR."""
    import apps.engine.auto_wiki as aw

    wiki = _make_wiki(tmp_path)
    monkeypatch.setattr(aw, "WIKI_DIR", wiki)

    # Attempt traversal
    aw.apply_page_deletions(["../../etc/passwd"])

    captured = capsys.readouterr()
    assert "path traversal" in captured.err.lower(), (
        "apply_page_deletions must log a path traversal error and skip the delete"
    )


def test_apply_page_deletions_missing_file_is_noop(tmp_path, monkeypatch):
    """apply_page_deletions must not crash when the target file is already gone."""
    import apps.engine.auto_wiki as aw

    wiki = _make_wiki(tmp_path)
    monkeypatch.setattr(aw, "WIKI_DIR", wiki)

    # Should not raise
    aw.apply_page_deletions(["entities/nonexistent.md"])


@pytest.mark.parametrize(
    "result",
    [
        {"should_update": True, "deleted_pages": ["entities/old-module.md"]},
    ],
)
def test_main_calls_apply_page_deletions(tmp_path, monkeypatch, result):
    """When the LLM result contains deleted_pages, apply_changes must call apply_page_deletions."""
    import apps.engine.auto_wiki as aw

    wiki = _make_wiki(tmp_path)
    monkeypatch.setattr(aw, "WIKI_DIR", wiki)

    called_with = []

    def fake_apply(paths):
        called_with.extend(paths)

    monkeypatch.setattr(aw, "apply_page_deletions", fake_apply)

    # Patch write_new_page and add_index_entries to no-ops
    monkeypatch.setattr(aw, "write_new_page", lambda *a, **kw: None)
    monkeypatch.setattr(aw, "add_index_entries", lambda *a, **kw: None)

    aw.apply_changes(result)

    assert "entities/old-module.md" in called_with, "apply_changes must forward deleted_pages to apply_page_deletions"


def test_auto_wiki_default_model():
    """auto_wiki default model must be ~deepseek/deepseek-flash-latest."""
    import apps.engine.auto_wiki as aw

    assert aw.DEFAULT_MODEL == "~deepseek/deepseek-flash-latest"


def test_auto_wiki_preservation_mandate_in_system_prompt():
    """auto_wiki SYSTEM_PROMPT must mandate preserving existing tools, schemas, and architecture."""
    import apps.engine.auto_wiki as aw

    prompt = aw.SYSTEM_PROMPT.lower()
    assert "preserve" in prompt, "SYSTEM_PROMPT must instruct model to preserve existing documentation"
    assert "tool" in prompt, "SYSTEM_PROMPT must mention preserving tool signatures"


def test_auto_wiki_extract_diff_filenames():
    """extract_diff_filenames must parse paths of modified files from git diff."""
    import apps.engine.auto_wiki as aw

    diff = """diff --git a/apps/engine/tasks/future_forces_task.py b/apps/engine/tasks/future_forces_task.py
index 123..456 100644
--- a/apps/engine/tasks/future_forces_task.py
+++ b/apps/engine/tasks/future_forces_task.py
@@ -10,3 +10,4 @@
+new_code()
"""
    files = aw.extract_diff_filenames(diff)
    assert files == ["apps/engine/tasks/future_forces_task.py"]


def test_auto_wiki_find_related_wiki_pages(tmp_path, monkeypatch):
    """find_related_wiki_pages must locate existing wiki pages matching modified files."""
    import apps.engine.auto_wiki as aw

    wiki = tmp_path / "wiki"
    wiki.mkdir()
    (wiki / "entities").mkdir()
    target_page = wiki / "entities" / "future-forces-portfolio.md"
    target_page.write_text("# Future Forces\nReferences `future_forces_task.py`.\n")

    monkeypatch.setattr(aw, "WIKI_DIR", wiki)

    matches = aw.find_related_wiki_pages(["apps/engine/tasks/future_forces_task.py"])
    assert "entities/future-forces-portfolio.md" in matches
    assert "future_forces_task.py" in matches["entities/future-forces-portfolio.md"]


def test_auto_wiki_collect_wiki_context_includes_related_pages(tmp_path, monkeypatch):
    """collect_wiki_context must include related existing wiki pages when diff mentions them."""
    import apps.engine.auto_wiki as aw

    wiki = tmp_path / "wiki"
    wiki.mkdir()
    (wiki / "entities").mkdir()
    target_page = wiki / "entities" / "future-forces-portfolio.md"
    target_page.write_text("# Future Forces\nReferences `future_forces_task.py`.\n")

    monkeypatch.setattr(aw, "WIKI_DIR", wiki)

    diff = """diff --git a/apps/engine/tasks/future_forces_task.py b/apps/engine/tasks/future_forces_task.py
index 123..456 100644
--- a/apps/engine/tasks/future_forces_task.py
+++ b/apps/engine/tasks/future_forces_task.py
@@ -10,3 +10,4 @@
+new_code()
"""
    context = aw.collect_wiki_context(diff)
    assert "future-forces-portfolio.md" in context
    assert "PRESERVE ALL INVARIANTS" in context


# ---------------------------------------------------------------------------
# Tier chain: free-llm-proxy (auto-go) is tier 1, OpenRouter is the fallback
# ---------------------------------------------------------------------------


def _tier_args(**overrides):
    import types

    base = {"model": "or-primary", "free_model": "or-free", "proxy_model": "auto-go"}
    base.update(overrides)
    return types.SimpleNamespace(**base)


def test_auto_wiki_calls_the_proxy_first(monkeypatch):
    """The in-repo proxy must be tier 1: auto-go walks free providers before the
    paid tail, so it is the cheap path and OpenRouter is the backup."""
    import apps.engine.auto_wiki as aw

    calls = []
    monkeypatch.setattr(aw, "get_proxy_config", lambda: ("http://proxy/v1", "key"))
    monkeypatch.setattr(
        aw,
        "call_free_proxy",
        lambda prompt, model=None: calls.append(("proxy", model)) or {"should_update": False},
    )
    monkeypatch.setattr(
        aw,
        "call_openrouter",
        lambda prompt, model, api_key: calls.append(("openrouter", model)) or {"should_update": True},
    )

    result = aw.generate_with_fallback("prompt", _tier_args(), "or-key")

    assert calls == [("proxy", "auto-go")]
    assert result == {"should_update": False}


def test_auto_wiki_falls_back_to_openrouter_when_the_proxy_fails(monkeypatch):
    import apps.engine.auto_wiki as aw
    import requests

    calls = []

    def failing_proxy(prompt, model=None):
        calls.append(("proxy", model))
        raise requests.RequestException("proxy down")

    monkeypatch.setattr(aw, "get_proxy_config", lambda: ("http://proxy/v1", "key"))
    monkeypatch.setattr(aw, "call_free_proxy", failing_proxy)
    monkeypatch.setattr(
        aw,
        "call_openrouter",
        lambda prompt, model, api_key: calls.append(("openrouter", model)) or {"should_update": True},
    )

    result = aw.generate_with_fallback("prompt", _tier_args(), "or-key")

    assert calls == [("proxy", "auto-go"), ("openrouter", "or-primary")]
    assert result == {"should_update": True}


def test_auto_wiki_skips_the_proxy_when_it_has_no_key(monkeypatch):
    """A clone with only an OpenRouter key must still document instead of aborting."""
    import apps.engine.auto_wiki as aw

    calls = []

    def unconfigured():
        raise RuntimeError("FREE_PROXY_MASTER_KEY is required")

    monkeypatch.setattr(aw, "get_proxy_config", unconfigured)
    monkeypatch.setattr(
        aw,
        "call_free_proxy",
        lambda prompt, model=None: calls.append(("proxy", model)) or {"should_update": True},
    )
    monkeypatch.setattr(
        aw,
        "call_openrouter",
        lambda prompt, model, api_key: calls.append(("openrouter", model)) or {"should_update": True},
    )

    aw.generate_with_fallback("prompt", _tier_args(), "or-key")

    assert calls == [("openrouter", "or-primary")]


def test_auto_wiki_proxy_timeout_is_bounded_for_the_hook(monkeypatch):
    """A saturated free pool must not stall a commit: the proxy tier is capped."""
    import importlib

    import apps.engine.auto_wiki as aw

    monkeypatch.setenv("WIKI_DOC_PROXY_TIMEOUT_SECONDS", "15")
    reloaded = importlib.reload(aw)
    try:
        assert reloaded.PROXY_TIMEOUT_SECONDS == 15
    finally:
        monkeypatch.delenv("WIKI_DOC_PROXY_TIMEOUT_SECONDS", raising=False)
        importlib.reload(aw)


def test_auto_wiki_proxy_timeout_defaults_below_four_minutes():
    import apps.engine.auto_wiki as aw

    assert 165 <= aw.PROXY_TIMEOUT_SECONDS <= 239, (
        "proxy timeout must exceed free-llm-proxy's 165s free+paid deadline while staying below four minutes"
    )


def test_auto_wiki_find_related_wiki_pages_ignores_bare_prose_stem_matches(tmp_path, monkeypatch):
    """Modifying execution/portfolio.py must not match unrelated pages merely mentioning 'portfolio'."""
    import apps.engine.auto_wiki as aw

    wiki = tmp_path / "wiki"
    (wiki / "entities").mkdir(parents=True)
    (wiki / "entities" / "unrelated.md").write_text("# Home\nDisplays the user's portfolio balance.\n")
    (wiki / "entities" / "portfolio-engine.md").write_text(
        "# Portfolio\nImplemented in `apps/engine/execution/portfolio.py`.\n"
    )

    monkeypatch.setattr(aw, "WIKI_DIR", wiki)

    matches = aw.find_related_wiki_pages(["apps/engine/execution/portfolio.py"])
    assert "entities/portfolio-engine.md" in matches
    assert "entities/unrelated.md" not in matches


def test_auto_wiki_free_backup_runs_last_and_failure_blocks_the_commit(monkeypatch):
    import apps.engine.auto_wiki as aw
    import requests

    calls = []

    def failing_proxy(prompt, model=None):
        raise requests.RequestException("proxy down")

    def failing_openrouter(prompt, model, api_key):
        calls.append(("openrouter", model))
        raise RuntimeError(f"tier failed: {model}")

    monkeypatch.setattr(aw, "get_proxy_config", lambda: ("http://proxy/v1", "key"))
    monkeypatch.setattr(aw, "call_free_proxy", failing_proxy)
    monkeypatch.setattr(aw, "call_openrouter", failing_openrouter)

    with pytest.raises(SystemExit) as exc:
        aw.generate_with_fallback("prompt", _tier_args(), "or-key")

    assert exc.value.code == 1
    assert calls == [("openrouter", "or-primary"), ("openrouter", "or-free")]
