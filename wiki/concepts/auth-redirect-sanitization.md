---
tags: [auth, security, redirect, open-redirect, oauth, tanstack-start]
category: concept
---

# Auth Redirect Sanitization & Return-Path Preservation

The web app gates several routes behind authentication (`/_authed/recipes`, `/_authed/recipes/backtest/$jobId`, `/profile`). When an unauthenticated visitor lands on a gated route, they are sent to `/login` or `/signup`, and after a successful sign-in they must be returned to the page they originally wanted — not dumped on the home page. Doing that safely requires rejecting attacker-controlled redirect targets, because a naive `?next=` parameter is a classic **open-redirect** vector.

`apps/web/src/shared/auth/redirect.ts` is the single source of truth for both concerns: it sanitizes every redirect target and builds the OAuth callback URL with a safe `next` parameter.

## The Three Helpers

### `sanitizeRedirectPath(raw)`

Returns a safe internal path or `/`. A candidate is accepted only when it:

- is a string,
- starts with a single `/` (not `//` and not `/\`),
- contains no ASCII control characters (`\u0000`–`\u001F`, `\u007F`).

Everything else — absolute URLs (`https://evil.com/phish`), protocol-relative URLs (`//evil.com`), backslash tricks (`/\evil.com`), and tab/newline prefixes (`/\t/evil.com`, `/\n/evil.com`) that the WHATWG URL parser strips before `//` — resolves to `/`. Empty and `undefined` inputs also resolve to `/`.

### `resolveCurrentReturnPath()`

Reads `window.location.pathname + window.location.search` in the browser and runs it through `sanitizeRedirectPath`. Auth self-paths (`/`, `/login`, `/signup`, `/logout`, `/auth/callback`) are collapsed to `/`, so signing in from the login page never bounces the user back to the login page. Returns `/` during SSR (`typeof window === 'undefined'`).

### `buildOAuthCallbackUrl(origin, currentPath?)`

Builds `${origin}/auth/callback`. When the sanitized current path is not an auth self-path, it appends `?next=<encoded path>` so the callback can restore the destination. A login-page origin therefore produces a bare `/auth/callback`, while a gated `/recipes` origin produces `/auth/callback?next=%2Frecipes`.

## Wiring

- **Google OAuth** — `Auth.tsx` calls `buildOAuthCallbackUrl(window.location.origin, resolveCurrentReturnPath())` as the `redirectTo` option of `signInWithOAuth`.
- **Callback** — `routes/auth.callback.tsx` validates `next` with `sanitizeRedirectPath` in `validateSearch`, exchanges the code, then `throw redirect({ href: sanitizeRedirectPath(next) })`.
- **Signup** — `routes/signup.tsx` validates `next` in `validateSearch`, passes it to `SignupComp` as `redirectTo`, forwards it to `signupFn` as `redirectUrl`, and navigates to the sanitized value on success.
- **Login** — `Login.tsx` resolves `resolveCurrentReturnPath()` on success and navigates there (or to `/` when it is the root), and forwards the same path into the signup mutation so a first-time user is returned to the gated route after account creation.

## Gated-Route UX

When the current return path starts with `/recipes`, `Auth.tsx` renders a **Strategy Recipe Studio — Free Beta Access** panel inside the auth card explaining the free beta limits (2 backtests/day on `strata-auto-go`, 3 live paper turns/day on `auto-go`) and linking to the public read-only `/recipes-demo` showcase so a visitor can inspect a sample backtest before signing in. See [[entities/recipe-studio]].

## Why It Matters

- **Open-redirect prevention** — an attacker cannot craft `/login?next=https://evil.com` or a protocol-relative/control-character variant to bounce a freshly authenticated user to a phishing site.
- **Return-path preservation** — deep links into gated routes survive the auth round-trip through both password login and Google OAuth.
- **Single implementation** — the sanitizer is shared by the callback route, signup, login, and the OAuth builder, so the rule cannot drift between entry points.

## Tests

`apps/web/src/shared/auth/redirect.test.ts` asserts that clean internal paths (including query strings) pass through, that external, protocol-relative, backslash, and control-character inputs collapse to `/`, and that `buildOAuthCallbackUrl` only attaches `next` for non-auth paths.

## Related

- [[concepts/supabase-redirect-whitelisting]] — Supabase project-level OAuth redirect URL configuration
- [[entities/recipe-studio]] — the gated Studio and its public `/recipes-demo` showcase
- [[entities/web-app]] — the dashboard that hosts the auth routes
- [[concepts/auth-db-client-separation]] — the Auth (cloud) vs DB (archive) client split
