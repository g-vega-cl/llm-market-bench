---
tags: [git, history, documentation, audit]
category: concept
---

# Git History as the Chronological Record

The project uses Git commit history — not a wiki log file — as the authoritative chronological record of all changes. This shift eliminates the maintenance burden of a separate append-only log while improving searchability and auditability.

## Architecture

- **Commit Message Standards**: All commits follow Conventional Commits format, enforced by `commit_msg_lint.py` via a Husky `commit-msg` hook. Types like `feat`, `fix`, `perf`, and `refactor` require descriptive bodies.
- **Automated Export**: `export_git_history.py` generates structured Markdown files in `git-history/` grouped by month, with full commit metadata and file change lists.
- **QMD Integration**: The exported history is indexed as a QMD collection, making the entire project history searchable via `qmd search` or `qmd query`.

## Migration from Wiki Log

The previous log.md and monthly log archive system under the wiki folder has been fully removed:
- wiki log.md — deleted
- wiki log monthly archives — deleted
- wiki_log_rotate.py — deleted
- gitattributes union merge rules for log files — removed

Git history is now the single source of truth for what changed and when.

## Related

- [[concepts/visual-planning]]
- [[concepts/output-normalization]]
