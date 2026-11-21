---
tags: [web, llm-proxy, audit, observability, private-route]
category: entity
---

# LLM Proxy Logs Page

`/llm-logs` is a private, owner-only viewer for the free LLM proxy's audit trail. It is the web surface over the records the proxy writes for every completion (see [[entities/free-llm-proxy]]), so routing decisions, failover chains, token usage, latency, and billing provenance can be inspected from the dashboard instead of shelling into the proxy host.

## Access Control

Three independent gates, all of which must pass:

1. **Session gate (`beforeLoad`)** — `apps/web/src/routes/llm-logs.tsx` throws `redirect({ to: '/auth', search: buildAuthRedirectSearch(location.pathname, location.searchStr), replace: true })` when `context.user` is absent, so an anonymous visitor is sent to `/auth` with `/llm-logs` as the return path (the same helper the other auth-gated routes use).
2. **Email allowlist** — the route component resolves `isAllowedLlmLogsEmail(user?.email)` from `apps/web/src/features/llm-logs/llm-logs-types.ts`. `ALLOWED_LLM_LOGS_EMAILS` is `['g.vega.cl@gmail.com']`, and the check trims and lowercases the caller's email before comparing case-insensitively. A signed-in user outside the allowlist renders `<NotFound />` rather than an error or an empty table, so the route's existence is not disclosed.
3. **Server-side enforcement** — `fetchLlmLogsData` (`apps/web/src/features/llm-logs/llm-logs-server.ts`) re-checks the caller before reading, throwing `Authentication required` for a missing session and `Restricted to authorized accounts` for a non-allowlisted email. Neither path issues a proxy request, so the browser gate is never the only barrier.

The route head declares `robots: noindex, nofollow` and the title `LLM Proxy Logs | Benchify`, so the page never enters a search index.

## Proxy Endpoint (`GET /v1/logs`)

The page reads a dedicated paginated audit endpoint on the free LLM proxy (see [[entities/free-llm-proxy]]):

```
GET /v1/logs?limit=50&offset=0&status_code=429&provider=groq&billing=paid
Authorization: Bearer <FREE_PROXY_MASTER_KEY>
```

- **Auth** — `verify_master_key(authorization, request=request)`; an unauthenticated request returns `401`.
- **Query parameters** — `limit` (clamped to `1..200`, default `50`), `offset` (clamped to `>= 0`), and optional `status_code`, `provider` (matched against `routed_provider`), and `billing` filters.
- **Response** — `{ total, limit, offset, logs }`, where `total` is the unfiltered-by-page count for the active filter set and `logs` is ordered `timestamp DESC, rowid DESC` (newest first).
- **Row shape** — `id`, `timestamp`, `requested_model`, `routed_provider`, `routed_model`, `prompt_tokens`, `completion_tokens`, `total_tokens`, `latency_ms`, `status_code`, `failover_chain`, `error_message`, `client_ip`, `user_agent`, `purpose`, `prompt_preview`, `is_stream`, `usage_available`, `ttft_ms`, `duration_ms`, `stream_completed`, `billing`.

`AuditDB.get_logs()` in `apps/free_llm_proxy/db.py` implements the query: it clamps the paging arguments, builds static `WHERE` clauses for the active filters, runs a `COUNT(*)` for `total`, and parses the stored `failover_chain` JSON string into a list (falling back to `[]` on malformed JSON or a non-list value) so the client never has to decode it.

## Data Flow

`LlmLogsRouteComponent` owns the query state; `LlmLogsPage` (`apps/web/src/features/llm-logs/LlmLogsPage.tsx`) is a pure presentation component.

- `filter` — `LlmLogsFilter`, initialized to `{ limit: 50, offset: 0 }`. Pagination is expressed as `limit`/`offset`, and the page's filter controls call `onFilterChange`.
- `data` — `LlmLogsResponse | null`, the server payload (`metrics`, `logs`, `total`, `isFallbackRecentOnly`, `proxyUrl`).
- `errorMessage` — a failed read is surfaced in-flow instead of being swallowed; the message falls back to `Failed to load proxy logs` for a non-`Error` throw.
- `isLoading` — set around every fetch.

`loadLogs(activeFilter)` is a `useCallback` that short-circuits when the caller is not authorized, calls `fetchLlmLogsFn({ data: activeFilter })`, and always clears `isLoading` in a `finally`. A `useEffect` keyed on `[isAuthorized, filter, loadLogs]` runs it on mount and on every filter change, and `onRefresh` re-runs the same call with the current filter.

### Server function (`fetchLlmLogsData`)

`fetchLlmLogsFn` is a `createServerFn({ method: 'GET' })` whose validator defaults an absent payload to `{}`; the handler delegates to `fetchLlmLogsData(filter)`:

