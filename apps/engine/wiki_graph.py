"""Deterministic on-demand reverse code-to-wiki dependency graph and topic-map renderer."""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCAFFOLD_FILES = {"SCHEMA.md", "index.md"}

GRAPH_PATH_RE = re.compile(
    r"(?:`|\[.*?\]\()(?:(apps|packages|scripts|supabase|docker|\.github|\.agents|\.pi|\.husky)(?:\/([a-zA-Z0-9_\-\.\/]+))?|(AGENTS\.md|PRODUCT\.md))(?:`|\))"
)


def extract_code_paths(content: str, repo_root: Path = REPO_ROOT) -> set[str]:
    """Extract existing repository file and directory paths referenced in a wiki page."""
    found: set[str] = set()
    for prefix, subpath, root_doc in GRAPH_PATH_RE.findall(content):
        rel = root_doc or (f"{prefix}/{subpath}".rstrip("/.,;") if subpath else prefix)
        if not rel or ".env" in rel or ".venv" in rel or rel.endswith("/dist") or "/dist/" in rel:
            continue
        if (repo_root / rel).exists():
            found.add(rel)
    return found


def build_code_to_wiki_map(
    pages: dict[str, Path],
    repo_root: Path = REPO_ROOT,
) -> dict[str, list[str]]:
    """Build deterministic reverse index mapping repo code paths to citing wiki pages."""
    mapping: dict[str, set[str]] = {}
    for rel, path in pages.items():
        if rel in SCAFFOLD_FILES or rel.startswith("sources/"):
            continue
        for code_path in extract_code_paths(path.read_text(), repo_root):
            mapping.setdefault(code_path, set()).add(rel)
    return {k: sorted(v) for k, v in sorted(mapping.items())}


def resolve_affected_pages(
    changed_files: list[str],
    code_map: dict[str, list[str]],
) -> dict[str, list[str]]:
    """Return {changed_file: [wiki_rel_paths]} for exact or ancestor-directory matches."""
    results: dict[str, list[str]] = {}
    for raw_path in changed_files:
        norm = raw_path.strip().lstrip("./").rstrip("/")
        if not norm:
            continue
        matched: set[str] = set(code_map.get(norm, []))
        parts = norm.split("/")
        min_depth = 2 if parts[0] in {"apps", "packages"} else 1
        for depth in range(len(parts) - 1, min_depth - 1, -1):
            ancestor = "/".join(parts[:depth])
            matched.update(code_map.get(ancestor, []))
        if matched:
            results[norm] = sorted(matched)
    return results


def _subsystem_key(code_path: str) -> str:
    parts = code_path.split("/")
    if parts[0] in {"apps", "packages"} and len(parts) >= 2:
        return f"{parts[0]}/{parts[1]}"
    return parts[0]


def format_topic_map(code_map: dict[str, list[str]]) -> str:
    """Render on-demand code-to-wiki reverse links grouped by subsystem."""
    groups: dict[str, list[tuple[str, list[str]]]] = {}
    for code_path, wiki_rels in code_map.items():
        groups.setdefault(_subsystem_key(code_path), []).append((code_path, wiki_rels))

    lines = [
        "# Code-to-Wiki Topic Map",
        "",
        "Derived on demand from repository citations across `wiki/` (`wiki_lint.py --topic-map`).",
        "",
    ]
    for subsystem in sorted(groups):
        lines.append(f"## `{subsystem}`")
        lines.append("")
        for code_path, wiki_rels in groups[subsystem]:
            links = ", ".join(f"[[{w[:-3] if w.endswith('.md') else w}]]" for w in wiki_rels[:6])
            suffix = f" (+{len(wiki_rels) - 6} more)" if len(wiki_rels) > 6 else ""
            lines.append(f"- `{code_path}` -> {links}{suffix}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
