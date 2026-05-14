---
tags: [biome, linting, scripts, automation]
category: entity
---

# Biome Lint Scripts

Two Python utility scripts that batch-fix common Biome lint violations across the TypeScript/React codebase:

- **`scripts/fix_button_types.py`** — adds `type="button"` to all `<button>` elements lacking a type attribute, fixing the `useButtonType` rule
- **`scripts/fix_svg_titles.py`** — adds `<title>SVG</title>` as the first child of `<svg>` elements without a title, fixing the `noSvgWithoutTitle` rule

Both scripts use regex-based pattern matching and are designed for one-shot codebase-wide fixes. They are not integrated into pre-commit hooks — they are run manually when Biome lint violations accumulate.

## Related

- [[entities/biome-linter]] — the linter these scripts fix violations for
- [[concepts/project-linting]] — overall linting strategy
