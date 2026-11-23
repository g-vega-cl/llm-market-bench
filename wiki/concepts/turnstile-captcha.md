---
tags: [auth, security, captcha, turnstile, cloudflare, bot-protection, supabase]
category: concept
---

# Cloudflare Turnstile CAPTCHA on Auth

The auth card (`apps/web/src/shared/auth/components/Auth.tsx`) is protected by **Cloudflare Turnstile**, a privacy-preserving CAPTCHA that issues a single-use token the Supabase Auth server verifies before accepting a password login or signup. The widget is opt-in: when `VITE_TURNSTILE_SITE_KEY` is unset the component renders nothing and the form submits exactly as before, so local development and unprovisioned environments keep working.

## Why It Exists

Password login and signup are the only unauthenticated write paths into Supabase Cloud Auth. Without a challenge, a script can brute-force credentials or mass-create accounts against the project's Auth quota. Turnstile moves that gate to the edge: the browser solves a challenge, receives a short-lived token, and Supabase rejects any `signInWithPassword` / `signUp` call that arrives without a valid one.

## The Widget (`apps/web/src/shared/auth/components/TurnstileWidget.tsx`)

`TurnstileWidget` renders a `<div data-testid="turnstile-widget" className="min-h-16">` container and mounts the Turnstile challenge into it with **explicit rendering** (`https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit`), so the script never auto-scans the DOM for `.cf-turnstile` elements.

- **Script loading (`loadTurnstileScript`)** — if `window.turnstile` already exists it calls back immediately; if a `<script src="…api.js?render=explicit">` tag is already in the document it attaches a `load` listener to it instead of injecting a duplicate; otherwise it appends an `async`/`defer` script to `document.head`. The returned cleanup removes the listener.
- **Mount** — `window.turnstile.render(container, { sitekey, theme: 'dark', callback, 'expired-callback', 'error-callback' })` returns a widget id stored in `widgetIdRef`. The mount is guarded by a `cancelled` flag and by `widgetIdRef.current` so a re-render never double-mounts.
- **Token callbacks** — `callback(token)` forwards the token; `expired-callback` and `error-callback` both forward `null`, so an expired or failed challenge clears the token and re-disables the submit button. `onToken` is held in a ref (`onTokenRef`) so a new callback identity never re-runs the mount effect.
- **Reset (`resetKey`)** — a second effect keyed on `[siteKey, resetKey]` calls `onToken(null)` and `window.turnstile.reset(widgetId)` whenever `resetKey` increments past `0`. Turnstile tokens are single-use, so a failed auth attempt must mint a fresh one.
- **Unmount** — the cleanup removes the widget (`window.turnstile.remove(widgetId)`) and nulls the ref.
- **No-op when unset** — `if (!siteKey) return null`, and the mount effect returns early when `siteKey` is falsy or `window` is undefined (SSR).

## Wiring Through the Auth Card

`Auth.tsx` owns the token state:

- `const turnstileSiteKey = import.meta.env.VITE_TURNSTILE_SITE_KEY` and `const [captchaToken, setCaptchaToken] = useState<string | null>(null)`.
- `const captchaPending = Boolean(turnstileSiteKey) && !captchaToken` disables the submit `Button` until a token exists. With no site key configured the button is never disabled by the CAPTCHA.
- A hidden `<input type="hidden" name="captchaToken" value={captchaToken ?? ''} />` carries the token into the `FormData` the parent route reads, so `Login` and `SignupComp` never need a prop for it.
- `<TurnstileWidget siteKey={turnstileSiteKey} resetKey={captchaResetKey} onToken={setCaptchaToken} />` sits directly above the submit button.

## Server-Side Verification

Both auth server functions accept an optional `captchaToken` and forward it to Supabase Cloud Auth, which performs the actual verification:

- **`loginFn`** (`apps/web/src/routes/_authed.tsx`) — `signInWithPassword({ email, password, ...(captchaToken ? { options: { captchaToken } } : {}) })`.
- **`signupFn`** (`apps/web/src/routes/signup.tsx`) — `signUp({ email, password, ...(captchaToken ? { options: { captchaToken } } : {}) })`.

Both trim the incoming value and treat an empty/whitespace string as absent, so a form submitted without a widget sends no `options` object at all rather than an empty token.

## Reset Lifecycle (`captchaResetKey`)

`Login` and `SignupComp` each hold `const [captchaResetKey, setCaptchaResetKey] = useState(0)` and pass it to `Auth`. The key increments on every non-successful outcome so the next attempt starts with a fresh challenge:

- `Login` — `loginMutation.onSuccess` when the result carries an error, `loginMutation.onError`, `signupMutation.onSuccess` when the result carries an error, and `signupMutation.onError`.
- `SignupComp` — `signupMutation.onSuccess` when the result carries an error (after which it `return`s before navigating), and `signupMutation.onError`.

A successful login/signup navigates away instead of resetting, so the token is never spent twice.

## Configuration

| Variable | Scope | Purpose |
| :--- | :--- | :--- |
| `VITE_TURNSTILE_SITE_KEY` | Build + runtime (public) | Cloudflare Turnstile site key. Unset → the widget renders nothing and no CAPTCHA is required. |

The key is documented in `apps/web/.env.example` as `VITE_TURNSTILE_SITE_KEY=<cloudflare_turnstile_site_key>` and added to `SECRETS_SCAN_OMIT_KEYS` in `apps/web/netlify.toml`, because a site key is a public value that legitimately appears in the client bundle and would otherwise trip Netlify's build-time secret scanner (see [[concepts/env-based-secrets]]). The matching secret key lives only in the Supabase Cloud Auth configuration — it is never read by this repository.

## Tests

`apps/web/src/shared/auth/components/TurnstileWidget.test.tsx` covers the contract hermetically (it deletes `window.turnstile` and clears `document.head` in `beforeEach`):

- an empty `siteKey` renders nothing (`container.firstChild === null`);
- with a site key and a stubbed `window.turnstile`, the widget renders `data-testid="turnstile-widget"` and calls `render` exactly once;
- the captured `callback` forwards its token to `onToken`, and `expired-callback` forwards `null`;
- re-rendering with an incremented `resetKey` calls `reset('widget-1')` and emits `onToken(null)`;
- unmounting calls `remove('widget-1')`.

## Related

- [[concepts/auth-redirect-sanitization]] — the return-path sanitizer the auth card shares
- [[concepts/auth-db-client-separation]] — Auth (Supabase Cloud) vs DB (archive) client split
- [[concepts/env-based-secrets]] — the Netlify secret-scanner omit list this key joins
- [[entities/web-app]] — the dashboard hosting the auth routes
