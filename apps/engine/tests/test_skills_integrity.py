from pathlib import Path

import yaml


def test_skills_frontmatter_and_structure():
    repo_root = Path(__file__).resolve().parents[3]
    skills_dir = repo_root / ".agents" / "skills"
    assert skills_dir.exists(), ".agents/skills directory must exist"

    for skill_path in skills_dir.iterdir():
        if not skill_path.is_dir():
            continue

        skill_md = skill_path / "SKILL.md"
        assert skill_md.exists(), f"Skill {skill_path.name} is missing SKILL.md"

        content = skill_md.read_text(encoding="utf-8")
        assert content.startswith("---"), f"{skill_md} must start with YAML frontmatter delimiter '---'"

        parts = content.split("---", 2)
        assert len(parts) >= 3, f"{skill_md} must have closed YAML frontmatter"

        frontmatter = yaml.safe_load(parts[1])
        assert isinstance(frontmatter, dict), f"Frontmatter in {skill_md} must parse to a dict"
        assert "name" in frontmatter, f"{skill_md} frontmatter missing 'name'"
        assert frontmatter["name"] == skill_path.name, (
            f"Skill name '{frontmatter['name']}' must match directory '{skill_path.name}'"
        )
        assert "description" in frontmatter, f"{skill_md} frontmatter missing 'description'"
        assert len(frontmatter["description"].strip()) > 10, f"{skill_md} description is too short"
