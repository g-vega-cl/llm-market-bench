---
tags: [git, history, export, documentation]
category: entity
---

# Git History Export

A post-commit and post-merge automation that exports the full Git commit history into structured Markdown files for search and archival purposes. Implemented in `apps/engine/export_git_history.py`.

## How It Works

1. **Extraction**: Runs `git log --reverse --name-status` to capture every commit with hash, date, author, subject, body, and changed files
2. **Grouping**: Commits are grouped by `YYYY-MM` and written to `git-history/YYYY-MM.md` files
3. **Formatting**: Each file uses YAML frontmatter (`category: history`) and renders commits as level-2 headings with metadata, body, and file change lists
4. **Indexing**: Registers the `git-history/` directory as a QMD collection and re-embeds after each export

## Automation

- **Post-commit (background)**: `.husky/post-commit` launches the export detached so the commit returns immediately:
  ```sh
  nohup flock -n /tmp/llm-market-bench-git-history.lock \
    "$REPO_ROOT/apps/engine/.venv/bin/python3" "$REPO_ROOT/apps/engine/export_git_history.py" \
    </dev/null > /tmp/llm-market-bench-git-history.log 2>&1 &
  ```
  `flock -n` makes a second concurrent export a no-op instead of racing the first (rapid successive commits therefore produce one export, not a pile-up), stdin is detached, and all output goes to `/tmp/llm-market-bench-git-history.log` rather than the terminal. Because the hook no longer blocks, a slow export can never delay or fail a commit.
- **Post-merge**: `.husky/post-merge` regenerates history after pulls/merges
- **Gitignore**: `git-history/` is automatically added to `.gitignore` as a generated cache

## Related

- [[entities/wiki-linter]]
- [[concepts/project-linting]]
