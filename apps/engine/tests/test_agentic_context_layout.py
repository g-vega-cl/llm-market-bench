"""Hermetic contract tests for the 4-layer progressive agent context layout."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_root_agents_md_is_canonical_and_compact():
    """Root AGENTS.md must be canonical, <= 125 lines, < 6KB, with GEMINI.md symlinked to it."""
    agents_md = REPO_ROOT / "AGENTS.md"
    gemini_md = REPO_ROOT / "GEMINI.md"

    assert agents_md.is_file() and not agents_md.is_symlink(), "AGENTS.md must be the canonical regular file"
    assert gemini_md.is_symlink(), "GEMINI.md must be a symlink to AGENTS.md"
    assert gemini_md.resolve() == agents_md.resolve(), "GEMINI.md must resolve to AGENTS.md"

    text = agents_md.read_text()
    line_count = len(text.splitlines())
    byte_count = agents_md.stat().st_size
    assert line_count <= 125, f"AGENTS.md must stay <= 125 lines (got {line_count})"
    assert byte_count < 6_500, f"AGENTS.md must stay < 6.5KB (got {byte_count} bytes)"

    for required in (
        "Plan-Gated",
        "worktree",
        "Minimal-Code Ladder",
        "### QMD Search",
        "Core Web Vitals",
        "LCP",
        "INP",
        "CLS",
        "2.5",
        "200",
        "0.1",
        "[[concepts/core-web-vitals]]",
        "--cov-config=.coveragerc",
        "apps/engine/AGENTS.md",
        "apps/web/AGENTS.md",
        "PRODUCT.md",
        ".agents/rules/design-spec.md",
    ):
        assert required in text, f"AGENTS.md missing required token: {required}"


def test_legacy_harness_clutter_removed():
    """Obsolete or progressive-loading-blocking files must not exist."""
    for legacy_rel in (".hermes.md", ".pi/APPEND_SYSTEM.md", "opencode.json", ".claude", "DESIGN.md"):
        target = REPO_ROOT / legacy_rel
        assert not target.exists() and not target.is_symlink(), f"Legacy file/dir must be removed: {legacy_rel}"


def test_scoped_domain_rules_and_product_md_exist():
    """Progressive domain AGENTS.md files and PRODUCT.md must exist and stay compact."""
    engine_agents = REPO_ROOT / "apps" / "engine" / "AGENTS.md"
    web_agents = REPO_ROOT / "apps" / "web" / "AGENTS.md"
    product_md = REPO_ROOT / "PRODUCT.md"

    for path in (engine_agents, web_agents, product_md):
        assert path.is_file(), f"Expected scoped context file: {path.relative_to(REPO_ROOT)}"
        assert path.stat().st_size < 8_000, f"{path.relative_to(REPO_ROOT)} exceeds 8KB scoped budget"

    assert "receipts" in product_md.read_text().lower(), "PRODUCT.md must preserve the 'show the receipts' positioning"
    assert "PGRST205" in engine_agents.read_text(), "apps/engine/AGENTS.md must document PostgREST replica reload"
    assert "Zero Compute on Frontend" in web_agents.read_text(), "apps/web/AGENTS.md must enforce zero frontend compute"


def test_gitignore_excludes_worktrees():
    """Ensure .gitignore ignores .worktrees/ for isolated task checkouts."""
    gitignore_text = (REPO_ROOT / ".gitignore").read_text()
    assert ".worktrees/" in gitignore_text
