---
tags: [web, tanstack-query, patterns]
category: source
---

# Source: TanStack Query Best Practices

Synthesized from `raw/docs/web/TANSTACK_BEST_PRACTICES.md`.

## Takeaways

- **Options Factory**: All queries are centralized in `src/lib/queries.ts` using named parameters for type safety and explicit API contracts.
- **SSR-Safe Singleton**: Uses a robust QueryClient setup that prevents data leakage between concurrent SSR requests.
- **Cursor Pagination**: Standardized pattern for infinite scrolling lists (Reasoning Logs, Memories).
- **Hybrid Fetching**: Combines server loaders for SEO/Initial load with client-side suspense queries for interactivity.
- **Server Function Parameter Unwrapping**: TanStack Start `useServerFn` hooks pass payloads wrapped in `{ data: ... }`. Server function handlers must safely unwrap both flat objects (`data.query`) and nested objects (`data.data.query`) to prevent `undefined` parameter evaluation.

## Related

- [[entities/web-app]]
