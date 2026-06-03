---
tags: [web, ssr, hybrid-ssr, csr, performance, tanstack-start]
category: concept
---

# Rendering Strategies

Establish a clear decision framework and set of technical patterns for Server-Side Rendering (SSR), Hybrid SSR, and Client-Side Rendering (CSR) across the application to balance SEO, Time to First Byte (TTFB), First Contentful Paint (FCP), and client interaction latency.

---

## The Rendering Decision Matrix

We evaluate every page route against this decision matrix to select the most performant rendering architecture:

| Rendering Mode | Core Mechanism | Best Used For | SEO Impact | Performance Profile | Examples in App |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Full SSR** | Renders complete DOM + data on the serverless edge before sending HTML. | Static pages, slow-changing config metadata, or small, high-SEO priority listings. | **Maximum**. Crawlers receive fully populated HTML. | FCP matches TTFB. High risk of TTFB delay if DB queries are slow or heavy. | `/how-it-works`<br>`/concepts`<br>`/autoresearch` |
| **Hybrid SSR** | Server renders a small, critical subset (e.g., first 5 items) for instant FCP and SEO. Browser hydrates and fetches the remaining/full payload asynchronously in the background. | Dynamic lists, feeds, dashboard panels, charts, or heavy hierarchical structures. | **High**. Critical metadata and top content are indexable immediately. | Near-instant TTFB/FCP. No blocking main-thread or database bottlenecks. | `/` (Homepage)<br>`/memories`<br>`/memories/chain/$memoryId`<br>`/reasoning`<br>`/market-overview` |
| **No SSR (Pure CSR)** | Sends a static HTML shell immediately. Client fetches 100% of the data post-mount. | Authenticated views, dashboard settings, tools, or secondary logs with zero SEO requirements. | **None**. Crawlers see an empty container or loading skeleton. | Near-zero TTFB. Slowest FCP/LCP as client waits for APIs to mount. | `/audits`<br>`/login`<br>`/signup` |

---

## Core Implementations & Patterns

### 1. Hybrid SSR (Initial Partial + Background Hydration)

This is the primary pattern for chronological feeds (`/reasoning`, `/memories`) and heavy page loads. By leveraging TanStack Start's `createServerFn` and TanStack Query (React Query) query clients, we render a partial state on the server, then fetch the full data silently on client mount.

#### Implementation Standard
1. **Server Loader**: Constrains the database fetch to an aggressive limit (typically 5 items).
2. **Client Fetcher**: Runs the query with the full limit (typically 50 items).
3. **Query Factory configuration**: Uses `staleTime: 0` (or `staleTime: 1000 * 30` depending on latency requirements) to mark the server-rendered payload as immediately stale in the browser cache.
4. **Hydration Phase**: On mount, React hydrates the DOM using the server's 5 items (FCP is instant, CLS is avoided). Immediately after hydration, the query client fires the background request for 50 items, expanding the UI seamlessly.

#### Case Study: Focus Node "Neighborhood" SSR (`/memories/chain/$memoryId`)
For recursive parent/descendant event chains, loading the entire hierarchical tree on the server blocks edge execution.
* **Refactored Architecture**: The route loader calls `fetchMemoryById` to load *only* the specific target node on the server.
* **Component Rendering**: The page is rendered with a 1-item chain.
* **Client Expansion**: The client query client executes the full `get_memory_chain` RPC (graph traversal CTE) post-mount, hydrating the remaining nodes in the background.

```typescript
// apps/web/src/routes/memories/chain/$memoryId.tsx
export const Route = createFileRoute('/memories/chain/$memoryId')({
    // Server Loader: fetches only the focus memory (1 row)
    loader: ({ params }) => getFocusMemory({ data: params.memoryId }),
    component: RouteComponent,
});

function RouteComponent() {
    const focusMemory = Route.useLoaderData();
    const getEventChainFn = useServerFn(getEventChain);

    // Initial shape for immediate hydration
    const initialData = {
        chain: focusMemory ? [focusMemory] : [],
        targetMemory: focusMemory || null,
    };

    return (
        <EventChainPage
            initialData={initialData}
            fetchFn={() => getEventChainFn({ data: memoryId })}
        />
    );
}
```

### 2. No SSR (Pure Client-Side Rendering)

To completely eliminate database overhead during the initial request phase for non-SEO views, we bypass loaders entirely.

#### Implementation Standard
* Define the Route with no loader property.
* In the component, fetch the data directly using a TanStack Query hook, displaying a loading skeleton or spinner during FCP.

---

## Best Practices & Guidelines

1. **Avoid Parallel Loader Queries**: Do not run multiple large queries inside a server loader. Consolidated fetches or moving secondary queries to client-side fetching keeps TTFB under `10ms`.
2. **Normalize Date Formatting**: Ensure dates rendered during both server-side generation and client-side hydration are symmetric. Always format timestamps on the server inside loaders or use locked-timezone utility helpers (such as `formatEasternDateTimeWithYear`) to avoid timezone/whitespace mismatch warnings (React Error #418).
3. **TDD Hydration Verification**: When adding or refactoring layouts, write tests utilizing `assertHydrationSymmetry` to verify that components render symmetrically under both SSR and client hydration modes.

---

## Related

- [[concepts/performance-auditing-strategy]]
- [[entities/web-app]]
- [[concepts/tanstack-query]]
