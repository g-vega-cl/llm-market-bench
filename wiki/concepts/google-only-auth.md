---
tags: [auth, oauth, google, web, security, session]
category: concept
---

# Google-Only Authentication

The web app authenticates users exclusively through Google OAuth. The former email/password login form and its Cloudflare Turnstile captcha were removed; the shared `Auth` component (`apps/web/src/shared/auth/components/Auth.tsx`) now renders a single Google button and drives the whole sign-in flow. The same component backs both `/login` and the dedicated `/signup` page through its `mode` prop.

## The Auth Component

`Auth` is a presentational + interaction component used by the auth routes. It takes optional `mode` (`'login' | 'signup'`, default `'login'`), `actionText`, `redirectPath`, and `errorCode` props.

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
- **error** — renders an inline `role="alert"` block with the failure message (headed `Sign-in failed`, or `Sign-up failed` in signup mode).

### Mode-Dependent Copy

`mode` drives the heading, subtitle, and button label:

| | `mode="login"` (default) | `mode="signup"` |
|---|---|---|
| Heading (`actionText` wins if supplied) | `Sign in to Benchify` | `Create your Benchify account` |
| Button | `Continue with Google` | `Sign up with Google` |
| Error heading | `Sign-in failed` | `Sign-up failed` |
| Cross-link | `New to Benchify? Create an account →` → `/signup` | `Already have an account? Sign in →` → `/login` |

The cross-link is `alternateAuthHref`, which always carries the current return path as `?redirect=` (`/signup?redirect=%2Fbuild` from login, `/login?redirect=%2Fbuild` from signup). `resolveAuthSubtitle(isSignup, isRecipesGate)` produces the one-sentence subtitle: signup copy states the account is created automatically on first sign-in, and the `/recipes` gate variant narrows the promise to backtests and live paper sessions.

### Return-Path Gate Callout (`resolveGateCallout`)

A recessed `.voxel-trough` callout explains what signing in actually unlocks for the destination:

| Return path | Title | Body |
|---|---|---|
| `/recipes`, `/recipes/*` | `Strategy Recipe Studio — Free Beta Access` | Sign in with Google to get 2 free 2-week backtests/day (strata-auto-go) and live paper turns every 30 minutes (auto-go). |
| `/build?starter=<name>` | `Starter recipe selected — sign in to open` | Sign in to load this starter bot directly in Strategy Recipe Studio with 2 free paper backtests/day and 3 live paper bots. |
| `/build` (no `starter`) | `Your draft stays saved in this browser` | After signing in, you'll return directly to the builder to align your strategy and run up to 2 free paper backtests/day. |
| anything else | — (no callout) | — |

`isBuildPath()` strips trailing slashes and query/hash before comparing, and `hasStarterParam()` parses the query so a `starter` link reads as a starter hand-off rather than a browser draft. A financial disclaimer block (`FINANCIAL_DISCLAIMER_SHORT_TEXT`) and Terms/Privacy links are always shown, plus a link to `/recipes-demo` to inspect a public sample backtest.

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

### Return Path

The return path is `redirectPath ?? resolveCurrentReturnPath()`.

## Dedicated `/signup` Route

`apps/web/src/routes/signup.tsx` (`SignupRouteComponent`) renders `<Auth mode="signup" redirectPath={redirectPath} errorCode={error} />` rather than redirecting anonymous visitors to `/login`, so a new visitor lands on an explicit account-creation view. Its `validateSearch` normalizes `?next=` into the same sanitized target as `?redirect=` (via `sanitizeRedirectPath` / `sanitizePostAuthRedirect`), and `beforeLoad` still short-circuits a signed-in visitor straight to `sanitizePostAuthRedirect(target)`. The route declares its own head metadata (`Create account | Benchify`) and is warmed by the idle route warmup allowlist.

## Pending Auth Marker (`apps/web/src/shared/auth/pending-auth.ts`)

A small sessionStorage-backed helper tracks an in-flight Google sign-in so the callback route can distinguish a genuine return from a cold visit:

- `markPendingGoogleAuth()` — writes `benchify_auth_started = 'google'`.
- `clearPendingGoogleAuth()` — removes the marker.
- `consumePendingGoogleAuth()` — reads and removes the marker, returning the provider or `null`.

All three guard against `typeof window === 'undefined'` and wrap storage access in try/catch, so private-browsing or restricted-iframe environments degrade gracefully while OAuth still proceeds. The marker is cleared on mount and on bfcache restore.

## Browser Credential Hydration

The browser auth client resolves its URL/key from `VITE_SUPABASE_AUTH_*`, then `VITE_SUPABASE_*`, then `setRuntimeAuthConfig()` values hydrated from the SSR root context — so Google OAuth still works when `VITE_*` variables were not baked into the bundle at build time. See [[concepts/auth-db-client-separation]].

## Related

- [[concepts/auth-redirect-sanitization]] — return-path and OAuth callback URL sanitization
- [[concepts/auth-db-client-separation]] — browser vs server auth client separation
- [[concepts/google-only-auth]] — this page
- [[entities/web-app]] — the TanStack Start dashboard
- [[concepts/starter-recipes]] — the gallery starter hand-off reflected in the gate callout
