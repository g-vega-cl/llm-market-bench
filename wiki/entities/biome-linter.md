---
tags: [linter, typescript, biome, tooling]
category: entity
---

# Biome Linter

Biome is the TypeScript/JavaScript linter and formatter used for the web app (`apps/web/`) and shared packages (`packages/database`, `packages/ui-design-system`). It replaces ESLint and Prettier with a single fast Rust-based tool.

## Configuration

Configured in `biome.json` at the monorepo root:

- **Formatter**: 4-space indent, 100 line width, single quotes, trailing commas, always semicolons
- **Linter**: recommended rules; `noExcessiveCognitiveComplexity`, `noNonNullAssertion`, `noExplicitAny`, `noArrayIndexKey`, `noStaticElementInteractions`, `useKeyWithClickEvents`, `noLabelWithoutControl` all downgraded to `warn`
- **Assist**: `organizeImports` on save
- **VCS**: enabled with git ignore file
- **Files**: includes `apps/web/**`, `packages/database/**`, `packages/ui-design-system/**`; excludes `dist`, `.netlify`, `node_modules`, `.vinxi`, `routeTree.gen.ts` (auto-generated), `app.css` (Tailwind directives)
- **File-level overrides**: D3/chart components get `noExcessiveCognitiveComplexity: "off"`; interactive card containers get `noStaticElementInteractions` and `useKeyWithClickEvents: "off"`

## Pre-commit behavior

Biome runs in the pre-commit hook via:
```sh
pnpm biome check --no-errors-on-unmatched apps/web packages/database packages/ui-design-system || true
```

It is **non-blocking** — pre-existing lint errors (38 as of 2026-05-14, mostly missing `type` props on buttons) do not block commits. Only `pnpm build:web` (tsc --noEmit) is blocking.

## Usage

Lint + format check:
```sh
pnpm biome check
```

Auto-fix all:
```sh
pnpm biome check --write
```

Auto-fix from subdirectory (monorepo path resolution quirk):
```sh
cd apps/web && pnpm biome check --write .
```

## Related

- [[entities/ruff-linter]] — Python counterpart
- [[concepts/project-linting]] — pre-commit hook design
- [[concepts/tool-enforcement]] — code quality enforcement