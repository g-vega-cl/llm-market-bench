#!/usr/bin/env python3
"""Sync knowledge emails from Supabase into a local Markdown directory for QMD search.

Exports records from knowledge_emails into markdown files with YAML frontmatter,
ensures the destination directory is strictly excluded in .gitignore,
and registers/refreshes the 'knowledge-db' collection in QMD.
"""

import argparse
import html
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

import dotenv
from supabase import Client, create_client


def ensure_gitignore(target_gitignore: Path | str | None = None) -> None:
    """Ensure knowledge-db/ cache directory is in .gitignore."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    gitignore_path = Path(target_gitignore) if target_gitignore else repo_root / ".gitignore"

    if not gitignore_path.exists():
        return

    content = gitignore_path.read_text(encoding="utf-8")
    lines = content.splitlines()

    # Check if knowledge-db/ is already present
    if not any(re.match(r"^/?knowledge-db/?$", line.strip()) for line in lines):
        print("[knowledge-sync] Adding knowledge-db/ to .gitignore...")
        with open(gitignore_path, "a", encoding="utf-8") as f:
            f.write("\n# Knowledge DB Cache (QMD collection)\nknowledge-db/\n")


def slugify(text: str) -> str:
    """Convert a title/subject into a clean, filesystem-safe slug."""
    if not text or not text.strip():
        return "untitled"
    # Replace non-alphanumeric with hyphens
    clean = re.sub(r"[^\w\s-]", "-", text).strip().lower()
    clean = re.sub(r"[-\s]+", "-", clean)
    clean = clean.strip("-")
    return clean[:60] if clean else "untitled"


def clean_article_body(raw_body: str | None) -> str:
    """Clean HTML tags and unescape entities into clean markdown/text prose."""
    if not raw_body:
        return ""

    text = raw_body

    # Remove script and style elements entirely
    text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)

    # Convert common HTML linebreaks and paragraphs
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</p>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</div>", "\n", text, flags=re.IGNORECASE)

    # Strip remaining HTML tags
    text = re.sub(r"<[^>]+>", "", text)

    # Unescape HTML entities (&amp;, &quot;, &#39;, etc.)
    text = html.unescape(text)

    # Collapse excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def format_article_markdown(email_row: dict[str, Any]) -> str:
    """Format an email record into structured Markdown with YAML frontmatter."""
    subject = email_row.get("subject") or "Untitled Document"
    sender = email_row.get("sender") or "Unknown"
    received_at = email_row.get("received_at") or ""
    gmail_id = email_row.get("gmail_id") or ""
    body = clean_article_body(email_row.get("body"))

    # Frontmatter safe quoting
    quoted_title = json.dumps(subject, ensure_ascii=False)
    quoted_sender = json.dumps(sender, ensure_ascii=False)
    quoted_date = json.dumps(received_at, ensure_ascii=False)
    quoted_id = json.dumps(gmail_id, ensure_ascii=False)

    lines = [
        "---",
        f"title: {quoted_title}",
        f"sender: {quoted_sender}",
        f"date: {quoted_date}",
        f"gmail_id: {quoted_id}",
        "tags: [knowledge-db, architecture]",
        "category: source",
        "---",
        "",
        f"# {subject}",
        "",
        f"> **Sender:** {sender}  ",
        f"> **Date:** {received_at}  ",
        "",
        body,
        "",
    ]
    return "\n".join(lines)


def run_cmd(command: list[str] | str, shell: bool | None = None) -> str:
    """Run a shell command safely."""
    if shell is None:
        shell = isinstance(command, str)
    try:
        executable = "/bin/bash" if shell else None
        res = subprocess.run(
            command,
            shell=shell,
            executable=executable,
            capture_output=True,
            text=True,
            check=True,
        )
        return res.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        err = getattr(e, "stderr", str(e))
        print(f"[knowledge-sync] Command failed: {command}\nError: {err}", flush=True)
        return ""


def get_supabase_client(
    url: str | None = None,
    key: str | None = None,
    env_file: Path | str | None = None,
) -> Client:
    """Resolve Supabase credentials from args, apps/engine/.env, or ../knowledge-db/.env."""
    if url and key:
        return create_client(url, key)

    repo_root = Path(__file__).resolve().parent.parent.parent

    # Search candidate env files
    env_candidates = [
        Path(env_file) if env_file else None,
        repo_root / "apps/engine/.env",
        repo_root.parent / "knowledge-db/.env",
        repo_root / ".env",
    ]

    resolved_url = os.getenv("MISC_SUPABASE_URL") or os.getenv("SUPABASE_URL") or os.getenv("VITE_SUPABASE_URL")
    resolved_key = (
        os.getenv("MISC_SUPABASE_KEY")
        or os.getenv("SUPABASE_KEY")
        or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("VITE_SUPABASE_ANON_KEY")
    )

    if not resolved_url or not resolved_key:
        for candidate in env_candidates:
            if candidate and candidate.exists():
                dotenv.load_dotenv(candidate)
                resolved_url = (
                    resolved_url
                    or os.getenv("MISC_SUPABASE_URL")
                    or os.getenv("SUPABASE_URL")
                    or os.getenv("VITE_SUPABASE_URL")
                )
                resolved_key = (
                    resolved_key
                    or os.getenv("MISC_SUPABASE_KEY")
                    or os.getenv("SUPABASE_KEY")
                    or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
                    or os.getenv("VITE_SUPABASE_ANON_KEY")
                )
                if resolved_url and resolved_key:
                    break

    if not resolved_url or not resolved_key:
        raise ValueError(
            "Supabase credentials not found. Provide --url/--key or set "
            "MISC_SUPABASE_URL / MISC_SUPABASE_KEY in apps/engine/.env or ../knowledge-db/.env"
        )

    return create_client(resolved_url, resolved_key)


def fetch_and_export_knowledge(
    client: Client,
    target_dir: Path | str,
    batch_size: int = 200,
    limit: int | None = None,
    dry_run: bool = False,
) -> tuple[int, int]:
    """Fetch email articles from Supabase in batches and write markdown files idempotently."""
    dest_path = Path(target_dir)
    dest_path.mkdir(parents=True, exist_ok=True)

    # Cache existing gmail_ids to make sync idempotent
    existing_ids: set[str] = set()
    for existing_file in dest_path.glob("*.md"):
        # Match short_id at the end of the filename: YYYY-MM-DD_slug--<short_id>.md
        if "--" in existing_file.name:
            file_id = existing_file.name.rsplit("--", 1)[1].removesuffix(".md")
            existing_ids.add(file_id)

    exported_count = 0
    skipped_count = 0
    offset = 0

    print(
        f"[knowledge-sync] Found {len(existing_ids)} existing documents in {dest_path}. Starting batch sync...",
        flush=True,
    )

    while True:
        end_offset = offset + batch_size - 1
        query = (
            client.table("knowledge_emails")
            .select("gmail_id,sender,subject,received_at,body")
            .order("received_at", desc=True)
            .range(offset, end_offset)
        )
        response = query.execute()
        rows = response.data or []

        if not rows:
            break

        for row in rows:
            gmail_id = row.get("gmail_id") or ""
            if not gmail_id:
                continue

            short_id = gmail_id[:16]

            # Idempotency check
            if short_id in existing_ids:
                skipped_count += 1
                continue

            date_str = (row.get("received_at") or "2026-01-01")[:10]
            slug = slugify(row.get("subject") or "untitled")
            filename = f"{date_str}_{slug}--{short_id}.md"
            file_path = dest_path / filename

            if not dry_run:
                md_content = format_article_markdown(row)
                file_path.write_text(md_content, encoding="utf-8")
                existing_ids.add(short_id)

            exported_count += 1

            if limit and (exported_count + skipped_count) >= limit:
                return exported_count, skipped_count

        offset += batch_size
        if limit and exported_count >= limit:
            break

    return exported_count, skipped_count


def update_qmd_index(target_dir: Path | str | None = None) -> None:
    """Register 'knowledge-db' collection and refresh the QMD index and embeddings."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    target_path = Path(target_dir) if target_dir else repo_root / "knowledge-db"

    print("[knowledge-sync] Checking QMD status...", flush=True)
    nvm_prefix = 'export NVM_DIR="$HOME/.nvm" && . "$NVM_DIR/nvm.sh" && nvm use 24'

    # Check if QMD is installed
    check_qmd = run_cmd(f"{nvm_prefix} && which qmd")
    if not check_qmd:
        print("[knowledge-sync] WARNING: QMD CLI not found. Skipping collection registration.", flush=True)
        return

    # Check collections
    collections = run_cmd(f"{nvm_prefix} && qmd collection list")

    if "knowledge-db" not in collections:
        print(f"[knowledge-sync] Registering knowledge-db collection at {target_path}...", flush=True)
        run_cmd(f"{nvm_prefix} && qmd collection add {target_path} --name knowledge-db")

    print("[knowledge-sync] Updating QMD index...", flush=True)
    run_cmd(f"{nvm_prefix} && qmd update")
    run_cmd(f"{nvm_prefix} && qmd embed")
    print("[knowledge-sync] QMD indexing completed successfully.", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync Supabase knowledge base to local QMD Markdown collection.")
    parser.add_argument("--dry-run", action="store_true", help="Simulate fetch without writing files.")
    parser.add_argument("--limit", type=int, default=None, help="Maximum records to process.")
    parser.add_argument("--batch-size", type=int, default=200, help="Batch size for Supabase pagination.")
    parser.add_argument("--target-dir", type=str, default=None, help="Target directory (default: ./knowledge-db).")
    parser.add_argument("--no-qmd", action="store_true", help="Skip updating QMD collection index.")
    parser.add_argument("--url", type=str, default=None, help="Supabase project URL.")
    parser.add_argument("--key", type=str, default=None, help="Supabase API key.")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent.parent
    target_dir = Path(args.target_dir) if args.target_dir else repo_root / "knowledge-db"

    # Step 1: Ensure directory is strictly gitignored
    ensure_gitignore()

    # Step 2: Connect to Supabase
    print("[knowledge-sync] Connecting to Supabase...", flush=True)
    client = get_supabase_client(url=args.url, key=args.key)

    # Step 3: Fetch and export
    exported, skipped = fetch_and_export_knowledge(
        client=client,
        target_dir=target_dir,
        batch_size=args.batch_size,
        limit=args.limit,
        dry_run=args.dry_run,
    )

    print(
        f"[knowledge-sync] Sync complete: {exported} new articles exported, {skipped} existing skipped.",
        flush=True,
    )

    # Step 4: Refresh QMD index if changes occurred and not disabled
    if not args.no_qmd and not args.dry_run and exported > 0:
        update_qmd_index(target_dir=target_dir)


if __name__ == "__main__":
    main()
