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