1. **Auth** — `getAuthServerClient().auth.getUser()`; a missing user throws `Authentication required`, a non-allowlisted email throws `Restricted to authorized accounts`.
2. **Proxy config** — `resolveProxyConfig()` reads `FREE_LLM_PROXY_URL` (default `https://llm.clvg.uk/v1`, trailing slash stripped) and `FREE_PROXY_MASTER_KEY` (falling back to `STRATA_API_KEY`). A missing key throws the generic `Proxy authentication is not configured on the server` rather than issuing an unauthenticated request — the message deliberately omits the env var / API key names so server-side secret identifiers are never leaked to the client.
3. **Parallel fetch** — `/metrics` and `/logs?<params>` are requested together with `Authorization: Bearer <key>` and a 10-second `AbortSignal.timeout`. `limit` is clamped to `1..200` and `offset` to `>= 0` before serialization; `status_code`, `provider`, and `billing` are only appended when set.
4. **Metrics failure** — a non-`ok` metrics response throws `Free LLM proxy metrics failed (<status>)`.
5. **Logs success** — the payload's `logs` are normalized through `normalizeLogEntry` (coercing nulls to `''`/`0`, defaulting `routed_provider`/`routed_model` to `'none'`, `billing` to `'free'`, `duration_ms` to the latency, and normalizing `failover_chain` from either an array or a JSON string) and returned with `isFallbackRecentOnly: false`.
6. **Logs 404 fallback** — when the proxy predates `/v1/logs`, the handler falls back to `metrics.recent_calls` (the 10 most recent calls embedded in the metrics payload), normalizes them the same way, and returns `isFallbackRecentOnly: true` so the page can label the degraded view.
7. **Other logs failures** — any other non-`ok` status throws `Free LLM proxy logs failed (<status>)`.

## Page Layout

`LlmLogsPage` renders three blocks inside a `PageLayout maxWidth="xl"`:

1. **Header & filters** — the `Free LLM Proxy Logs` title with a solid `PRIVATE` badge, an info badge for `metrics.connector_id`, a danger `401 SPIKE` badge when `metrics.security_alert_active` is set, the resolved proxy URL (suffixed `(showing recent 10 from /v1/metrics)` when `isFallbackRecentOnly`), and a `Refresh` button that disables while loading. Four `Select` controls drive the filter: status (`All Statuses`, `200 OK`, `401 Unauthorized`, `429 Rate Limited`, `502/503 Error`), provider (populated from `metrics.providers` keys), billing (`All Billing`, `Free Tier`, `Paid Fallback`), and rows per page (`25`/`50`/`100`/`200`). Every change resets `offset` to `0`.
2. **Summary telemetry** — an `items-stretch` `MetricTile` grid (`repeat(auto-fit,minmax(min(100%,12rem),1fr))`) showing Total Requests, Success Rate (`success_rate_pct` to one decimal), Total Tokens, Avg Latency (rounded ms), and Paid Calls (24h). A failed read renders an `ErrorCard` titled `Proxy Telemetry Error` above the tiles.
3. **Call audit stream** — a `SectionHeading` with an `N of M calls` counter, then either an `EmptyState` (`No proxy calls recorded` / `No call_logs matched the active filters.`) or a `Table` with columns Timestamp (UTC), Requested, Provider, Billing, Status, Tokens (right-aligned), and Latency (right-aligned). Status renders as a `Badge` colored by `statusBadgeColor` (2xx success, 429 warning, >=400 danger, else neutral), and billing renders as a soft `warning` badge for `paid` and `neutral` otherwise.

Each row is followed by an optional `LogRowDetail` row — an in-flow recessed `.voxel-trough` slot (never a floating tooltip, per [[concepts/in-flow-inspection]]) that renders `purpose`, `ip`, `model`, `ttft` (only when `is_stream === 1`), and the joined `failover:` chain in a wrapping meta line, then the `prompt_preview` and any `error_message` in monospace. The detail row is omitted entirely when none of those fields are present.

## Tests

- `apps/free_llm_proxy/tests/test_logs_endpoint.py` — `/v1/logs` returns `401` without a master key; with a key it returns newest-first rows, honors `provider`, `status_code`, and `billing` filters, and paginates via `limit`/`offset` while reporting the unfiltered `total`.
- `apps/web/src/features/llm-logs/llm-logs-server.test.ts` — an unauthenticated caller and a non-allowlisted authenticated caller both throw without calling `fetch`; an allowlisted caller issues exactly two Bearer-authenticated requests to `/metrics` and `/logs?limit=50&offset=0&provider=groq`; a `404` on `/logs` falls back to `metrics.recent_calls` with `isFallbackRecentOnly: true` and a parsed `failover_chain`; and when both `FREE_PROXY_MASTER_KEY` and `STRATA_API_KEY` are unset the handler throws `Proxy authentication is not configured on the server` without leaking either env var name in the message.
- `apps/web/src/features/llm-logs/LlmLogsPage.test.tsx` — renders the title, success rate, formatted token total, a log row, and the in-flow trough detail (`purpose:`, prompt preview, `failover:` chain).
- `apps/web/src/routes/-llm-logs.test.tsx` — drives the real `Route.options.beforeLoad` with a stubbed auth client: an unauthenticated context throws a redirect with `status: 307`, `to: '/auth'`, and `search: { redirect: '/llm-logs' }`; an authenticated context resolves without throwing, leaving the email allowlist to the component and the server function.

## Related

- [[entities/free-llm-proxy]] — the proxy whose audit rows this page reads, and the `/v1/logs` endpoint it exposes
- [[entities/web-app]] — the dashboard that hosts the route
- [[concepts/auth-db-client-separation]] — the auth client used by the session gate
- [[concepts/observability-standard]] — logging and traceback conventions
- [[concepts/in-flow-inspection]] — why row detail renders in a trough instead of a tooltip
