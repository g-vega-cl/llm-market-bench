---
tags: [react, profiling, build, vite, performance, observability]
category: concept
---

# React Profiling

The web app aliases `react-dom/client` to `react-dom/profiling` in `apps/web/vite.config.ts`, so production builds ship the React profiling build. This lets the React DevTools Profiler capture render timings and component commit data against the deployed app rather than only in local development.

## Configuration

The alias is declared under `resolve.alias` in the Vite config:

```ts
resolve: {
    alias: {
        'react-dom/client': 'react-dom/profiling',
    },
},
```

Every import of `react-dom/client` (including the app entry point) resolves to the profiling bundle instead of the standard production bundle.

## Trade-offs

The profiling build carries extra instrumentation overhead compared to the standard production build, so it is slightly larger and marginally slower at runtime. In exchange, render performance can be measured directly on real deployments — useful for diagnosing re-render hotspots and layout thrash in the dashboard's live portfolio views.

## Verification

`apps/web/src/test/react-profiling-config.test.ts` asserts that the alias is present in `vite.config.ts`, guarding against accidental removal during config refactors.

## Related

- [[entities/web-app]]
- [[concepts/rendering-strategies]]
- [[concepts/observability-standard]]
