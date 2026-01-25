# Web Application Architecture: AI Wall Street Dashboard

The frontend of AI Wall Street is a high-performance, type-safe web application built with **TanStack Start**. It provides real-time visualization of LLM trading performance, portfolio metrics, and the decision attribution trail.

## 1. Tech Stack

| Component | Technology |
| --- | --- |
| **Framework** | [TanStack Start](https://tanstack.com/start) (React 19 + Vite) |
| **Routing** | [TanStack Router](https://tanstack.com/router) (File-based) |
| **Styling** | [Tailwind CSS 4](https://tailwindcss.com/) |
| **Data Fetching** | [TanStack Query](https://tanstack.com/query) |
| **Backend** | [Supabase](https://supabase.com/) (Auth, Postgres, Real-time) |
| **Language** | TypeScript |

## 2. Project Structure

```text
apps/web/
├── src/
│   ├── components/      # UI components (DashboardCards, Charts, etc.)
│   ├── routes/          # File-based routing (____root.tsx, index.tsx, etc.)
│   ├── styles/          # Global CSS and Tailwind configuration
│   ├── utils/           # Supabase client, SEO helpers, and API functions
│   ├── hooks/           # Custom React hooks for data fetching
│   ├── router.tsx       # Router configuration
│   └── routeTree.gen.ts # Automatically generated route tree
└── vite.config.ts       # Vite and TanStack Start configuration
```

## 3. Core Architectural Concepts

### File-Based Routing
We use **TanStack Router's** file-based routing system. Routes are defined in `src/routes`:
*   `__root.tsx`: The layout wrapper, handling global state and the navigation bar.
*   `_authed.tsx`: A layout group for routes requiring authentication.
*   `index.tsx`: The main landing page.
*   `login.tsx`, `signup.tsx`, `logout.tsx`: Authentication flows.

### Full-Stack Integration (TanStack Start)
TanStack Start allows us to define "Server Functions" for secure backend operations.
*   **Authentication Check:** Performed in `__root.tsx` using `beforeLoad` to ensure user sessions are valid before rendering protected content.
*   **SSR & Hydration:** The application is server-side rendered for SEO and performance, then hydrated on the client for full interactivity.

### Supabase Integration
We use `@supabase/ssr` to manage session consistency between the server and client.
*   **Server Client:** Configured in `src/utils/supabase.ts` for handling Cookies, SSR, and Server Functions.
*   **Browser Client:** Configured in `src/utils/supabase-client.ts` for handling client-side events like OAuth redirects.
*   **Environment Variables:** Uses `VITE_` prefixing for browser-exposed variables to comply with Vite's security model.
*   **Row Level Security (RLS):** Ensures that users can only access their own data and public performance metrics.

## 4. State Management

*   **Server State:** Managed by **TanStack Query**. It handles caching, background refetching, and synchronization with our Supabase database.
*   **Routing State:** Managed by **TanStack Router**, providing type-safe navigation and URL-driven state.

## 5. Development Guide

### Local Setup
1.  Ensure you have `pnpm` installed.
2.  Install dependencies from the root: `pnpm install`.
3.  Configure `.env` in `apps/web/.env` (see `Overview.md` for required keys).
4.  Run the development server: `pnpm --filter web dev`.

### Design System
We follow a "Rich Aesthetics" approach using Tailwind CSS 4. Focus on:
*   Vibrant HSL-tailored colors.
*   Glassmorphism effects for dashboard cards.
*   Subtle micro-animations for interactive elements.
