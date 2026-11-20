"""Wikilink handling: code spans are literal, ghost pages are de-linked."""


def test_extract_links_ignores_code_spans_and_fences():
    import apps.engine.wiki_lint as wl

    content = "Real link [[entities/recipe-studio]] and inline `[[examples/target]]`.\n```\n[[fenced/example]]\n```\n"

    assert wl.extract_links(content) == ["entities/recipe-studio"]


def test_sanitize_wikilinks_renders_file_paths_as_code():
    import apps.engine.auto_wiki as aw

    raw = "- [[packages/config/recipe-naming.json]] — config\n- [[entities/recipe-studio]] — page\n"
    sanitized = aw.sanitize_wikilinks(raw)

    assert "`packages/config/recipe-naming.json`" in sanitized
    assert "[[entities/recipe-studio]]" in sanitized


def test_delink_missing_pages_keeps_real_links_only():
    import apps.engine.auto_wiki as aw

    raw = "- [[entities/recipe-studio]] — exists\n- [[entities/ghost-page]] — invented\n"
    result = aw.delink_missing_pages(raw)

    assert "[[entities/recipe-studio]]" in result
    assert "[[entities/ghost-page]]" not in result
    assert "entities/ghost-page" in result


def test_normalize_code_references_resolves_engine_scripts_to_repo_root():
    import apps.engine.auto_wiki as aw

    raw = "See `scripts/update_prices.py`, `scripts/auto-wiki.sh`, and example `wiki/concepts/new-page.md`."
    normalized = aw.normalize_code_references(raw)

    assert "`apps/engine/scripts/update_prices.py`" in normalized
    assert "`scripts/auto-wiki.sh`" in normalized
    assert "`wiki/concepts/new-page.md`" not in normalized
    assert "wiki/concepts/new-page.md" in normalized


def test_write_new_page_normalizes_engine_script_refs(tmp_path, monkeypatch):
    import apps.engine.auto_wiki as aw

    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    monkeypatch.setattr(aw, "WIKI_DIR", wiki_dir)
    recorded: list[str] = []

    aw.write_new_page(
        "concepts/sample.md",
        "---\ntags: [t]\ncategory: concept\n---\n\nSee `scripts/update_prices.py`.\n",
        recorded_paths=recorded,
    )

    written = (wiki_dir / "concepts" / "sample.md").read_text()
    assert "`apps/engine/scripts/update_prices.py`" in written
    assert recorded == ["wiki/concepts/sample.md"]
