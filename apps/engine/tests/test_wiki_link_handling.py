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
