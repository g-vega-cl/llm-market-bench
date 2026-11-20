---
tags: [auto-wiki, documentation, git, staging, automation]
category: entity
---

# Auto-Wiki

`apps/engine/auto_wiki.py` (invoked by `scripts/auto-wiki.sh`) generates and updates wiki documentation from staged git diffs. It runs as a blocking pre-commit step: if documentation generation fails, the commit is blocked.

## Staging Contract

The script tracks exactly which files it writes and re-stages only those files, avoiding accidental inclusion of unrelated concurrent wiki edits.

- `scripts/auto-wiki.sh` creates a temp `WRITTEN_LIST` file and passes `--written-files-out "$WRITTEN_LIST"` to `auto_wiki.py`.
- `auto_wiki.py` records every page it creates/updates/deletes into that list.
- After generation, the shell script re-stages only the listed files (`git add -- "$file"`), never sweeping the whole `wiki/` tree.
- If the "How It Works" page is recompiled (`apps/engine/scripts/compile_how_it_works.py`), the generated `apps/web/src/config/how-it-works.json` is appended to the written list on success.

This prevents a commit from capturing unrelated wiki edits made concurrently in the working tree.

## Code Reference Normalization

`auto_wiki.py::normalize_code_references` rewrites code references in generated pages so paths are relative to the repository root. Engine script references like `apps/engine/scripts/update_prices.py` are expanded to `apps/engine/scripts/update_prices.py`, while non-engine paths (e.g. `scripts/auto-wiki.sh`) are left intact. `write_new_page` applies this normalization before writing.

## Related

- [[concepts/wiki-synchronization]] — keeping wiki pages in sync with code
- [[entities/wiki-linter]] — structural lint on commits
- [[concepts/code-reference-validation]] — validating code references in docs
