"""Hermetic tests for the unified .agents/skills/ spine and Pi/Hermes parity."""

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
SKILLS_DIR = REPO_ROOT / ".agents" / "skills"
PI_SKILLS_DIR = REPO_ROOT / ".pi" / "skills"

EXPECTED_SKILLS = (
    "grill-me",
    "wayfinder",
    "implement",
    "qa",
    "verify",
    "ship",
    "qmd-wiki",
    "last30days",
    "unslop",
    "code-hotspots",
    "creative-ideation",
    "gemini-api-dev",
)

MANUAL_ONLY_SKILLS = ("grill-me", "wayfinder", "ship")


def _parse_frontmatter(skill_md: Path) -> dict:
    raw = skill_md.read_text()
    assert raw.startswith("---\n"), f"{skill_md} missing YAML frontmatter"
    end = raw.find("\n---", 4)
    assert end != -1, f"{skill_md} has unclosed YAML frontmatter"
    data = yaml.safe_load(raw[4:end])
    assert isinstance(data, dict)
    return data


def test_all_expected_skills_exist_in_agents_skills():
    """Every core skill in the spine must live canonically under .agents/skills/<name>/SKILL.md."""
    for name in EXPECTED_SKILLS:
        skill_md = SKILLS_DIR / name / "SKILL.md"
        assert skill_md.is_file(), f"Missing canonical skill: .agents/skills/{name}/SKILL.md"
        fm = _parse_frontmatter(skill_md)
        assert fm.get("name") == name, f"Skill frontmatter name mismatch in {skill_md}: {fm.get('name')}"
        assert fm.get("description"), f"Skill missing description in {skill_md}"
        assert len(skill_md.read_text().splitlines()) < 500, f"Skill body exceeds 500-line ceiling: {skill_md}"

    for manual_name in MANUAL_ONLY_SKILLS:
        fm = _parse_frontmatter(SKILLS_DIR / manual_name / "SKILL.md")
        assert fm.get("disable-model-invocation") is True, f"{manual_name} must set disable-model-invocation: true"


def test_pi_skills_symlinked_to_canonical_agents_skills():
    """Pi must see the identical skill spine via .pi/skills/<name> symlinks."""
    for name in EXPECTED_SKILLS:
        pi_entry = PI_SKILLS_DIR / name
        assert pi_entry.is_symlink(), f".pi/skills/{name} must be a symlink to ../../.agents/skills/{name}"
        assert (pi_entry / "SKILL.md").resolve() == (SKILLS_DIR / name / "SKILL.md").resolve()


def test_implement_qa_ship_and_cold_reviewer_contracts():
    """Verify key procedural guardrails in implement, qa, ship, and verify cold-review profiles."""
    implement_text = (SKILLS_DIR / "implement" / "SKILL.md").read_text()
    assert ".worktrees/" in implement_text
    assert "SPEC.md" in implement_text
    assert "Red" in implement_text and "Green" in implement_text

    qa_text = (SKILLS_DIR / "qa" / "SKILL.md").read_text()
    assert "PRODUCT.md" in qa_text
    assert "design-spec.md" in qa_text
    assert "360" in qa_text

    ship_text = (SKILLS_DIR / "ship" / "SKILL.md").read_text()
    assert "deploy_secondary.sh" in ship_text
    assert "PGRST205" in ship_text
    assert "worktree" in ship_text

    reviewer_cfg = REPO_ROOT / ".agents" / "reviewer-profiles.json"
    assert reviewer_cfg.is_file(), "Expected .agents/reviewer-profiles.json for cross-model cold review profiles"
