---
tags: [entity, web, dashboard, frontend]
category: entity
---

# Web App

TanStack Start dashboard (React + TypeScript) providing real-time portfolio data, trade audit trails, and LLM cognitive synthesis. The frontend is organized into vertical feature slices.

## Key Features

- **Daily Predictions Page** (`/daily-predictions`): Independent model tabs (DeepSeek Flash, MiniMax M3) with strict track isolation. The `resolveActiveDailyPrompt` function now only considers experiments filtered to the selected model — no cross-track fallback. The `allExperiments` prop and `isFallback` flag have been removed. Status badges: `active` status only shows `🟢 ACTIVE` for the single active variant; other `active` records display `📦 SAVED`. The Autoresearch view defaults to inspecting the current active variant.
- **Autoresearch Milestone Cards**: Shows active ratchet score, best baseline score, delta, and baseline anchor status. No fallback indicator.
- **Variant Sidebar**: Lists all experiments for the selected model with status badges (`🟢 ACTIVE`, `🏆 BASELINE`, `❌ DISCARDED`, `📦 SAVED`).

## Architecture

- Built with TanStack Start (React Router v7, SSR).
- Uses TanStack Query for data fetching with SSR-safe QueryClient.
- Styled with Tailwind CSS and a custom design system.

## Related

- [[entities/daily-market-predictor]]
- [[concepts/multi-track-autoresearch]]
- [[concepts/tanstack-query]]
- [[concepts/type-safety]]
