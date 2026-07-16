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

- **Post-commit**: `.husky/post-commit` regenerates history after every commit
- **Post-merge**: `.husky/post-merge` regenerates history after pulls/merges
- **Gitignore**: `git-history/` is automatically added to `.gitignore` as a generated cache

## Related

- [[entities/wiki-linter]]
- [[concepts/project-linting]]
