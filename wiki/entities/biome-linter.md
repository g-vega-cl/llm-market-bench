---
tags: [linter, typescript, biome, tooling]
category: entity
---

# Biome Linter

Biome is the TypeScript/JavaScript linter and formatter used for the web app (`apps/web/`) and shared packages (`packages/database`, `packages/ui-design-system`). It replaces ESLint and Prettier with a single fast Rust-based tool.

## Configuration

Configured in `biome.json` at the monorepo root:

- **Formatter**: 4-space indent, 100 line width, single quotes, trailing commas, always semicolons
- **Linter**: recommended rules, `noExcessiveCognitiveComplexity` warn, `noNonNullAssertion` warn
- **Assist**: `organizeImports` on save
- **VCS**: enabled with git ignore file
- **Files**: includes `apps/web/**`, `packages/database/**`, `packages/ui-design-system/**`; excludes `dist`, `.netlify`, `node_modules`, `.vinxi`

## Usage

Lint + format check:
```sh
pnpm biome check
```

Auto-fix all:
```sh
pnpm biome check --write
```

Runs as part of the pre-commit hook before tests.

## Related

- [[entities/ruff-linter]] — Python counterpart
- [[concepts/tool-enforcement]] — code quality enforcement
