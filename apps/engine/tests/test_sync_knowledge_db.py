from unittest.mock import MagicMock, patch

from apps.engine.sync_knowledge_db import (
    clean_article_body,
    ensure_gitignore,
    fetch_and_export_knowledge,
    format_article_markdown,
    slugify,
    update_qmd_index,
)


def test_ensure_gitignore_adds_entry(tmp_path):
    gitignore = tmp_path / ".gitignore"
    gitignore.write_text("node_modules/\ndist/\n", encoding="utf-8")

    ensure_gitignore(target_gitignore=gitignore)

    content = gitignore.read_text(encoding="utf-8")
    assert "knowledge-db/" in content
    assert "# Knowledge DB Cache (QMD collection)" in content

    # Calling again should not duplicate entry
    ensure_gitignore(target_gitignore=gitignore)
    assert content.count("knowledge-db/") == 1


def test_slugify():
    assert (
        slugify("Knowing When to Stop Engineering: Airbnb's Lesson")
        == "knowing-when-to-stop-engineering-airbnb-s-lesson"
    )
    assert slugify("EP200: HTTP/2 over TCP vs HTTP/3 over QUIC! #1") == "ep200-http-2-over-tcp-vs-http-3-over-quic-1"
    assert slugify("") == "untitled"


def test_clean_article_body():
    html_input = "<p>Hello <b>World</b>&amp;friends!</p><br><div>Next line</div><style>bad { color: red; }</style>"
    cleaned = clean_article_body(html_input)
    assert "Hello" in cleaned
    assert "World&friends!" in cleaned
    assert "Next line" in cleaned
    assert "<style>" not in cleaned
    assert "bad { color: red; }" not in cleaned


def test_format_article_markdown():
    email_row = {
        "gmail_id": "19c1858e098d1536",
        "sender": "Byte-Sized Design <bytesizeddesign@substack.com>",
        "subject": "Knowing When to Stop Engineering: Airbnb’s Hardest Lesson",
        "received_at": "2026-02-01T07:36:29+00:00",
        "body": "This is an architectural deep dive into stopping engineering over-complexity.",
    }
    md = format_article_markdown(email_row)
    assert "---" in md
    assert 'title: "Knowing When to Stop Engineering: Airbnb’s Hardest Lesson"' in md
    assert 'sender: "Byte-Sized Design <bytesizeddesign@substack.com>"' in md
    assert 'gmail_id: "19c1858e098d1536"' in md
    assert "tags: [knowledge-db, architecture]" in md
    assert "# Knowing When to Stop Engineering: Airbnb’s Hardest Lesson" in md
    assert "This is an architectural deep dive" in md


def test_fetch_and_export_knowledge_idempotency(tmp_path):
    target_dir = tmp_path / "knowledge-db"
    target_dir.mkdir(exist_ok=True)

    # Mock Supabase client
    mock_supabase = MagicMock()
    mock_table = MagicMock()
    mock_select = MagicMock()
    mock_order = MagicMock()

    mock_supabase.table.return_value = mock_table
    mock_table.select.return_value = mock_select
    mock_select.order.return_value = mock_order

    sample_rows = [
        {
            "gmail_id": "id_100",
            "sender": "Author One <author1@example.com>",
            "subject": "Pattern 1: Circuit Breaker",
            "received_at": "2026-02-01T10:00:00Z",
            "body": "Circuit breaker body text.",
        },
        {
            "gmail_id": "id_200",
            "sender": "Author Two <author2@example.com>",
            "subject": "Pattern 2: Event Sourcing",
            "received_at": "2026-02-02T11:00:00Z",
            "body": "Event sourcing body text.",
        },
    ]

    # First page returns 2 rows, second page returns empty list
    mock_range_1 = MagicMock()
    mock_range_1.execute.return_value = MagicMock(data=sample_rows)
    mock_range_2 = MagicMock()
    mock_range_2.execute.return_value = MagicMock(data=[])

    mock_order.range.side_effect = [mock_range_1, mock_range_2]

    # Initial export
    exported, skipped = fetch_and_export_knowledge(
        client=mock_supabase,
        target_dir=target_dir,
        batch_size=2,
    )
    assert exported == 2
    assert skipped == 0

    files = list(target_dir.glob("*.md"))
    assert len(files) == 2

    # Second export: rows already exist on disk, should skip both
    mock_order.range.side_effect = [mock_range_1, mock_range_2]
    exported_2, skipped_2 = fetch_and_export_knowledge(
        client=mock_supabase,
        target_dir=target_dir,
        batch_size=2,
    )
    assert exported_2 == 0
    assert skipped_2 == 2


def test_update_qmd_index():
    with patch("apps.engine.sync_knowledge_db.run_cmd") as mock_run:
        # Mock checking QMD: installed, collection not yet registered
        mock_run.side_effect = [
            "/home/cv/.nvm/versions/node/v24.22.1/bin/qmd",  # which qmd
            "Collections (2):\n  wiki\n  git-history",  # qmd collection list
            "",  # qmd collection add
            "",  # qmd update
            "",  # qmd embed
        ]

        update_qmd_index(target_dir="/tmp/test-kdb")

        assert mock_run.call_count == 5
        add_call = mock_run.call_args_list[2][0][0]
        assert "qmd collection add /tmp/test-kdb --name knowledge-db" in add_call
