# Type Generation from Supabase Database

This document explains how to generate TypeScript types from the Supabase database schema and keep them synchronized with the frontend.

## Why Generate Types from the Database?

1. **Single Source of Truth**: The database schema is the authoritative source for data structures. Generating types from it ensures the frontend always matches the backend.

2. **Catch Type Drift Early**: When a migration adds or changes a column, TypeScript will flag mismatches immediately rather than causing runtime errors.

3. **Reduced Duplication**: No need to manually maintain parallel type definitions across the codebase.

4. **Complete Coverage**: Generated types include all columns, even optional ones that might be missed in manual definitions.

5. **Type Safety**: PostgreSQL types like `JSONB` become proper TypeScript `Json` types instead of `any`.

## Architecture

```
Supabase Database (Remote)
        │
        │ supabase gen types typescript --linked
        ▼
packages/database/supabase-types.ts  (Generated - committed to repo)
        │
        │ Re-exports with exclusions
        ▼
packages/database/index.ts  (Curated type exports)
        │
        │ Import from @llm-market-bench/database
        ▼
apps/web (Frontend)
```

## Tables Included

Types are generated for all tables and views, but the `index.ts` re-exports only those used by the frontend:

| Table/View | Type Export | Notes |
|------------|-------------|-------|
| `memories` | `Memory` | `embedding` excluded (server-side only) |
| `decisions` | `Decision` | `embedding` excluded (server-side only) |
| `trades` | `Trade` | - |
| `portfolios` | `Portfolio` | - |
| `portfolio_performance` | `PortfolioPerformance` | - |
| `llm_reasoning_logs` | `LLMReasoningLog` | - |
| `newsletter_snapshots` | `NewsletterSnapshot` | - |
| `market_data_cache` | `MarketDataCache` | - |
| `position_pnl` (view) | `PositionPnl` | - |
| `portfolio_positions` | `PortfolioPosition` | - |

### View Model Types

Additional types are exported for frontend-specific combinations:

- `PositionWithReasoning` - `PositionPnl` with added `reasoning` field (joined from decisions)
- `TradeWithReasoning` - `Trade` with added `reasoning` field (joined from decisions)

## How to Generate Types

### Prerequisites

1. Install Supabase CLI:
   ```bash
   brew install supabase/tap/supabase
   ```

2. Login to Supabase CLI:
   ```bash
   supabase login
   ```

3. Initialize Supabase in the project (if not already done):
   ```bash
   supabase init
   ```

4. Link to the remote project:
   ```bash
   supabase link --project-ref <project-ref>
   ```

### Generate Types

Run the generate script in the database package:

```bash
cd packages/database
pnpm generate:types
```

This runs `supabase gen types typescript --linked > supabase-types.ts`.

### After Generating

1. Review the generated `supabase-types.ts` file to ensure it looks correct
2. The `packages/database/index.ts` re-exports are already configured to use the generated types
3. Update the frontend imports if needed

## When to Regenerate Types

Regenerate types after any database migration that:

- Adds a new table or view
- Adds, removes, or modifies a column
- Changes a column's type or nullability
- Adds or modifies constraints

**Note**: Adding new tables not used by the frontend is fine - they won't break anything, but you should add them to `packages/database/index.ts` if you want to use them.

## Excluded Fields

The following fields are excluded from frontend types because they are server-side only:

| Table | Field | Reason |
|-------|-------|--------|
| `memories` | `embedding` | `VECTOR(768)` - used for similarity search, never sent to frontend |
| `decisions` | `embedding` | `VECTOR(768)` - used for clustering, never sent to frontend |

These are excluded using TypeScript's `Omit` utility type:

```typescript
export type Memory = Omit<Database['public']['Tables']['memories']['Row'], 'embedding'>
export type Decision = Omit<Database['public']['Tables']['decisions']['Row'], 'embedding'>
```

## Importing Types

Frontend code should import types from `@llm-market-bench/database`:

```typescript
import type { Memory, Trade, Portfolio } from '@llm-market-bench/database'
```

The package is configured in `packages/database/package.json` and referenced via pnpm workspace.

## Type Structure

Each table type is exported as:

- **Row type** (e.g., `Memory`): The shape of a row when selecting from the table
- **Insert type** (e.g., `MemoryInsert`): The shape required when inserting a new row
- **Update type** (e.g., `MemoryUpdate`): The shape allowed when updating a row

Example usage:

```typescript
// Selecting rows
const memories: Memory[] = await supabase.from('memories').select('*')

// Inserting a new row
const newMemory: MemoryInsert = { content: '...', metadata: {} }

// Updating a row
const update: MemoryUpdate = { content: 'updated content' }
```

## Troubleshooting

### "Command not found: supabase"

The CLI is not installed or not in your PATH. Install it with:
```bash
brew install supabase/tap/supabase
```

### "Access token not provided"

Run `supabase login` to authenticate, or set the `SUPABASE_ACCESS_TOKEN` environment variable.

### "Project not linked"

Run:
```bash
supabase link --project-ref <project-ref>
```

### Type errors after regeneration

If TypeScript reports errors after regenerating types:

1. Check if a migration added a required column - the frontend might need to handle it
2. Check if a column was removed - the frontend code might reference it
3. Check if a column type changed - frontend code might need adjustment

## Adding New Tables to Frontend

When you add a new table that the frontend needs:

1. Ensure types are regenerated (`pnpm generate:types`)
2. Add the type to `packages/database/index.ts`:
   ```typescript
   export type NewTable = Database['public']['Tables']['new_table']['Row']
   ```
3. Import and use in frontend code:
   ```typescript
   import type { NewTable } from '@llm-market-bench/database'
   ```
