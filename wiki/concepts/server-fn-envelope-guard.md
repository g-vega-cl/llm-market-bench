---
tags: [web, tanstack-start, server-functions, error-handling, resilience]
category: concept
---

# Server-Function Envelope Guard

TanStack Start's client resolves a server-function response that is not a `{ result, error, context }` envelope to `undefined` instead of throwing. An edge 502, a request cut off at the origin, or a WAF JSON body all produce this. Every consumer that then reads a property of `undefined` reports a raw `TypeError` (e.g. `Cannot read properties of undefined (reading 'status')`) instead of the transport failure — or worse, renders an empty state over live data.

`apps/web/src/lib/server-fn.ts` exports `assertServerFnResult<T>(value, what)` to make that failure loud and retryable at the boundary.

## The Helper

```ts
export function assertServerFnResult<T>(value: T | undefined, what: string): T {
    if (value === undefined) {
        throw new Error(
            `${what} did not come back — the request was cut off before it finished. Try again.`,
        );
    }
    return value;
}
```

Call it at every server-function boundary where the caller would otherwise dereference the result.

## Why Throwing Is the Right Failure

- **TanStack Query keeps the last good payload.** A throwing `queryFn` leaves the previous `data` in place and retries with backoff, so a transient cut-off never blanks a live view. Returning `undefined` would overwrite the cache with an empty state.
- **The message is legible.** The thrown error names the surface (`The builder`, `The latest backtest run`, `The backtest run`) and states that nothing was queued, so the UI can show a retryable message instead of a stack trace.
- **It fails at the boundary, not at the first property read.** The failure is attributed to the transport, not to a downstream `undefined` dereference.

## Consumers

- `apps/web/src/features/recipes/builder/use-builder-chat.ts` — wraps `compileStrategyFn`; an envelope-less reply becomes a retryable `NO_REPLY_MESSAGE` and the phase becomes `error` (see [[concepts/recipe-builder-compiler]]).
- `apps/web/src/features/recipes/utils/use-latest-recipe-run.ts` — wraps `fetchLatestRecipeRunFn`; a cut-off keeps the previous run row and lets the query retry instead of blanking the status strip.
- `apps/web/src/features/recipes/pages/RecipeBacktestPage.tsx` — wraps `fetchRecipeRunDetailFn`; a cut-off keeps the last good run payload instead of flipping the page to "Not Found". The poll gate reads `q.state.data?.job?.status` so a missing payload never throws inside `refetchInterval`.

## Related

- [[concepts/recipe-builder-compiler]] — the `/build` compiler that consumes this guard
- [[entities/recipe-studio]] — the recipe surfaces that call server functions
- [[concepts/tanstack-query]] — caching and retry semantics the guard relies on
- [[entities/web-app]] — the TanStack Start app hosting these server functions
