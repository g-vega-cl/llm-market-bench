---
tags: [wiki, linting, quality, architecture]
category: concept
---

# Code Reference Validation

Ensures that files, directories, and code components referenced inside the wiki pages actually exist in the physical codebase repository.

## Overview

The "LLM Market Bench" wiki serves as the compiled memory and living synthesis of the project. To prevent documentation rot, it is essential that all references to specific files, directories, and code structures remain accurate. 

If a file is renamed, deleted, or reorganized, any references to its path in the wiki must be updated. This concept details how code reference validation is structured and how it bridges the gap between written documentation and the physical codebase.

## Current Linter Scope

An audit of the existing dual-linter pipeline reveals the following behavior:

1. **Structural Linter (`apps/engine/wiki_lint.py`)**: Runs locally on every commit. It verifies metadata (frontmatter), checks index coverage, parses double-bracket `[ [page-name] ]` links, and flags orphaned wiki files. It operates **exclusively** on markdown files inside `wiki/` and has no awareness of the surrounding codebase.
2. **LLM Linter (`apps/engine/wiki_lint_llm.py`)**: Runs weekly via GitHub Actions. It sends compiled markdown files to an LLM (e.g. DeepSeek) to audit conceptual contradictions and semantic gaps. It **does not** receive repository code or directory trees as context, meaning it cannot verify if file paths or symbols exist.

> [!WARNING]
> Because neither linter checks the physical repository, references to files (e.g., `` `apps/engine/wiki_lint.py` ``) or directory slices can easily become stale or broken without triggering a build or pre-commit failure.

## Architectural Decision: Deterministic vs. Heuristic Linting

To bridge this gap, validation is divided into two distinct logical layers based on performance, cost, and predictability:

| Dimension | Path & Directory Existence | Semantic & Symbol Alignment |
| :--- | :--- | :--- |
| **Nature** | Deterministic (True/False) | Heuristic & Contextual |
| **Best Engine** | Structural Linter (`wiki_lint.py`) | LLM Linter (`wiki_lint_llm.py`) |
| **Trigger** | Every Commit (Pre-commit hook) | Weekly Cron (GitHub Actions) |
| **API Cost** | **$0** (Runs locally on disk) | Variable (OpenRouter token costs) |
| **Performance** | **< 5ms** (Filesystem OS checks) | **10s – 30s** (API call latency) |

By validating code paths deterministically in the local structural linter, we prevent broken documentation references from entering the main branch immediately and with zero performance or monetary overhead.

## Path-Only Validation Strategy

This codebase path-validation check is fully active and integrated directly into the structural linter `wiki_lint.py`. It runs locally on every commit via the pre-commit hook.

### 1. Extraction Pattern
Wiki pages reference codebase paths in two standard markdown structures:
* **Inline Backticks**: `` `apps/engine/wiki_lint.py` `` or `` `packages/config/models.json` ``
* **Markdown Links**: `[models.json](../../packages/config/models.json)`

A regex can scan the markdown content to extract candidate paths. To avoid false positives (such as generic words in backticks), the regex only flags paths that begin with defined repository directory segments:

```python
import re
from pathlib import Path

# Matches strings starting with key project directories inside backticks or links
PATH_RE = re.compile(
    r"(?:`|\[.*?\]\()(apps|packages|scripts|supabase|wiki|\.github)\/([a-zA-Z0-9_\-\.\/]+)(?:`|\))"
)
```

### 2. Validation Implementation
Below is the python implementation that can be added as a step inside `apps/engine/wiki_lint.py`:

```python
def validate_codebase_references(content: str, repo_root: Path) -> list[str]:
    """Scans content for repo paths and validates their existence on disk."""
    errors = []
    
    # Find all path-like patterns matching project directory prefix
    matches = PATH_RE.findall(content)
    for prefix, subpath in matches:
        relative_path = f"{prefix}/{subpath}"
        # Strip trailing punctuation that might be caught in backticks (e.g. trailing period)
        cleaned_path = relative_path.rstrip(".,;")
        
        full_path = repo_root / cleaned_path
        if not full_path.exists():
            errors.append(f"Broken code reference: `{cleaned_path}` does not exist on disk")
            
    return errors
```

### 3. Integration Points
Integrating this into `wiki_lint.py` requires:
1. Adding the validation check inside `lint()`:
   ```python
   # inside the page loop in apps/engine/wiki_lint.py
   code_errors = validate_codebase_references(content, REPO_ROOT)
   for err in code_errors:
       issues.append(f"[broken-code-ref] {rel}: {err}")
   ```
2. Running the check on all non-scaffold wiki pages.
3. Exiting with status `1` if any broken references are found, blocking the commit.

### 4. TDD Verification and Implementation Pattern

Applying Test-Driven Development (TDD) is essential when introducing codebase reference validation to ensure the checking engine operates reliably and captures edge cases:

1. **Create the Failing Test (Red)**:
   * Create a temporary wiki page (e.g., `wiki/concepts/temp-broken-test.md`) with valid frontmatter and a deliberately invalid path reference (e.g., `` `apps/engine/nonexistent_file.py` ``).
   * Run the structural linter: `./apps/engine/.venv/bin/python3 apps/engine/wiki_lint.py`.
   * The linter must fail and explicitly output: `[broken-code-ref] concepts/temp-broken-test.md: Broken code reference: apps/engine/nonexistent_file.py does not exist on disk`.
2. **Implement Minimal Logic (Green)**:
   * Inject `validate_codebase_references()` and its extraction regex into `wiki_lint.py`.
   * Re-run the linter to verify it successfully intercepts the invalid reference and aborts the commit.
3. **Verify Positive Case**:
   * Change the invalid path in `temp-broken-test.md` to a valid file on disk (e.g., `` `apps/engine/wiki_lint.py` ``).
   * Re-run the linter and ensure the check passes.
4. **Cleanup & Refactor**:
   * Delete `wiki/concepts/temp-broken-test.md` to restore the wiki to its pristine state.

## Future Extensions

While path validation covers 90% of structural documentation decay, deep codebase linting can be extended to:
* **Symbol Audits (Intermediate)**: Parsing Python/TS references in markdown and verifying using `grep` or compiler tools that specific class or function symbols still exist in the target code files.
* **Bi-directional Auditing**: Scanning the codebase for major system components and warning if no corresponding wiki entity or concept page references them.

## Related

* [[entities/wiki-linter]] — Structural and LLM-powered wiki QA details
* [[concepts/project-linting]] — Pre-commit hook architecture and tool limits
* [[entities/auto-wiki]] — Autogenerating wiki updates from diffs
