"""Reproduction and regression tests for wiki and documentation consistency."""

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
WIKI_DIR = REPO_ROOT / "wiki"
README_PATH = REPO_ROOT / "README.md"
MODELS_JSON = REPO_ROOT / "packages" / "config" / "models.json"


def test_no_duplicate_links_in_wiki_index():
    """Ensure wiki/index.md contains no duplicate [[link]] targets."""
    index_file = WIKI_DIR / "index.md"
    assert index_file.is_file()

    content = index_file.read_text()
    link_re = re.compile(r"\[\[([^\]]+)\]\]")
    seen_links = set()
    duplicates = []

    for line in content.splitlines():
        match = link_re.search(line)
        if match:
            target = match.group(1).strip()
            if target in seen_links:
                duplicates.append(target)
            seen_links.add(target)

    assert not duplicates, f"Found duplicate links in wiki/index.md: {duplicates}"


def test_no_hardcoded_macos_user_paths_in_wiki():
    """Ensure no wiki markdown files contain hardcoded macOS /Users/... machine paths."""
    macos_path_re = re.compile(r"/(?:Users)/[a-zA-Z0-9_\-\./]+")
    offending_files = []

    for md_file in WIKI_DIR.rglob("*.md"):
        content = md_file.read_text(errors="ignore")
        matches = macos_path_re.findall(content)
        if matches:
            offending_files.append((str(md_file.relative_to(REPO_ROOT)), matches))

    assert not offending_files, f"Found hardcoded macOS paths in wiki files: {offending_files}"


def test_readme_utility_script_paths_exist():
    """Ensure all python utility script paths referenced in README.md exist on disk."""
    assert README_PATH.is_file()
    content = README_PATH.read_text()

    # Match `python apps/engine/...` or `python apps/engine/scripts/...`
    script_re = re.compile(r"`python\s+(apps/engine/[a-zA-Z0-9_\-/]+\.py)`")
    matches = script_re.findall(content)
    assert matches, "Expected to find python script references in README.md"

    missing = []
    for rel_path in matches:
        full_path = REPO_ROOT / rel_path
        if not full_path.exists():
            missing.append(rel_path)

    assert not missing, f"README references nonexistent script paths: {missing}"


def test_alpaca_audit_cli_models_are_active():
    """Ensure CLI model examples in alpaca-audit.md reference active configured models."""
    audit_doc = WIKI_DIR / "entities" / "alpaca-audit.md"
    assert audit_doc.is_file()

    models_data = json.loads(MODELS_JSON.read_text())
    active_models = set()
    for v in models_data.values():
        if isinstance(v, str):
            active_models.add(v)
        elif isinstance(v, list):
            for item in v:
                if isinstance(item, str):
                    active_models.add(item)

    content = audit_doc.read_text()
    # Find --model <name>
    model_flags = re.findall(r"--model\s+([a-zA-Z0-9_\-\.]+)", content)
    assert model_flags, "Expected to find --model flags in alpaca-audit.md"

    invalid_models = [m for m in model_flags if m not in active_models]
    assert not invalid_models, f"alpaca-audit.md references inactive models: {invalid_models}"
