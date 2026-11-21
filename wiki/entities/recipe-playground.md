---
tags: [reverted, playground, webgl, homepage, postmortem]
category: entity
---

# Recipe Playground (reverted)

> **Status: removed.** This entity shipped on 2026-11-20 in commit `f4b5e721` and was
> reverted in full the next day, including its two database migrations. Pages that
> still link here describe code that no longer exists. The reason, and the process
> rules that came out of it, are in [[concepts/visual-work-alignment]].

## What it was

A replacement homepage where a visitor assembled a five-block bot (universe, filter,
think, answer, and an output format), pressed RUN, and got a backtest queued through an
atomic `launch_recipe` RPC. The centrepiece was a WebGL voxel "market world" — an
isometric field of bars coloured by the day's mood — intended as the launch gate.

The database work was real and reviewed: an advisory-locked idempotency ledger
(`recipe_launch_requests`), nullable per-tier quota overrides on `recipe_user_quotas`,
and a `run_requests` table for asking for more runs. All of it is gone from
`market_bench_archive`; nothing was ever applied to the MiniPC replica, since logical
replication does not carry DDL.

## Why it was reverted

The world looked wrong. Not broken — verified, tested, and rendering — but wrong as a
piece of design, and the first person to see it on a real screen rejected it outright.
No amount of type-checking, coverage or review could have found that, because at no
point in the build did a human look at a still frame and say whether the direction was
right.

## What survives

- The lesson: [[concepts/visual-work-alignment]].
- The commit, on the local branch `backup/playground-2026-11-21` until someone deletes it.
- The review findings, in `.hermes/plans/2026-11-21-playground-refactor.md` (untracked).

## If this is ever rebuilt

Render one still first. Get a human verdict on the composition, the palette and the
sense of depth before any animation exists. Then build geometry, then motion, then
fallbacks, one reviewable change at a time.
