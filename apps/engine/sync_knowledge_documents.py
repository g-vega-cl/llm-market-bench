#!/usr/bin/env python3
"""Mirror long-form articles (`knowledge_documents`) from Supabase into QMD markdown.

Companion to `sync_knowledge_db.py`: that module exports the email corpus, this one
exports the parsed articles so a single QMD collection (`knowledge-db`) covers both.

Files land in `<target-dir>/greatfrontend/<slug>.md` with YAML frontmatter and the
stored Markdown body verbatim — QMD chunks on headings itself, so one file per
document keeps `qmd get` returning a coherent, section-aware article.
"""

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from supabase import Client

DOCUMENTS_SUBDIR = "greatfrontend"
TAGS = "[knowledge-db, frontend, system-design]"
FRONTMATTER_KEYS = ("title", "url", "source", "slug", "access", "published_at", "content_hash")


def _quote(value: Any) -> str:
    """Frontmatter-safe JSON string (handles quotes, unicode, None)."""
    return json.dumps("" if value is None else str(value), ensure_ascii=False)


def safe_slug(slug: str | None, title: str | None = None) -> str:
    """Filesystem-safe slug that keeps stable inputs stable."""
    raw = (slug or title or "untitled").strip().lower()
    clean = re.sub(r"[^a-z0-9]+", "-", raw).strip("-")
    return clean[:80] or "untitled"


def content_hash(row: dict[str, Any]) -> str:
    """Prefer the producer's hash; fall back to hashing the Markdown itself."""
    stored = (row.get("content_hash") or "").strip()
    if stored:
        return stored
    return hashlib.sha256((row.get("markdown") or "").encode("utf-8")).hexdigest()


def format_document_markdown(row: dict[str, Any]) -> str:
    """Render a `knowledge_documents` row as frontmatter + verbatim body."""
    title = row.get("title") or "Untitled Document"
    url = row.get("url") or ""
    access = row.get("access") or ""
    body = (row.get("markdown") or "").rstrip()

    lines = [
        "---",
        f"title: {_quote(title)}",
        f"url: {_quote(url)}",
        f"source: {_quote(row.get('source') or 'greatfrontend')}",
        f"slug: {_quote(row.get('slug') or '')}",
        f"access: {_quote(access)}",
        f"published_at: {_quote(row.get('published_at'))}",
        f'content_hash: "{content_hash(row)}"',
        f"tags: {TAGS}",
        "category: source",
        "---",
        "",
        f"# {title}",
        "",
        f"> **Source:** {url}  ",
        f"> **Access:** {access or 'unknown'}  ",
        "",
    ]
    if body:
        lines.extend([body, ""])
    return "\n".join(lines)


def read_stored_hash(path: Path) -> str | None:
    """Return the `content_hash` recorded in an existing mirror file."""
    try:
        head = path.read_text(encoding="utf-8")[:2000]
    except OSError:
        return None
    match = re.search(r'^content_hash: "?([^"\n]+)"?$', head, re.MULTILINE)
    return match.group(1) if match else None


def fetch_and_export_documents(
    client: Client,
    target_dir: Path | str,
    batch_size: int = 200,
    dry_run: bool = False,
) -> tuple[int, int]:
    """Paginate `knowledge_documents` and write `<target>/greatfrontend/<slug>.md`.

    Rewrites a file when its stored `content_hash` changes, so a re-parse upstream
    propagates without deleting the mirror first.
    """
    dest = Path(target_dir) / DOCUMENTS_SUBDIR
    if not dry_run:
        dest.mkdir(parents=True, exist_ok=True)

    written = 0
    skipped = 0
    offset = 0
    total_seen = 0

    while True:
        response = (
            client.table("knowledge_documents")
            .select("slug,title,url,source,published_at,access,markdown,content_hash")
            .order("slug")
            .range(offset, offset + batch_size - 1)
            .execute()
        )
        rows = [row for row in (response.data or []) if isinstance(row, dict)]
        if not rows:
            if offset == 0:
                print(
                    "[knowledge-sync] WARNING: knowledge_documents returned 0 rows — "
                    "the resolved API key probably lacks the service/secret role.",
                    flush=True,
                )
            break
        total_seen += len(rows)

        for row in rows:
            if not (row.get("markdown") or "").strip():
                skipped += 1
                continue

            path = dest / f"{safe_slug(row.get('slug'), row.get('title'))}.md"
            if path.exists() and read_stored_hash(path) == content_hash(row):
                skipped += 1
                continue

            if not dry_run:
                path.write_text(format_document_markdown(row), encoding="utf-8")
            written += 1

        offset += batch_size

    if total_seen:
        print(f"[knowledge-sync] knowledge_documents: {total_seen} rows visible", flush=True)
    return written, skipped
