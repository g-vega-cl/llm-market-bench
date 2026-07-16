#!/usr/bin/env python3
import re
import subprocess
from pathlib import Path

# Mapping of git change status characters to readable labels
STATUS_MAP = {
    "A": "Added",
    "M": "Modified",
    "D": "Deleted",
    "R": "Renamed",
    "C": "Copied",
    "T": "Type Changed",
}


def ensure_gitignore(target_gitignore=None):
    """Ensure git-history/ is in the root .gitignore."""
    gitignore_path = (
        Path(target_gitignore) if target_gitignore else Path(__file__).resolve().parent.parent.parent / ".gitignore"
    )
    if not gitignore_path.exists():
        return

    content = gitignore_path.read_text(encoding="utf-8")
    lines = content.splitlines()

    # Check if git-history/ is already present
    if not any(re.match(r"^/?git-history/?$", line.strip()) for line in lines):
        print("[git-history] Adding git-history/ to .gitignore...")
        with open(gitignore_path, "a", encoding="utf-8") as f:
            f.write("\n# Git History Cache\ngit-history/\n")


def run_cmd(command: str, shell: bool = True) -> str:
    """Run a shell command and return its stdout, or empty string on error."""
    try:
        res = subprocess.run(command, shell=shell, capture_output=True, text=True, check=True)
        return res.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"[git-history] Command failed: {command}\nError: {e.stderr}", flush=True)
        return ""


def export_git_history(target_dir=None):
    repo_root = Path(__file__).resolve().parent.parent.parent
    history_dir = Path(target_dir) if target_dir else repo_root / "git-history"
    history_dir.mkdir(exist_ok=True)

    print("[git-history] Fetching git logs...", flush=True)
    # Fetch all commits with date, author, subject, body, and name status
    git_log_cmd = (
        "git log --reverse --name-status --date=short "
        '--pretty=format:"__GIT_HISTORY_COMMIT_START__|%H|%ad|%an|%s%n%b%n__GIT_HISTORY_COMMIT_FILES__"'
    )

    raw_log = run_cmd(git_log_cmd)
    if not raw_log:
        print("[git-history] No git logs found or git command failed.")
        return

    # Split by commit start marker
    commits_data = raw_log.split("__GIT_HISTORY_COMMIT_START__|")

    # Group commits by YYYY-MM
    commits_by_month = {}

    for block in commits_data:
        if not block.strip():
            continue

        lines = block.splitlines()
        if not lines:
            continue

        # Parse the header line: hash|date|author|subject
        header_parts = lines[0].split("|", 3)
        if len(header_parts) < 4:
            continue

        commit_hash, date_str, author, subject = header_parts
        # Standardize subject
        subject = subject.strip()

        # Parse body and files
        body_lines = []
        files_lines = []
        in_files_section = False

        for line in lines[1:]:
            if line.strip() == "__GIT_HISTORY_COMMIT_FILES__":
                in_files_section = True
                continue

            if in_files_section:
                if line.strip():
                    files_lines.append(line.strip())
            else:
                body_lines.append(line)

        # Clean body
        body = "\n".join(body_lines).strip()

        # Parse files changed list
        files_changed = []
        for file_line in files_lines:
            # File status is usually: M\tfilename or A\tfilename
            parts = file_line.split(None, 1)
            if len(parts) == 2:
                status_code, filename = parts
                status = STATUS_MAP.get(status_code[0], status_code)
                files_changed.append(f"- `{filename}` ({status})")
            else:
                files_changed.append(f"- `{file_line}`")

        # Resolve Year-Month
        # Date is formatted as YYYY-MM-DD
        year_month = date_str[:7]  # YYYY-MM

        commit_entry = {
            "hash": commit_hash,
            "date": date_str,
            "author": author,
            "subject": subject,
            "body": body,
            "files": files_changed,
        }

        commits_by_month.setdefault(year_month, []).append(commit_entry)

    # Write monthly files
    print(f"[git-history] Writing history files to {history_dir}...", flush=True)
    for year_month, entries in commits_by_month.items():
        file_path = history_dir / f"{year_month}.md"

        # Sort commits in descending order (newest first) for easier reading
        entries_sorted = sorted(entries, key=lambda x: x["date"], reverse=True)

        # Formulate Month Name
        # e.g., 2026-07 -> July 2026
        from datetime import datetime

        try:
            dt = datetime.strptime(year_month, "%Y-%m")
            title_date = dt.strftime("%B %Y")
        except ValueError:
            title_date = year_month

        md_content = []
        md_content.append("---")
        md_content.append("tags: [git-history, change-log]")
        md_content.append("category: history")
        md_content.append("---")
        md_content.append("")
        md_content.append(f"# Git History — {title_date}")
        md_content.append("")

        for entry in entries_sorted:
            md_content.append(f"## [{entry['date']}] Commit: {entry['hash'][:12]}")
            md_content.append(f"**Author:** {entry['author']}  ")
            md_content.append(f"**Subject:** {entry['subject']}  ")
            md_content.append("")

            if entry["body"]:
                md_content.append("**Body:**")
                md_content.append(entry["body"])
                md_content.append("")

            if entry["files"]:
                md_content.append("**Files Changed:**")
                md_content.extend(entry["files"])
                md_content.append("")

            md_content.append("---")
            md_content.append("")

        file_path.write_text("\n".join(md_content), encoding="utf-8")

    print(f"[git-history] Exported {len(commits_by_month)} monthly log files.", flush=True)


def update_qmd_index():
    """Register collection and run QMD updates using system NVM/Node 24 config."""
    print("[git-history] Checking QMD status...", flush=True)
    nvm_prefix = 'export NVM_DIR="$HOME/.nvm" && . "$NVM_DIR/nvm.sh" && nvm use 24'

    # Check if QMD is installed
    check_qmd = run_cmd(f"{nvm_prefix} && which qmd")
    if not check_qmd:
        print("[git-history] WARNING: QMD CLI is not installed on this system. Skipping index updates.", flush=True)
        return

    # Check registered collections
    collections = run_cmd(f"{nvm_prefix} && qmd collection list")

    # Check if git-history is already registered
    if "git-history" not in collections:
        print("[git-history] Registering git-history collection with QMD...", flush=True)
        run_cmd(f"{nvm_prefix} && qmd collection add git-history/ --name git-history")

    print("[git-history] Updating QMD index...", flush=True)
    run_cmd(f"{nvm_prefix} && qmd update")
    run_cmd(f"{nvm_prefix} && qmd embed")
    print("[git-history] QMD indexing completed successfully.", flush=True)


if __name__ == "__main__":
    ensure_gitignore()
    export_git_history()
    update_qmd_index()
