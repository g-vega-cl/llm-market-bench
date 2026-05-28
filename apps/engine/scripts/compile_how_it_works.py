#!/usr/bin/env python3
import json
import re
import subprocess
import sys
from pathlib import Path


def parse_pipeline_markdown(md_content: str) -> list[dict]:
    # Split content by '## Phase'
    blocks = re.split(r"^## Phase\s+", md_content, flags=re.MULTILINE)

    phases = []

    # The first block is frontmatter/intro
    for block in blocks[1:]:
        # Parse phase number and title (e.g. "1: Ingestion & Normalization\n...")
        header_match = re.match(r"^(\d+):\s*(.*?)\n", block)
        if not header_match:
            continue

        phase_num = int(header_match.group(1))
        title = header_match.group(2).strip()

        # Remaining block body
        block_body = block[header_match.end() :]

        # Remove any subsequent non-Phase headings (like "## Related" at the end of the last phase)
        body_parts = re.split(r"^##\s+(?!Phase)", block_body, flags=re.MULTILINE)
        block_body = body_parts[0]

        # Regex search for metadata
        icon_match = re.search(r"^\*\s+\*\*Icon\*\*:\s*(.*?)\s*$", block_body, re.MULTILINE)
        badge_match = re.search(r"^\*\s+\*\*Badge\*\*:\s*(.*?)\s*$", block_body, re.MULTILINE)
        tags_match = re.search(r"^\*\s+\*\*Tags\*\*:\s*\[(.*?)\]\s*$", block_body, re.MULTILINE)

        icon = icon_match.group(1).strip() if icon_match else ""
        badge = badge_match.group(1).strip() if badge_match else ""

        tags = []
        if tags_match and tags_match.group(1).strip():
            tags = [t.strip() for t in tags_match.group(1).split(",")]

        # Clean lines to extract description and bullets
        clean_lines = []
        for line in block_body.splitlines():
            # Skip metadata declaration lines
            if re.match(r"^\*\s+\*\*(Icon|Badge|Tags)\*\*:", line):
                continue
            clean_lines.append(line)

        # Extract bullets (lines starting with * or -)
        bullets = []
        for line in clean_lines:
            line_str = line.strip()
            if line_str.startswith("*") or line_str.startswith("-"):
                # Strip leading bullet marker
                bullet_content = re.sub(r"^[*-]\s+", "", line_str)
                bullets.append(bullet_content)

        # Description is the first non-empty paragraph that isn't a bullet list
        description_lines = []
        for line in clean_lines:
            line_str = line.strip()
            if not line_str:
                if description_lines:
                    break  # End of paragraph
                continue
            if line_str.startswith("*") or line_str.startswith("-"):
                break  # Bullet list starts
            description_lines.append(line_str)

        description = " ".join(description_lines).strip()

        phases.append(
            {
                "phase": phase_num,
                "title": title,
                "badge": badge,
                "description": description,
                "bullets": bullets,
                "tags": tags,
                "icon": icon,
            }
        )

    return phases


def compile_pipeline_to_json(wiki_path: Path, output_path: Path) -> None:
    if not wiki_path.is_file():
        raise FileNotFoundError(f"Wiki pipeline source not found at: {wiki_path}")

    md_content = wiki_path.read_text(encoding="utf-8")
    phases = parse_pipeline_markdown(md_content)

    # Ensure directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write JSON formatted output
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(phases, f, indent=4, ensure_ascii=False)
        f.write("\n")

    # Run biome format on the output file to match style guide
    try:
        subprocess.run(
            ["pnpm", "biome", "format", "--write", str(output_path)],
            check=True,
            capture_output=True,
        )
    except Exception as e:
        # Don't crash if pnpm/biome is missing during python-only test runs, just log warning
        print(
            f"Warning: could not auto-format JSON with Biome: {e}",
            file=sys.stderr,
        )


def main():
    # Resolve project root directories
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir
    while repo_root != repo_root.parent and not (repo_root / ".git").exists():
        repo_root = repo_root.parent

    wiki_path = repo_root / "wiki" / "entities" / "pipeline.md"
    output_path = repo_root / "apps" / "web" / "src" / "config" / "how-it-works.json"

    print(f"Compiling pipeline documentation from {wiki_path.relative_to(repo_root)}...")
    try:
        compile_pipeline_to_json(wiki_path, output_path)
        print(f"Successfully compiled how-it-works.json to {output_path.relative_to(repo_root)} ✓")
    except Exception as e:
        print(f"Error compiling pipeline json: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
