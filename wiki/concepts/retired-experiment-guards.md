---
tags: [web, posthog, experiments, cleanup, guardrails, tests]
category: concept
---

# Retired Experiment Guards

Retired experiment guards are source-tree tests that keep deleted experiment code and feature-flag reads from being reintroduced. The first instance protects the retired `homepage-bg-experiment` PostHog experiment (376759) and the removed `ShaderBackground` WebGL component. The active homepage backdrop is [[entities/global-background]], so the experiment no longer has an owner.

## Current State

apps/web/src/components/ui/ShaderBackground.tsx and its unit test are deleted. `apps/web/src/features/home/pages/HomePage.test.tsx` no longer mocks `usePostHog`, because no source file under `apps/web/src` should read the `homepage-bg-experiment` flag or reference the `ShaderBackground` symbol.

## Guard Implementation

`apps/web/src/test/retired-experiments.test.ts` recursively walks `.ts` and `.tsx` files under `apps/web/src`, excluding itself, and fails when any retired token appears. It also asserts that apps/web/src/components/ui/ShaderBackground.tsx does not exist.

Retired tokens:

- `homepage-bg-experiment` — PostHog flag associated with the WebGL homepage backgrounds; `GlobalBackground` is the current backdrop owner
- `ShaderBackground` — deleted full-screen WebGL canvas component

The guard excludes itself so its own token list does not fail the scan.

## Why This Exists

Deleting code is only half of experiment retirement. Without a guard, a stale flag read, copied component, or partial revert can revive an experiment that no longer has an owner. The guard makes retirement explicit in the test suite while leaving the active background architecture unambiguous.

## Related

- [[entities/global-background]] — current homepage backdrop owner
- [[concepts/living-scene-backdrops]] — current living background architecture for page backdrops
- [[concepts/posthog-stealth-proxy]] — PostHog integration context
- [[concepts/design-variant-budget]] — design-variant governance
