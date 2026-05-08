#!/usr/bin/env python3
"""Structural lint for wiki/ — checks frontmatter, orphans, broken links, index gaps.

Usage:
    python apps/engine/wiki_lint.py          # check everything
    python apps/engine/wiki_lint.py --quiet  # only print errors

Exit code 0 = clean, 1 = issues found.
"""

import argparse
import re
import sys
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
WIKI_DIR = REPO_ROOT / "wiki"

# Files that are scaffold — don't flag as orphans
SCAFFOLD_FILES = {"SCHEMA.md", "index.md", "log.md"}

# Regex for [[page-name]] wiki links
LINK_RE = re.compile(r"\[\[([^\]]+)\]\]")

# Regex for YAML frontmatter
FM_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)


def parse_frontmatter(content: str) -> dict | None:
    m = FM_RE.match(content)
    if not m:
        return None
    try:
        return yaml.safe_load(m.group(1))
    except yaml.YAMLError:
        return None


def extract_links(content: str) -> list[str]:
    return [m.strip() for m in LINK_RE.findall(content)]


def resolve_link(target: str) -> str | None:
    """Convert a [[link]] to a relative path from wiki/ root. Returns None if unresolvable."""
    if not target.endswith(".md"):
        target += ".md"
    candidate = WIKI_DIR / target
    if candidate.is_file():
        return target
    return None


def find_all_pages() -> dict[str, Path]:
    """Return {relpath: abspath} for all .md files in wiki/."""
    pages = {}
    for f in WIKI_DIR.rglob("*.md"):
        rel = str(f.relative_to(WIKI_DIR))
        pages[rel] = f
    return pages


def build_link_graph(pages: dict[str, Path]) -> dict[str, tuple[set[str], set[str]]]:
    """Return {relpath: (outgoing_links, incoming_links)}."""
    graph = {p: (set(), set()) for p in pages}
    for rel, path in pages.items():
        content = path.read_text()
        outgoing = set()
        for link in extract_links(content):
            resolved = resolve_link(link)
            if resolved:
                outgoing.add(resolved)
                if resolved in graph:
                    graph[resolved][1].add(rel)
        graph[rel] = (outgoing, graph[rel][1])
    return graph


def lint() -> list[str]:
    issues = []
    pages = find_all_pages()
    graph = build_link_graph(pages)

    for rel, path in sorted(pages.items()):
        content = path.read_text()

        # 1. Frontmatter check (skip scaffold files)
        if rel not in SCAFFOLD_FILES:
            fm = parse_frontmatter(content)
            if fm is None:
                issues.append(f"[frontmatter] {rel}: missing or malformed YAML frontmatter")
            elif not isinstance(fm, dict):
                issues.append(f"[frontmatter] {rel}: frontmatter is not a YAML mapping")
            else:
                for field in ("tags", "category"):
                    if field not in fm or not fm[field]:
                        issues.append(f"[frontmatter] {rel}: missing '{field}' field")

        # 2. Broken outgoing links (skip scaffold files — they contain examples)
        if rel not in SCAFFOLD_FILES:
            for link in extract_links(content):
                if not resolve_link(link):
                    issues.append(f"[broken-link] {rel}: [[{link}]] does not resolve to a file")

        # 3. Orphan check (no incoming links)
        incoming = graph[rel][1]
        if rel not in SCAFFOLD_FILES and not incoming:
            issues.append(f"[orphan] {rel}: no incoming links from any wiki page")

    # 4. Index coverage
    index_path = WIKI_DIR / "index.md"
    if index_path.is_file():
        index_content = index_path.read_text()
        index_links = set(extract_links(index_content))

        # Pages not in index (exclude scaffold)
        for rel in sorted(pages):
            if rel in SCAFFOLD_FILES:
                continue
            link_without_ext = rel
            if link_without_ext.endswith(".md"):
                link_without_ext = link_without_ext[:-3]
            if link_without_ext not in index_links and rel not in index_links:
                issues.append(f"[index-gap] {rel}: not referenced in index.md")

        # Index links pointing nowhere
        for link in index_links:
            if not resolve_link(link):
                issues.append(f"[dead-index] index.md: [[{link}]] does not resolve to a file")

    return issues


def main():
    parser = argparse.ArgumentParser(description="Lint wiki/ structure")
    parser.add_argument("--quiet", action="store_true", help="only print errors")
    args = parser.parse_args()

    issues = lint()

    if not issues:
        if not args.quiet:
            print(f"✓ wiki/ is clean ({len(find_all_pages())} pages)")
        sys.exit(0)

    print(f"✗ wiki/ has {len(issues)} issue(s):\n")
    for issue in sorted(issues):
        print(f"  {issue}")

    if not args.quiet:
        print(f"\n{len(issues)} issue(s) total.")

    sys.exit(1)


if __name__ == "__main__":
    main()
