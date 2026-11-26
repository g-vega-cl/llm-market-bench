---
tags: [auth, oauth, google, web, security, session]
category: concept
---

# Google-Only Authentication

The web app authenticates users exclusively through Google OAuth. The former email/password login form and its Cloudflare Turnstile captcha were removed; the shared `Auth` component (`apps/web/src/shared/auth/components/Auth.tsx`) now renders a single "Continue with Google" button and drives the whole sign-in flow.

## The Auth Component

`Auth` is a presentational + interaction component used by the auth routes. It takes optional `actionText` (default `Sign in to Benchify`), `redirectPath`, and `errorCode` props.

### Auth Phases

State is modeled as a discriminated union:

```ts
type AuthPhase =
  | { kind: 'idle' }
  | { kind: 'redirecting' }
  | { kind: 'error'; message: string };
```

- **idle** — the Google button is enabled.
- **redirecting** — set immediately on click; the button shows `Redirecting to Google...`, is disabled, and `isLoading`. Re-entry is guarded (`if (phase.kind === 'redirecting') return;`) so double-clicks cannot start two OAuth flows.
- **error** — renders an inline `role="alert"` block with the failure message.

### Error Code Mapping

`resolveAuthErrorMessage(code)` maps known `errorCode` query values to safe copy and falls back to a generic message for anything else:

| Code | Message |
|------|---------|
| `access_denied` | Google sign-in was cancelled. Try again when you are ready. |
| `exchange_failed` | We could not finish signing you in with Google. Please try again. |
| `oauth_failed` / unknown | Google sign-in could not be completed. Please try again. |

Arbitrary strings passed as `errorCode` are never echoed to the user — only the mapped copy is shown, preventing phishing-style copy injection. The initial phase is derived from `errorCode` via `initialPhaseFromErrorCode`, and a `prevErrorCodeRef` effect re-derives the phase when the prop changes.

### OAuth Flow

`handleGoogleLogin`:

1. bails out if already `redirecting`;
2. sets phase to `redirecting`;
3. calls `markPendingGoogleAuth()` (see below);
4. resolves the browser client via `getAuthBrowserClient()` and calls `auth.signInWithOAuth({ provider: 'google', options: { redirectTo: buildOAuthCallbackUrl(window.location.origin, returnPath) } })`;
5. throws on `result.error`;
6. on any thrown error, calls `clearPendingGoogleAuth()` and sets an `error` phase with the error message (or a generic fallback).

### bfcache Recovery

A `pageshow` listener checks `event.persisted`; when the page is restored from the back/forward cache after an abandoned OAuth redirect, it clears the pending marker and resets the phase to `idle`, so the user is not stuck on a disabled "Redirecting..." button.

### Return Path & Recipes Gate

The return path is `redirectPath ?? resolveCurrentReturnPath()`. `isRecipesPath()` (trailing-slash and query/hash tolerant) detects `/recipes` and `/recipes/*` to show the Strategy Recipe Studio beta copy (2 free 2-week backtests/day via strata-auto-go, 3 live paper turns/day via auto-go). A financial disclaimer block (`FINANCIAL_DISCLAIMER_SHORT_TEXT`) and Terms/Privacy links are always shown, plus a link to `/recipes-demo` to inspect a public sample backtest.

## Pending Auth Marker (`apps/web/src/shared/auth/pending-auth.ts`)

A small sessionStorage-backed helper tracks an in-flight Google sign-in so the callback route can distinguish a genuine return from a cold visit:

- `markPendingGoogleAuth()` — writes `benchify_auth_started = 'google'`.
- `clearPendingGoogleAuth()` — removes the marker.
- `consumePendingGoogleAuth()` — reads and removes the marker, returning the provider or `null`.

All three guard against `typeof window === 'undefined'` and wrap storage access in try/catch, so private-browsing or restricted-iframe environments degrade gracefully while OAuth still proceeds. The marker is cleared on mount and on bfcache restore.

## Related

- [[concepts/auth-redirect-sanitization]] — return-path and OAuth callback URL sanitization
- [[concepts/auth-db-client-separation]] — browser vs server auth client separation
- [[concepts/google-only-auth]] — this page
- [[entities/web-app]] — the TanStack Start dashboard
