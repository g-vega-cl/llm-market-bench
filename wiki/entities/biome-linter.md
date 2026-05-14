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

## Override strategy

As of 2026-05-14, the project maintains 0 active warnings across all files. This is achieved through a layered override system in `biome.json`:

### Override groups (in order of definition)

| Group | Files | Rules suppressed | Rationale |
|---|---|---|---|
| Database | `**/packages/database/**` | `noExplicitAny` | JSONB columns — `Record<string, any>` is correct |
| Routes + auth | `**/routes/**`, `**/Login.tsx`, `**/signup.tsx` | `noExplicitAny` | TanStack `createServerFn as any` framework limitation |
| Lib utilities | `lib/queries.ts`, `lib/query-keys.ts` | `noExplicitAny` | React Query generic utility types |
| Chart/visualization | PerformanceChart, PortfolioComparisonChart, PositionsTable, TradesTable, UncorrelatedPairs, FutureCatalysts, MarketStatusHero, HumanFriendlyPrompt, HumanFriendlyResponse, ReasoningPage, MemoryCard, MarketOverviewPage, MemoryFlow, ConceptMap, EventChainPage, fetch-portfolios, FormattedContent, DataCard, AgentInsights, CorrelationHeatmap | `noExplicitAny`, `noArrayIndexKey`, `noExcessiveCognitiveComplexity`, `noStaticElementInteractions`, `useKeyWithClickEvents`, `noNonNullAssertion` | D3 rendering pipelines, complex interactivity, static-layout index keys |
| Interactive cards | TradeActivity | `noExplicitAny`, `noArrayIndexKey`, `noExcessiveCognitiveComplexity`, `noStaticElementInteractions`, `useKeyWithClickEvents`, `useSemanticElements` | Expandable trade cards with nested interactive elements |
| Feature components | MarketUpdates, PortfolioDetailPage, PortfoliosPage, TodayPage, NewsletterFeed, portfolios/queries/options, CauseAndEffectCard/List/Page, MemoriesPage, AuditsPage, fetch-audits | `noExplicitAny` | Supabase dynamic data flowing through page props |
| Static indicators | ThoughtProcessFlow, MemoryCard | `noArrayIndexKey` | Deterministic dot indicators and asset grids |
| Test files | `**/*.test.ts`, `**/*.test.tsx` | `noExplicitAny` | Mock objects, Link stubs, test data factories |

### When to add a new override

- **Do**: When a file's `any` usage represents genuinely dynamic data (JSONB columns, API responses, D3 type parameters)
- **Do**: When `noArrayIndexKey` fires on a list whose order is deterministic and items never reorder (indicator dots, ticker badges, static grids)
- **Don't**: When you can fix the issue in source with a proper interface or type

### Override mechanics

Overrides go at the ROOT level of `biome.json`, NOT inside `linter`:
```json
{
  "linter": { "rules": { ... } },
  "overrides": [
    {
      "includes": ["**/MyComponent.tsx"],
      "linter": {
        "rules": {
          "suspicious": { "noExplicitAny": "off" }
        }
      }
    }
  ]
}
```

## Pre-commit behavior

Biome runs in the pre-commit hook. With 0 warnings as of 2026-05-14, the `|| true` fallback is no longer needed. Biome lint can (and should) be blocking where possible, though currently remains non-blocking per the hook's historical configuration.

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
