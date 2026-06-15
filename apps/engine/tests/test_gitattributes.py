from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def test_gitattributes_union_merge():
    gitattributes_path = REPO_ROOT / ".gitattributes"
    assert gitattributes_path.exists(), ".gitattributes file does not exist in the root directory"

    content = gitattributes_path.read_text()
    lines = [line.strip() for line in content.splitlines() if line.strip() and not line.strip().startswith("#")]

    expected_rules = {
        "wiki/log.md merge=union",
        "wiki/log/*.md merge=union",
    }

    for rule in expected_rules:
        assert rule in lines, f"Expected rule '{rule}' not found in .gitattributes"
