from unittest.mock import MagicMock, patch

from apps.engine.sync_knowledge_documents import (
    fetch_and_export_documents,
    format_document_markdown,
)

DOC_ROW = {
    "slug": "image-carousel",
    "title": "Image Carousel",
    "url": "https://www.greatfrontend.com/questions/system-design/image-carousel",
    "source": "greatfrontend",
    "published_at": "2026-01-04T00:00:00+00:00",
    "access": "premium",
    "content_hash": "hash-v1",
    "markdown": "# Image Carousel\n\n## Requirements\n\n- Must support swipe.\n\n```ts\nexport const a = 1;\n```\n\n### Exercise\n\nPick the right answer.\n",
}


def test_format_document_markdown_keeps_body_verbatim():
    md = format_document_markdown(DOC_ROW)

    assert 'title: "Image Carousel"' in md
    assert 'url: "https://www.greatfrontend.com/questions/system-design/image-carousel"' in md
    assert 'slug: "image-carousel"' in md
    assert 'access: "premium"' in md
    assert 'content_hash: "hash-v1"' in md
    assert "tags: [knowledge-db, frontend, system-design]" in md
    # body must survive untouched: fences and exercise text are part of the corpus
    assert "```ts\nexport const a = 1;\n```" in md
    assert "Pick the right answer." in md


def test_format_document_markdown_handles_null_metadata():
    row = {**DOC_ROW, "published_at": None, "markdown": None, "content_hash": None}
    md = format_document_markdown(row)
    assert 'published_at: ""' in md
    assert "# Image Carousel" in md
    assert md.rstrip().endswith("> **Access:** premium")


def _mock_client(rows):
    """One page of rows, then an empty page so pagination terminates."""
    client = MagicMock()
    table = client.table.return_value
    chain = table.select.return_value.order.return_value

    def _page(payload):
        page = MagicMock()
        page.execute.return_value = MagicMock(data=payload)
        return page

    chain.range.side_effect = [_page(rows), _page([])]
    return client


def test_fetch_and_export_documents_writes_then_skips_unchanged(tmp_path):
    target = tmp_path / "knowledge-db"

    written, skipped = fetch_and_export_documents(_mock_client([DOC_ROW]), target)
    assert (written, skipped) == (1, 0)

    path = target / "greatfrontend" / "image-carousel.md"
    assert path.exists()
    assert "Pick the right answer." in path.read_text(encoding="utf-8")

    written, skipped = fetch_and_export_documents(_mock_client([DOC_ROW]), target)
    assert (written, skipped) == (0, 1)


def test_fetch_and_export_documents_rewrites_on_hash_change(tmp_path):
    target = tmp_path / "knowledge-db"
    fetch_and_export_documents(_mock_client([DOC_ROW]), target)

    updated = {**DOC_ROW, "content_hash": "hash-v2", "markdown": DOC_ROW["markdown"] + "\nNew section.\n"}
    written, skipped = fetch_and_export_documents(_mock_client([updated]), target)
    assert (written, skipped) == (1, 0)
    assert "New section." in (target / "greatfrontend" / "image-carousel.md").read_text(encoding="utf-8")


def test_fetch_and_export_documents_skips_rows_without_markdown(tmp_path):
    rows = [{**DOC_ROW, "markdown": None}, {**DOC_ROW, "slug": "second", "content_hash": "h2"}]
    written, skipped = fetch_and_export_documents(_mock_client(rows), tmp_path)
    assert written == 1
    assert skipped == 1
    assert not (tmp_path / "greatfrontend" / "image-carousel.md").exists()


def test_documents_export_is_dry_runnable(tmp_path):
    written, skipped = fetch_and_export_documents(_mock_client([DOC_ROW]), tmp_path, dry_run=True)
    assert (written, skipped) == (1, 0)
    assert not (tmp_path / "greatfrontend").exists()


def test_secret_key_is_preferred_for_documents():
    from apps.engine.sync_knowledge_db import get_supabase_client

    env = {
        "MISC_SUPABASE_URL": "https://x.supabase.co",
        # a real apps/engine/.env is loaded at import; blank it so precedence is what is tested
        "MISC_SUPABASE_KEY": "",
        "SUPABASE_SECRET_KEY": "sb_secret_new",
        "SUPABASE_KEY": "legacy-anon-jwt",
    }
    with patch("apps.engine.sync_knowledge_db.create_client") as create, patch.dict("os.environ", env, clear=False):
        get_supabase_client()
        create.assert_called_once_with("https://x.supabase.co", "sb_secret_new")
