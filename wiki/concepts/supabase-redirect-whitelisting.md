---
tags: [supabase, auth, redirection, setup]
category: concept
---

# Supabase Redirect Whitelisting

Documents how Supabase OAuth (Google SSO) redirects are processed, whitelisted, and resolved across different local development ports and production environments.

## OAuth Redirection Flow

When a user initiates Google SSO, the client application calls `signInWithOAuth()` and passes a `redirectTo` URL. Supabase Auth processes this flow through the following sequence:

1. **OAuth Request**: The browser requests sign-in from the Supabase Auth server, specifying where to return after authentication (e.g., `http://localhost:3000/auth/callback`).
2. **Google Authentication**: Supabase routes the user to Google. The user signs in and is returned to Supabase's authentication server.
3. **Whitelist Validation**: Supabase checks the requested `redirectTo` URL against its whitelisted domains (specifically the **Site URL** and **Additional Redirect URLs**).
4. **Redirection**:
   - **If Whitelisted**: Supabase redirects the browser to the requested URL (e.g., `/auth/callback?code=xxx`) to exchange the code for a session.
   - **If Rejected (Mismatch)**: For security, Supabase rejects the destination and redirects the user to the default **Site URL** configured in the dashboard (appending `?code=xxx` to the root path `/` instead of the callback path).

## Port Mismatch (Netlify Dev vs Vite)

This project has two distinct ports used during local development:

*   **Vite Server (Port 3005)**: The raw Vite dev server runs at `http://localhost:3005` as configured in `vite.config.ts`.
*   **Netlify Dev Proxy (Port 3000)**: Netlify CLI starts a local proxy at `http://localhost:3000` (defined in `netlify.toml`) which forwards requests to Vite.

Because the browser visits `http://localhost:3000` when running under Netlify Dev, the frontend dynamically requests `http://localhost:3000/auth/callback` as its redirect URL. If testing Vite directly, it requests `http://localhost:3005/auth/callback`.

## The Mismatch Fallback Symptom

If a user lands on `http://localhost:3000/?code=xxx` (the home page) instead of `http://localhost:3000/auth/callback?code=xxx` and remains logged out, this indicates:
1. The requested redirect URL (`/auth/callback`) was rejected by Supabase.
2. Supabase fell back to the default **Site URL** (which was set to `http://localhost:3000`), appending `?code=xxx` to the root path.
3. Because the user landed on `/` instead of `/auth/callback`, the router never invoked the server function to exchange the auth code for a session.

## Configuration Checklists

To prevent redirect fallbacks, the active Supabase project's URL configuration must align with the environment:

### Local Development Setup

When testing locally (using either a local Supabase CLI instance or a remote development instance), configure **Auth > URL Configuration** in the dashboard as follows:

1.  **Site URL**: `http://localhost:3000` (if using Netlify Dev) or `http://localhost:3005` (if using direct Vite).
2.  **Additional Redirect URLs**:
    - `http://localhost:3000/auth/callback`
    - `http://localhost:3005/auth/callback`
    - `http://localhost:3005/**` (or use wildcard patterns)

*Note: For local Supabase CLI instances (`supabase start`), these settings are managed in `supabase/config.toml` under `[auth]` (`site_url` and `additional_redirect_urls`).*

### Production Deployment Setup

When deploying to the live Netlify site:

1.  **Site URL**: `https://benchify.netlify.app`
2.  **Additional Redirect URLs**:
    - `https://benchify.netlify.app/auth/callback`
    - `http://localhost:3000/auth/callback` (keeps local dev working on the same project if shared)

## Related

- [[entities/web-app]]
- [[entities/database]]
- [[sources/web-deployment-source]]
