---
tags: [auth, security, redirect, oauth, web]
category: concept
---

# Auth Redirect Sanitization

All post-authentication navigation and OAuth callback URLs are built from sanitized, same-origin relative paths. The helpers live in `apps/web/src/shared/auth/redirect.ts` and prevent open-redirect and auth-loop attacks.

## Path Normalization

`normalizePathname(path)` strips the query/hash suffix and trailing slashes, defaulting to `/`:

```ts
function normalizePathname(path: string): string {
  const pathname = path.split(/[?#]/)[0] ?? '/';
  return pathname.replace(/\/+$/, '') || '/';
}
```

`isAuthSelfPath(path)` returns true when the normalized pathname is one of the auth self-paths: `/`, `/auth`, `/login`, `/signup`, `/logout`, `/auth/callback`. Because it normalizes first, `/login/`, `/login#section`, and `/auth?redirect=/chat` all count as self-paths.

## Sanitizers

### `sanitizeRedirectPath(raw)`

Trims the input, rejects non-strings and external/protocol-relative URLs, and returns `/` as the safe default. Only clean internal relative paths survive.

### `sanitizePostAuthRedirect(raw)`

Wraps `sanitizeRedirectPath` and additionally collapses any auth self-path to `/`:

```ts
export function sanitizePostAuthRedirect(raw: unknown): string {
  const safe = sanitizeRedirectPath(raw);
  return isAuthSelfPath(safe) ? '/' : safe;
}
```

This prevents redirect loops where a user returning from OAuth is bounced back to `/login`, `/auth`, `/signup`, `/logout`, or `/auth/callback` (including trailing-slash and query variants). Non-auth paths such as `/recipes?recipeId=rec-1` pass through unchanged.

### `resolveCurrentReturnPath()`

Builds the candidate from `window.location.pathname + search`, sanitizes it, and returns `/` when the result is an auth self-path. This is the fallback return path when no explicit `redirectPath` is supplied.

### `buildOAuthCallbackUrl(origin, currentPath?)`

Builds the Google OAuth `redirectTo` URL. It strips a trailing slash from the origin, sanitizes the next path, and:

- returns `<origin>/auth/callback` when the next path is an auth self-path;
- otherwise returns `<origin>/auth/callback?next=<encoded path>`.

### `buildAuthRedirectSearch(pathname, searchStr)`

Produces the `{ redirect }` search object used when a gated route sends an unauthenticated visitor to the auth page.

## Related

- [[concepts/google-only-auth]] — Google-only OAuth flow and pending-auth marker
- [[concepts/auth-db-client-separation]] — browser vs server auth client separation
- [[entities/web-app]] — the TanStack Start dashboard
