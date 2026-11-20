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


def test_agent_rule_files_under_truncation_limit():
    """Ensure GEMINI.md, AGENTS.md, and .agents/rules/*.md stay under the 20KB budget (24KB hard cap)."""
    max_rule_bytes = 20_000
    rule_files = [
        REPO_ROOT / "GEMINI.md",
        REPO_ROOT / "AGENTS.md",
        *sorted((REPO_ROOT / ".agents" / "rules").glob("*.md")),
    ]

    oversized = []
    for path in rule_files:
        assert path.is_file(), f"Expected rule file {path} to exist"
        size = path.stat().st_size
        if size > max_rule_bytes:
            oversized.append((str(path.relative_to(REPO_ROOT)), size))

    assert not oversized, (
        f"Agent rule files exceed {max_rule_bytes} byte budget (risking 24KB runtime truncation): {oversized}"
    )

    prose_boxel_re = re.compile(r"(?<![a-zA-Z0-9_-])boxel(?![a-zA-Z0-9_-])", re.IGNORECASE)
    gemini_text = (REPO_ROOT / "GEMINI.md").read_text()
    assert "### QMD Search" in gemini_text, "GEMINI.md must retain QMD Search documentation"
    assert not prose_boxel_re.search(gemini_text), "Use 'Voxel' instead of 'Boxel' in GEMINI.md prose"

    design_spec_text = (REPO_ROOT / ".agents" / "rules" / "design-spec.md").read_text()
    assert not prose_boxel_re.search(design_spec_text), "Use 'Voxel' instead of 'Boxel' in design-spec.md prose"

    offending_wiki = []
    for wiki_md in WIKI_DIR.rglob("*.md"):
        if prose_boxel_re.search(wiki_md.read_text(errors="ignore")):
            offending_wiki.append(str(wiki_md.relative_to(REPO_ROOT)))
    assert not offending_wiki, f"Use 'Voxel' instead of 'Boxel' in wiki prose: {offending_wiki}"


def test_validate_agent_rules_budget_flags_oversized(tmp_path):
    """Ensure validate_agent_rules_budget catches rule files exceeding 20KB."""
    from wiki_lint import validate_agent_rules_budget

    assert validate_agent_rules_budget(REPO_ROOT) == []

    fake_gemini = tmp_path / "GEMINI.md"
    fake_gemini.write_text("x" * 20_500)
    errors = validate_agent_rules_budget(tmp_path)
    assert len(errors) == 1
    assert "GEMINI.md" in errors[0]


def test_core_web_vitals_documented():
    """Ensure Core Web Vitals (web.dev/articles/vitals) and 3-tier JS loading are codified in rules and wiki."""
    gemini_text = (REPO_ROOT / "GEMINI.md").read_text()
    for token in ("Core Web Vitals", "LCP", "INP", "CLS", "2.5", "200", "0.1", "[[concepts/core-web-vitals]]"):
        assert token in gemini_text, f"GEMINI.md must document Core Web Vitals token: {token}"

    design_spec_text = (REPO_ROOT / ".agents" / "rules" / "design-spec.md").read_text()
    assert "[[concepts/core-web-vitals]]" in design_spec_text, (
        ".agents/rules/design-spec.md must cross-reference [[concepts/core-web-vitals]]"
    )

    cwv_page = WIKI_DIR / "concepts" / "core-web-vitals.md"
    assert cwv_page.is_file(), "wiki/concepts/core-web-vitals.md must exist"
    cwv_text = cwv_page.read_text()
    for token in (
        "https://web.dev/articles/vitals",
        "LCP",
        "INP",
        "CLS",
        "75th percentile",
        "Tier 1",
        "Tier 2",
        "Tier 3",
    ):
        assert token in cwv_text, f"wiki/concepts/core-web-vitals.md missing required section/token: {token}"

    index_text = (WIKI_DIR / "index.md").read_text()
    assert "[[concepts/core-web-vitals]]" in index_text, "wiki/index.md must index [[concepts/core-web-vitals]]"
