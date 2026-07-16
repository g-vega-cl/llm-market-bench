#!/usr/bin/env python3
import re
import sys

# Conventional commit types
VALID_TYPES = {"feat", "fix", "perf", "docs", "doc", "refactor", "style", "test", "build", "ci", "chore", "revert"}

# Subject regex: type(optional-scope): description
# Allows optional '!' for breaking changes
CONVENTIONAL_REGEX = re.compile(
    r"^(?P<type>[a-z]+)(?:\((?P<scope>[a-z0-9_\-\/ ]+)\))?(?P<breaking>!)?:\s+(?P<subject>.+)$"
)


def validate_commit_msg(msg_content: str) -> tuple[bool, list[str]]:
    errors = []
    lines = [line.rstrip() for line in msg_content.splitlines()]

    # Strip any comment lines (starting with #) as git removes them
    lines = [line for line in lines if not line.startswith("#")]

    # Strip trailing empty lines
    while lines and not lines[-1]:
        lines.pop()

    if not lines or not any(line.strip() for line in lines):
        return False, ["Commit message is empty."]

    subject_line = lines[0]

    # Whitelist auto-generated merge and revert commits
    if subject_line.startswith("Merge ") or subject_line.startswith("Revert "):
        return True, []

    match = CONVENTIONAL_REGEX.match(subject_line)

    if not match:
        errors.append(
            "Subject line must follow Conventional Commits format: '<type>(scope): <description>' or '<type>: <description>'"
        )
        return False, errors

    commit_type = match.group("type")
    subject = match.group("subject")

    if commit_type not in VALID_TYPES:
        errors.append(f"Invalid commit type '{commit_type}'. Must be one of: {', '.join(sorted(VALID_TYPES))}")

    if len(subject) < 5:
        errors.append("Subject description is too short (minimum 5 characters).")

    if len(subject_line) > 100:
        errors.append(f"Subject line is too long ({len(subject_line)} chars). Keep it under 100 characters.")

    # Validate body if present or required
    body_required = commit_type in {"feat", "fix", "perf", "refactor"}
    has_body = len(lines) > 1 and any(line.strip() for line in lines[1:])

    if has_body:
        # Line 1 (the line after the subject) must be empty
        if len(lines) > 1 and lines[1].strip() != "":
            errors.append("Subject line and body must be separated by a blank line.")

        # Validate body length
        body_content = "\n".join(lines[2:]).strip()
        if len(body_content) < 15:
            errors.append("Commit body is too short (minimum 15 characters of description required).")
    elif body_required:
        errors.append(f"Commit type '{commit_type}' requires a body explaining the context and changes.")

    return len(errors) == 0, errors


def main():
    if len(sys.argv) < 2:
        print("Usage: commit_msg_lint.py <path-to-commit-message-file>", file=sys.stderr)
        sys.exit(1)

    commit_msg_filepath = sys.argv[1]
    try:
        with open(commit_msg_filepath, encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Error: Commit message file not found at {commit_msg_filepath}", file=sys.stderr)
        sys.exit(1)

    is_valid, errors = validate_commit_msg(content)
    if not is_valid:
        print("❌ ERROR: Commit message validation failed!", file=sys.stderr)
        print("\nViolations:", file=sys.stderr)
        for err in errors:
            print(f" - {err}", file=sys.stderr)
        print("\nYour original commit message:", file=sys.stderr)
        print("-" * 40, file=sys.stderr)
        print(content.strip(), file=sys.stderr)
        print("-" * 40, file=sys.stderr)
        print("\nExample of a valid commit message:", file=sys.stderr)
        print("  feat(engine): support parallel ingestion of newsletters\n", file=sys.stderr)
        print("  - Use asyncio.gather to fetch daily emails concurrently", file=sys.stderr)
        print("  - Add unit tests for batch fetching latency", file=sys.stderr)
        sys.exit(1)

    print("✅ Commit message validation passed.")
    sys.exit(0)


if __name__ == "__main__":
    main()
