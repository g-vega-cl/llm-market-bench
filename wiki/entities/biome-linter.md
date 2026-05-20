---
tags: [linter, typescript, biome, tooling]
category: entity
---

# Biome Linter

Biome is the TypeScript/JavaScript linter and formatter used for the web app (`apps/web/`) and shared packages (`packages/database`, `packages/ui-design-system`). It replaces ESLint and Prettier with a single fast Rust-based tool.

## Configuration

Configured in `biome.json` at the monorepo root:

- **Formatter**: 4-space indent, 100 line width, single quotes, trailing commas, always semicolons
- **Linter**: recommended rules; `noExplicitAny` is set to `error` (blocking). Rules downgraded to `warn` include: `noExcessiveCognitiveComplexity`, `noNonNullAssertion`, `noArrayIndexKey`, `noStaticElementInteractions`, `useKeyWithClickEvents`, `noLabelWithoutControl`.
- **Assist**: `organizeImports` on save
- **VCS**: enabled with git ignore file
- **Files**: includes `apps/web/**`, `packages/database/**`, `packages/ui-design-system/**`; excludes `dist`, `.netlify`, `node_modules`, `.vinxi`, `routeTree.gen.ts` (auto-generated), `app.css` (Tailwind directives)

## Override strategy

As of 2026-05-14, the project maintains 0 active warnings across all files. This is achieved through a layered override system in `biome.json` combined with strict inline comment-based ignore declarations for specific files:

### Wildcard Overrides in `biome.json`
To avoid blanket suppressions, wildcard `noExplicitAny` overrides have been completely removed from `biome.json`. Root overrides in `biome.json` are strictly reserved for other warnings (like cognitive complexity or D3 visualizer array keys):

| Group | Files | Rules suppressed | Rationale |
|---|---|---|---|
| Chart/visualization | PerformanceChart, PortfolioComparisonChart, PositionsTable, TradesTable, UncorrelatedPairs, FutureCatalysts, MarketStatusHero, HumanFriendlyPrompt, HumanFriendlyResponse, ReasoningPage, MemoryCard, MarketOverviewPage, MemoryFlow, ConceptMap, EventChainPage, fetch-portfolios, FormattedContent, DataCard, AgentInsights, CorrelationHeatmap | `noExcessiveCognitiveComplexity`, `noStaticElementInteractions`, `useKeyWithClickEvents`, `noNonNullAssertion`, `noArrayIndexKey` | D3 rendering pipelines, complex visual interactivity, static-layout index keys |
| Interactive cards | TradeActivity | `noArrayIndexKey`, `noExcessiveCognitiveComplexity`, `noStaticElementInteractions`, `useKeyWithClickEvents`, `useSemanticElements` | Expandable trade cards with nested interactive elements |
| Static indicators | ThoughtProcessFlow, MemoryCard | `noArrayIndexKey` | Deterministic dot indicators and asset grids |

### Localized `noExplicitAny` Overrides
Because global wildcard overrides for `noExplicitAny` are disabled, any genuine use of `any` required for database serialization, third-party libraries, or frameworks (such as TanStack Start `createServerFn` deep inference boundaries) **must** be suppressed locally in-file using inline comments:

```typescript
// biome-ignore lint/suspicious/noExplicitAny: Intentional any for TanStack Start serialization
```

### When to suppress/override

- **Do**: Use local inline `// biome-ignore` comments when a file's `any` usage represents genuinely dynamic data or is forced by framework serialization limitations.
- **Do**: Check if `noArrayIndexKey` overrides in `biome.json` apply if you are building visual/chart elements with static, deterministic list order.
- **Don't**: Ever add `noExplicitAny` to wildcard/group overrides in `biome.json`. Fix the type signature or use localized inline comments.

## Pre-commit behavior

Biome runs in the pre-commit hook. With 0 warnings as of 2026-05-14 and `noExplicitAny` configured as an error, the `|| true` fallback has been removed and Biome linting is now a blocking (fail-fast) step in the CI pipeline. Any lint error or unignored `any` type will abort the commit.

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
- [[entities/biome-lint-scripts]] — batch-fix scripts
