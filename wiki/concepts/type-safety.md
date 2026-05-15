---
tags: [typescript, type-safety, web-app, biome]
category: concept
---

# Type Safety

The web app enforces strict TypeScript type safety with zero `any` usage, enforced by Biome's `noExplicitAny` rule set to `error`. This ensures compile-time correctness and maintainability.

## Key Conventions

- **JSON Fields**: Use `Record<string, any>` for database JSONB fields (metadata, prompt, response) to ensure compatibility with TanStack Start's serialization layer.
- **Server Functions**: Use `.inputValidator()` and avoid `as unknown` casting to maintain type integrity.
- **Infinite Queries**: Implement the `extends CursorPage` constraint in all list factories for safe `getNextPageParam` access.
- **Timestamp Handling**: Gracefully handle `string | null` for all database timestamps.

## Database Types

`packages/database/index.ts` uses Supabase generated types with `Omit` to strip large JSON fields (embedding, metadata, prompt, response) and re-add them with explicit `Record<string, any>` annotations. This provides full type safety for all other columns while allowing flexible JSON serialization.

## D3 Type Annotations

Components using D3 (`ConceptMap`, `MemoryFlow`) received proper type annotations for geometry, hierarchy, and link generators, replacing `any` casts with `d3.GeoPermissibleObjects` and explicit generic parameters.

## Related

- [[entities/web-app]]
- [[entities/biome-linter]]
- [[concepts/project-linting]]
