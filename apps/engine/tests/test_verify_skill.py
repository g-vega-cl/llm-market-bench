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


def test_verify_skill_mandates_typecheck_and_supabase_parity():
    """Verify that SKILL.md and wiki entity explicitly mandate TypeScript typecheck and remote Supabase parity."""
    assert VERIFY_SKILL_MD.exists(), "SKILL.md must exist"
    skill_content = VERIFY_SKILL_MD.read_text()
    assert "typecheck" in skill_content, "SKILL.md must mandate pnpm run typecheck"
    assert "supabase db push" in skill_content or "remote Supabase" in skill_content, (
        "SKILL.md must mandate remote Supabase state parity"
    )

    assert VERIFY_ENTITY_MD.exists(), "wiki/entities/verify-skill.md must exist"
    entity_content = VERIFY_ENTITY_MD.read_text()
    assert "typecheck" in entity_content, "wiki/entities/verify-skill.md must document typecheck mandate"
    assert "supabase db push" in entity_content or "remote Supabase" in entity_content, (
        "wiki/entities/verify-skill.md must document remote Supabase state parity"
    )


def test_verify_script_checks_supabase_migration_parity():
    """Verify that verify.sh executes an automated remote Supabase migration parity check."""
    assert VERIFY_SCRIPT.exists(), "verify.sh must exist"
    content = VERIFY_SCRIPT.read_text()
    assert "supabase migration list" in content or "supabase db push" in content, (
        "verify.sh must inspect Supabase migrations for remote parity"
    )
