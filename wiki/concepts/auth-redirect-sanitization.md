---
tags: [auth, security, redirect, open-redirect, oauth, tanstack-start]
category: concept
---

# Auth Redirect Sanitization & Return-Path Preservation

The web app gates several routes behind authentication (`/_authed/recipes`, `/_authed/recipes/backtest/$jobId`, `/profile`). When an unauthenticated visitor lands on a gated route, the `/_authed` `beforeLoad` guard throws a 307 to `/auth?redirect=<path>` (rather than throwing an error, which SSR answered with a 500 error page), and after a successful sign-in the visitor is returned to the page they originally wanted — not dumped on the home page. Doing that safely requires rejecting attacker-controlled redirect targets, because a naive `?next=` parameter is a classic **open-redirect** vector.

`apps/web/src/shared/auth/redirect.ts` is the single source of truth for both concerns: it sanitizes every redirect target and builds the OAuth callback URL with a safe `next` parameter.

## The Three Helpers

### `sanitizeRedirectPath(raw)`

Returns a safe internal path or `/`. A candidate is accepted only when it:

- is a string,
- starts with a single `/` (not `//` and not `/\`),
- contains no ASCII control characters (`\u0000`–`\u001F`, `\u007F`).

Everything else — absolute URLs (`https://evil.com/phish`), protocol-relative URLs (`//evil.com`), backslash tricks (`/\evil.com`), and tab/newline prefixes (`/\t/evil.com`, `/\n/evil.com`) that the WHATWG URL parser strips before `//` — resolves to `/`. Empty and `undefined` inputs also resolve to `/`.

### `resolveCurrentReturnPath()`

Reads `window.location.pathname + window.location.search` in the browser and runs it through `sanitizeRedirectPath`. Auth self-paths (`/`, `/auth`, `/login`, `/signup`, `/logout`, `/auth/callback`) are collapsed to `/`, so signing in from the auth card never bounces the user back to the auth card. Returns `/` during SSR (`typeof window === 'undefined'`).

### `buildAuthRedirectSearch(pathname, searchStr?)`

Builds the `{ redirect }` search object the gated-route guard forwards, running the composed path through `sanitizeRedirectPath` so the guard never constructs a redirect target by hand. `/_authed` passes `location.pathname` + `location.searchStr`, which is why a deep link like `/recipes?recipeId=rec-1` survives the round-trip while `//evil.com` collapses to `/`.

### `buildOAuthCallbackUrl(origin, currentPath?)`

Builds `${origin}/auth/callback`. When the sanitized current path is not an auth self-path, it appends `?next=<encoded path>` so the callback can restore the destination. A login-page origin therefore produces a bare `/auth/callback`, while a gated `/recipes` origin produces `/auth/callback?next=%2Frecipes`.

## Wiring

- **Gated routes** — `/_authed.tsx` `beforeLoad` throws `redirect({ to: '/auth', search: buildAuthRedirectSearch(pathname, searchStr), replace: true })`. SSR answers `307` with `Location: /auth?redirect=%2Frecipes`, so an anonymous deep link is a real navigation to a `200` auth card instead of a `500` error page. Its `errorComponent` still renders `<Login />` for the legacy `Not authenticated` error.
- **Auth entry** — `routes/auth.tsx` (and `routes/login.tsx`, kept as an alias) validate `?redirect=` with `sanitizeRedirectPath` and pass it to `Login` as `redirectPath`.
- **Google OAuth** — `Auth.tsx` calls `buildOAuthCallbackUrl(window.location.origin, returnPath)` where `returnPath` is the `redirect` param when present, else `resolveCurrentReturnPath()`, as the `redirectTo` option of `signInWithOAuth`.
- **Callback** — `routes/auth.callback.tsx` validates `next` with `sanitizeRedirectPath` in `validateSearch`, exchanges the code, then `throw redirect({ href: sanitizeRedirectPath(next) })`. It is a child of `routes/auth.tsx`; it carries no component, so the loader's redirect settles before the parent card would render.
- **Signup** — `routes/signup.tsx` validates `next` in `validateSearch`, passes it to `SignupComp` as `redirectTo`, forwards it to `signupFn` as `redirectUrl`, and navigates to the sanitized value on success.
- **Login** — `Login.tsx` navigates to `redirectPath` on success (falling back to `resolveCurrentReturnPath()`, or `/` at the root), forwards the same path into the signup mutation, and hands it to `Auth` so the card shows the right context.

## Gated-Route UX

Anonymous `/recipes` (including `/recipes?recipeId=<id>`) lands on `/auth?redirect=%2Frecipes`. When the resolved return path starts with `/recipes`, `Auth.tsx` renders a **Strategy Recipe Studio — Free Beta Access** panel inside the auth card explaining the free beta limits (2 backtests/day on `strata-auto-go`, 3 live paper turns/day on `auto-go`) and linking to the public read-only `/recipes-demo` showcase so a visitor can inspect a sample backtest before signing in. The panel is driven by the `redirectPath` prop, so it appears both on `/auth?redirect=/recipes` and `/login?redirect=/recipes`; a bare `/auth` shows the plain card. See [[entities/recipe-studio]].

## Why It Matters

- **Open-redirect prevention** — an attacker cannot craft `/login?next=https://evil.com` or a protocol-relative/control-character variant to bounce a freshly authenticated user to a phishing site.
- **Return-path preservation** — deep links into gated routes survive the auth round-trip through both password login and Google OAuth.
- **Single implementation** — the sanitizer is shared by the callback route, signup, login, and the OAuth builder, so the rule cannot drift between entry points.

## Tests

`apps/web/src/shared/auth/redirect.test.ts` asserts that clean internal paths (including query strings) pass through, that external, protocol-relative, backslash, and control-character inputs collapse to `/`, that `buildAuthRedirectSearch` sanitizes the carried target, and that `buildOAuthCallbackUrl` only attaches `next` for non-auth paths (with `/auth` counted as an auth path). `apps/web/src/routes/-authed-guard.test.tsx` asserts the guard throws a `307` to `/auth` with the sanitized `redirect` and lets an authenticated context through, and `Auth.test.tsx` asserts the beta panel shows for `/recipes` targets only.

## Related

- [[concepts/supabase-redirect-whitelisting]] — Supabase project-level OAuth redirect URL configuration
- [[entities/recipe-studio]] — the gated Studio and its public `/recipes-demo` showcase
- [[entities/web-app]] — the dashboard that hosts the auth routes
- [[concepts/auth-db-client-separation]] — the Auth (cloud) vs DB (archive) client split
