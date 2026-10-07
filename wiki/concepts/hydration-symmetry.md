---
tags: [frontend, ssr, hydration, i18n, rendering]
category: concept
---

# Hydration Symmetry

The web app is server-rendered by TanStack Start and then hydrated on the client. Any value that renders differently on the server than on the client produces a React hydration mismatch. The most common source of these mismatches is locale-dependent formatting: `Number.prototype.toLocaleString()` and `Date.prototype.toLocaleString()` fall back to the *runtime's* default locale, which differs between the SSR Node process and the visitor's browser.

Hydration symmetry is the discipline of making every rendered value deterministic across both environments.

## The Problem

A call like `value.toLocaleString()` with no locale argument produces `"10,582.61"` on a US-locale server but `"10.582,61"` in a browser defaulting to `es-CL` or a European locale. React sees two different strings for the same node and throws a hydration error, forcing a client re-render and a visible flash.

## The Rules

1. **Always pass an explicit locale.** Every `toLocaleString` call in the web app passes `'en-US'` as the first argument, e.g. `value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })`. Never rely on the runtime default (`undefined` or omitted).
2. **Route date/time formatting through `~/utils/date`.** Instead of `new Date(x).toLocaleString()` / `toLocaleTimeString()`, components import helpers such as `formatEasternDateTime`, `formatEasternDateTimeWithYear`, `formatEasternTime`, and `formatEasternShortTime`. These pin both the locale and the timezone (US Eastern), so timestamps render identically on server and client.
3. **Suppress hydration warnings only where unavoidable.** Third-party or browser-managed nodes (e.g. the async Google Fonts `<link>` and its `<noscript>` fallback in `__root.tsx`) use `suppressHydrationWarning` because the browser mutates them outside React's control.

## Enforcement

The regression suite `apps/web/src/test/hydration.test.tsx` ("SSR Hydration Symmetry Regression Suite") renders each page with `ReactDOMServer.renderToString` and compares against a client render. It spies on `Number.prototype.toLocaleString` to simulate a client browser defaulting to a non-US locale (`es-CL`) and asserts that no hydration errors are produced. Pages covered include Home, Market Overview, Event Chain, Memories, and the sitemap of all pages.

## Related

- [[entities/web-app]]
- [[concepts/rendering-strategies]]
- [[concepts/zero-frontend-compute]]
- [[concepts/fluent-responsive-design]]
