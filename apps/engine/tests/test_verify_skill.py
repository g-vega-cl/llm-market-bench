"""Tests verifying that the verify skill and its runner script actively update the wiki.

Checks that verify.sh executes auto-indexing, hotspots wiki refresh, and QMD embeddings,
and that SKILL.md and wiki/entities/verify-skill.md mandate wiki synchronization.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
VERIFY_SCRIPT = REPO_ROOT / ".agents" / "skills" / "verify" / "scripts" / "verify.sh"
VERIFY_SKILL_MD = REPO_ROOT / ".agents" / "skills" / "verify" / "SKILL.md"
VERIFY_ENTITY_MD = REPO_ROOT / "wiki" / "entities" / "verify-skill.md"


def test_verify_script_updates_wiki():
    assert VERIFY_SCRIPT.exists(), "verify.sh must exist"
    content = VERIFY_SCRIPT.read_text()

    # Must auto-index new wiki pages
    assert "wiki_lint.py --fix" in content, "verify.sh must run wiki_lint.py with --fix"

    # Must refresh hotspots wiki page
    assert "--write-wiki" in content, "verify.sh must run hotspots.py with --write-wiki"

    # Must refresh QMD vector embeddings if qmd is available
    assert "qmd update" in content, "verify.sh must run qmd update"
    assert "qmd embed" in content, "verify.sh must run qmd embed"


def test_verify_skill_md_mandates_wiki_updates():
    assert VERIFY_SKILL_MD.exists(), "SKILL.md must exist"
    content = VERIFY_SKILL_MD.read_text()

    # Must mandate updating wiki when code/calculations change
    assert "Wiki and documentation synchronization" in content or "Wiki and documentation integrity" in content
    assert "hotspots.py" in content and "--write-wiki" in content
    assert "qmd update && qmd embed" in content or "qmd embed" in content


def test_verify_entity_md_documents_wiki_update():
    assert VERIFY_ENTITY_MD.exists(), "wiki/entities/verify-skill.md must exist"
    content = VERIFY_ENTITY_MD.read_text()

    assert "--write-wiki" in content or "hotspots" in content
    assert "qmd" in content or "auto-index" in content


def test_verify_skill_mandates_typecheck_and_db_parity():
    """Verify that SKILL.md and wiki entity explicitly mandate TypeScript typecheck and self-hosted DB schema parity."""
    assert VERIFY_SKILL_MD.exists(), "SKILL.md must exist"
    skill_content = VERIFY_SKILL_MD.read_text()
    assert "typecheck" in skill_content, "SKILL.md must mandate pnpm run typecheck"
    assert "PostgreSQL" in skill_content or "PostgREST" in skill_content or "schema parity" in skill_content, (
        "SKILL.md must mandate self-hosted DB schema parity"
    )
    assert "supabase db push" not in skill_content, "SKILL.md must not contain stale supabase db push reference"

    assert VERIFY_ENTITY_MD.exists(), "wiki/entities/verify-skill.md must exist"
    entity_content = VERIFY_ENTITY_MD.read_text()
    assert "typecheck" in entity_content, "wiki/entities/verify-skill.md must document typecheck mandate"
    assert "PostgreSQL" in entity_content or "PostgREST" in entity_content or "schema parity" in entity_content, (
        "wiki/entities/verify-skill.md must document self-hosted DB schema parity"
    )
    assert "supabase db push" not in entity_content, (
        "wiki/entities/verify-skill.md must not contain stale supabase db push reference"
    )


def test_verify_script_checks_migration_integrity():
    """Verify that verify.sh executes an automated migration integrity test."""
    assert VERIFY_SCRIPT.exists(), "verify.sh must exist"
    content = VERIFY_SCRIPT.read_text()
    assert "test_migration_grants.py" in content, "verify.sh must inspect migrations using test_migration_grants.py"
    assert "supabase migration list" not in content, "verify.sh must not call obsolete supabase migration list"


def test_verify_skill_mandates_tier_7_wiki_docs():
    """Verify that SKILL.md and wiki entity explicitly mandate Tier 7 for Wiki and documentation synchronization."""
    assert VERIFY_SKILL_MD.exists(), "SKILL.md must exist"
    skill_content = VERIFY_SKILL_MD.read_text()
    assert "Tier 7" in skill_content, "SKILL.md must have a dedicated Tier 7"
    assert "seven tiers" in skill_content.lower() or "7 tiers" in skill_content.lower()

    assert VERIFY_ENTITY_MD.exists(), "wiki/entities/verify-skill.md must exist"
    entity_content = VERIFY_ENTITY_MD.read_text()
    assert "Tier 7" in entity_content or "seven tiers" in entity_content.lower()


def test_verify_script_checks_strict_wiki_lint():
    """Verify that verify.sh executes strict wiki_lint (ensuring config-parity and integrity)."""
    assert VERIFY_SCRIPT.exists(), "verify.sh must exist"
    content = VERIFY_SCRIPT.read_text()
    # Must run wiki_lint.py as a strict check (in addition to --fix)
    lines = [line.strip() for line in content.splitlines()]
    has_strict_lint = any("apps/engine/wiki_lint.py" in line and "--fix" not in line for line in lines)
    assert has_strict_lint, "verify.sh must execute strict wiki_lint.py to enforce config parity"


def test_verify_skill_mandates_config_parity_and_preservation():
    """Verify that SKILL.md and wiki entity explicitly mandate config-parity and tool preservation."""
    assert VERIFY_SKILL_MD.exists(), "SKILL.md must exist"
    skill_content = VERIFY_SKILL_MD.read_text()
    assert "config parity" in skill_content.lower()
    assert "tools.json" in skill_content
    assert "auto_wiki" in skill_content or "preservation" in skill_content.lower()

    assert VERIFY_ENTITY_MD.exists(), "wiki/entities/verify-skill.md must exist"
    entity_content = VERIFY_ENTITY_MD.read_text()
    assert "config parity" in entity_content.lower() or "tools.json" in entity_content


def test_verify_script_supports_sequential():
    """Verify that verify.sh and SKILL.md document and support sequential execution with 1 worker."""
    assert VERIFY_SCRIPT.exists(), "verify.sh must exist"
    content = VERIFY_SCRIPT.read_text()
    assert "--sequential" in content
    assert "pytest --cov=. --cov-config=.coveragerc" in content
    assert "--maxWorkers=1" in content

    skill_content = VERIFY_SKILL_MD.read_text()
    assert "--sequential" in skill_content

    entity_content = VERIFY_ENTITY_MD.read_text()
    assert "--sequential" in entity_content
