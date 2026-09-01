---
tags: [deployment, release, canary, posthog, feature-flags, netlify, ssr]
category: concept
---

# Release and Canary Deployments

Architecture, paradigms, and operational playbook for decoupling deployment from release across the web application and engine pipelines.

## The Decoupling Principle

- **Deployment**: Moving built assets and server code into production infrastructure (Netlify CDN, edge functions, Supabase migrations).
- **Release**: Making new features or code paths active and visible to end users.

Coupling deployment directly to release forces teams into high-stakes, stressful deployments where every Git merge immediately impacts 100% of users. Decoupling deployment from release allows continuous deployment (CD) to `main` at high frequency while managing user exposure independently.

```mermaid
flowchart TD
    subgraph Pipeline [Continuous Deployment & Release Pipeline]
        PR[Pull Request] --> DP[Netlify Deploy Preview (Pre-merge QA)]
        DP --> Merge[Merge to main]
        Merge --> Atomic[Atomic CDN Deployment (Blue/Green)]
        
        Atomic --> RiskCheck{Is change high-risk or incomplete epic?}
        RiskCheck -->|No: 90% of PRs| Direct[100% Immediate Release]
        RiskCheck -->|Yes: 10% of PRs| Canary[PostHog Canary Flag (0% Base)]
        
        Canary --> Stage1[Stage 1: Internal Testing (user.email = team)]
        Stage1 --> Stage2[Stage 2: 10% Canary (Telemetry & Error Audit)]
        Stage2 --> Stage3[Stage 3: 100% Full Rollout]
        Stage3 --> Cleanup[Stage 4: Flag Cleanup PR (≤ 14 days)]
    end
```

---

## Architectural Paradigms & Anti-Patterns

### 1. The Global Timed Gate Anti-Pattern
Attempting to put a single, global 0% $\to$ 100% percentage gate across the entire application fails for two reasons:
1. **Concurrency Collisions**: If Developer A merges Feature 1 (rolling out 0% $\to$ 100% over 4 hours) and Developer B merges Feature 2 two hours later, Feature 2 either instantly exposes untested code to 50% of users or resets the global gate to 0%, downgrading Feature 1's active users.
2. **SPA Chunk Mismatch**: Single Page Applications rely on content-hashed chunks (`index-[hash].js`). A fluctuating global percentage gate without persistent session affinity causes users navigating routes to load new HTML against old cached bundles, triggering `ChunkLoadError` exceptions.

### 2. The Universal Feature Flag Anti-Pattern
Wrapping *every* commit in a feature flag creates unsustainable technical debt:
- Multiplies runtime branching (`if (flag) ... else ...`).
- Leads to a combinatorial testing explosion ($2^N$ possible application states).
- Slows client initialization and burdens PostHog evaluation payloads.

### 3. The Recommended Pattern: Trunk-Based CD + Selective Canary Flags
- **90% Routine Work** (bug fixes, small UI updates, performance optimizations, utility functions) deploys directly to `main` with 100% release, guarded by pre-commit linters (`ruff`, `biome`), high unit test coverage (70% engine, 40% web), and Netlify Deploy Previews.
- **10% High-Risk Work** (payment/checkout flows, algorithmic changes, breaking UI redesigns, multi-PR dark launches) is guarded by short-lived PostHog feature flags.

---

## SDK Boundaries: `@posthog/react` vs `posthog-node`

The project utilizes two distinct PostHog SDKs partitioned strictly by execution environment:

| Attribute | `@posthog/react` (Client) | `posthog-node` (Server) |
| :--- | :--- | :--- |
| **Execution Environment** | Browser DOM / React runtime | Node.js / TanStack Start server / Netlify Functions |
| **Configuration File** | Mounted in `apps/web/src/routes/__root.tsx` | Exported via `apps/web/src/utils/posthog-server.ts` |
| **Primary Capabilities** | Pageviews, UI click autocapture, `useFeatureFlagEnabled` | Backend event tracking, cron job telemetry, SSR flag pre-evaluation |
| **Identity Persistence** | Browser cookie (`ph_<token>_posthog`) + `localStorage` | Stateless (requires explicit `distinct_id` per invocation) |

---

## Client-Side Canary Implementation

For standard UI components, feature flags are evaluated in the browser using the `@posthog/react` hook.

```tsx
import { useFeatureFlagEnabled } from '@posthog/react';

export function MarketAnalysisWidget() {
    const isAdvancedModelEnabled = useFeatureFlagEnabled('v2-deep-reasoning');

    if (isAdvancedModelEnabled) {
        return <AdvancedReasoningView />;
    }

    return <StandardReasoningView />;
}
```

### Identity & Persistence
When a user logs in or signs up, `posthog.identify(user.email)` writes the user's distinct identity into PostHog's persistent browser cookie and local storage. On subsequent visits and page reloads on that device, PostHog reads the cookie synchronously, maintaining user targeting without requiring client-side re-identification effects.

---

## Zero-Flicker Server-Side Rendering (SSR)

When a feature flag dictates top-level layout or initial page markup, evaluating flags client-side can cause a brief visual flash (flash of unflagged content) while the browser fetches flags from PostHog.

To achieve zero-flicker SSR with TanStack Start:

1. **Evaluate on Server**: Use `getPostHogClient()` in a server function or `Route.beforeLoad`.
2. **Bootstrap to Client**: Pass the resolved flags into the root `<PostHogProvider>` via `options.bootstrap`.

```tsx
// Server-side loader (TanStack Start)
import { createServerFn } from '@tanstack/react-start';
import { getPostHogClient } from '~/utils/posthog-server';

export const fetchFeatureFlags = createServerFn({ method: 'GET' }).handler(async () => {
    const user = await getCurrentUser();
    const posthog = getPostHogClient();
    
    const flags = await posthog.getAllFlags(user?.email || 'anonymous');
    return { flags };
});
```

```tsx
// Root component initialization
<PostHogProvider
    apiKey={import.meta.env.VITE_PUBLIC_POSTHOG_PROJECT_TOKEN}
    options={{
        api_host: '/p',
        bootstrap: {
            distinctId: user?.email,
            featureFlags: serverFlags,
        },
    }}
>
    {children}
</PostHogProvider>
```

---

## 4-Step Canary Release Lifecycle

1. **Step 1: Code Behind Flag**
   - Wrap risky logic in `useFeatureFlagEnabled('flag-name')` or server-side check.
   - Create flag in PostHog dashboard with default state: **0% (Disabled)**.
2. **Step 2: Dark Deploy to `main`**
   - Merge PR to `main`. Netlify performs an atomic deployment. The code is in production but inactive for all users.
3. **Step 3: PostHog Phased Rollout**
   - **Stage 3a (Dogfooding)**: Add release condition `email = your_team@domain.com`. Test directly in production.
   - **Stage 3b (Canary)**: Set rollout to **10%–25% of users**. Monitor error captures, session recordings, and performance metrics.
   - **Stage 3c (Full Release)**: Set rollout to **100% of users**.
4. **Step 4: Cleanup Chore PR**
   - Once stable at 100% for 7–14 days, submit a cleanup PR removing the `useFeatureFlagEnabled` conditional and deleting the legacy code branch.
   - Archive/delete the feature flag in PostHog.

---

## Related

- [[entities/web-app]] — TanStack Start dashboard and client router
- [[concepts/posthog-stealth-proxy]] — Same-origin reverse proxy architecture for ad-blocker immunity
- [[concepts/rendering-strategies]] — SSR, Hybrid SSR, and CSR rendering patterns
- [[concepts/agent-workflow]] — Mandatory TDD and test verification sequence
