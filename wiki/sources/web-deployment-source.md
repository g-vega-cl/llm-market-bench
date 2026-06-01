---
tags: [web, deployment, netlify]
category: source
---

# Source: Web Deployment Guide

Synthesized from `raw/docs/web/tanstack-start-deploy-official.md` and current `netlify.toml` + `public/_headers`.

## Takeaways

- **Netlify Serverless**: Deployed as a serverless TanStack Start app on Netlify (project `autoresearch`).
- **Plugin Integration**: Uses the `@netlify/vite-plugin-tanstack-start` for automatic zero-config deployment.
- **Environment Management**: Client-side (VITE_) and server-side environment variables are managed directly in Netlify site settings.

## Edge Cache Headers (2026-06-01)

`public/_headers` and `netlify.toml` are kept in sync and define three CDN cache policies for SSR + static asset delivery:

- **Homepage (`/`)**: `Cache-Control: public, s-maxage=60, stale-while-revalidate=300` — the rendered homepage is identical for every anonymous visitor, so the CDN serves the same response for 60 s and revalidates in the background for the next 5 minutes. Cuts TTFB and LCP dramatically on repeat visits. Validated by `src/test/netlify-config.test.ts` (3 Vitest cases).
- **Static assets (`/assets/*`)**: `Cache-Control: public, max-age=31536000, immutable` — Vite-hashed filenames (`main-abc123.js`, `app-xyz789.css`) are content-addressed, so 1-year immutable caching is safe and saves the browser from re-fetching on every navigation.
- **Authenticated subtree (`/_authed/*`)**: `Cache-Control: private, no-store` — any page under the auth-gated layout must never be cached by a shared CDN, because the response is per-user and may leak portfolio data.
- **PostHog stealth proxy (`/p/static/*`)**: `Cache-Control: public, max-age=31536000, immutable` — versioned tracking assets served via the `status=200` proxy rewrite get the same long-term caching so the browser doesn't re-download `dead-clicks-autocapture.js` and friends on every visit.

## Related

- [[entities/web-app]]
- [[concepts/performance-auditing-strategy]] — performance budget + cache header rationale
- [[concepts/posthog-stealth-proxy]] — proxy rewrite and `/p/static/*` caching
- [[concepts/hero-loader-split]] — parallel hero + full loaders that benefit from `/` caching
