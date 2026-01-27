# Google Authentication Walkthrough

This document describes the implementation of Google Authentication using Supabase OAuth 2.0.

## Implementation Details

### 1. Client-side Supabase Utility
Created `apps/web/src/lib/supabase-client.ts` to provide a Supabase client that works in the browser. This is necessary for triggering the OAuth flow.

### 2. Google Login Button
Modified `apps/web/src/shared/auth/components/Auth.tsx` to include a "Sign in with Google" button. 
- **Tech:** Uses `supabase.auth.signInWithOAuth`.
- **Client Usage:** Uses the **Browser Client** (`getSupabaseBrowserClient`) to trigger the redirect flow from the frontend.
- **Redirect:** Sends users to Google and specifies `/auth/callback` as the return URL.

### 3. Auth Callback Route
Created `apps/web/src/routes/auth.callback.tsx` to handle the session exchange once Google redirects the user back.
- **SSR Support:** Uses a TanStack Start server function (`exchangeCodeFn`) to exchange the temporary code for a permanent session on the server.
- **Cookies:** Authenticated sessions are securely stored in cookies via `@supabase/ssr`.

### 4. Environment Configuration
The system requires both standard and `VITE_` prefixed environment variables in `apps/web/.env`:
- `SUPABASE_URL`: Used by the server-side client.
- `SUPABASE_ANON_KEY`: Used by the server-side client.
- `VITE_SUPABASE_URL`: Exposed to the browser via Vite.
- `VITE_SUPABASE_ANON_KEY`: Exposed to the browser via Vite.

> [!IMPORTANT]
> **Why VITE_?** Vite automatically filters out any environment variables that do not start with `VITE_` when bundling the frontend. This prevents accidental exposure of sensitive backend keys (like `OPENAI_API_KEY`).

> [!NOTE]
> **Safety:** Exposing the `Anon Key` to the frontend is secure because table-level access is controlled by **Postgres Row Level Security (RLS)** policies.

The Google credentials (Client ID and Secret) must be configured in the **Supabase Dashboard** under **Authentication > Providers > Google**.

## How to Test
1. Start the application: `npm run dev --filter web`
2. Navigate to [http://localhost:3000/login](http://localhost:3000/login).
3. Click **"Google"**.
4. Complete the Google sign-in flow.
5. You should be redirected back to the home page and see your email in the header.
