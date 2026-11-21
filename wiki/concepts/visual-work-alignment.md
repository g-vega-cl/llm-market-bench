---
tags: [process, design, visualization, webgl, delegation, verification, lessons]
category: concept
---

# Artistic Work Needs Vision Alignment First

A postmortem of the homepage playground build (2026-11-20 → 2026-11-21): a five-block
bot builder, a WebGL voxel market world, two SQL contracts, and five review agents.
The code was verified, reviewed, migrated, committed — and then reverted in full,
because the centrepiece looked wrong to the only person whose eyes mattered.

## The lesson that outranks the rest

**A visual or artistic deliverable cannot be approved by anyone but the human who
will look at it.** The world was built from a description, "verified" in a headless
browser, and shipped to the homepage. The human's verdict on first sight was
immediate and total. Nothing in the process could have caught it, because no step
in the process involved a human looking at the thing.

Rules that follow, and that apply to any 3D scene, generated artwork, illustration,
chart styling, or animation:

1. **Static before motion.** Produce one frame — a rendered still, a screenshot, a
   hand-drawn composition — and get explicit approval of its *look* before writing
   animation, camera, or interaction code. The still is cheap; the loop is not.
2. **One visual change per review cycle.** Never batch a palette change, a framing
   change and a perspective change into one "looks better now" claim. The human
   cannot tell you which one broke it, and neither can you.
3. **Never infer approval from silence or from automated checks.** A passing gate
   says the code runs. It says nothing about whether the result is any good.
4. **Headless rendering is not looking.** A headless browser proved the canvas had a
   GL context, a compiled program, and no error. It could not see the scene. At one
   point it was reported as "renders nothing" when a DOM sibling was simply painting
   over it — a wrong diagnosis of a visual failure, from a tool that cannot perceive.
5. **Budget the human's attention, not just the tokens.** Ask for the look check at
   the moment a rough shape exists, not after the polish is finished, and not in the
   last five minutes of a long session.

The correct sequence for the world would have been: a single isometric still with
real colours and real spacing → "is this the feeling?" → only then voxel geometry,
idle loop, pointer parallax, and fallback band.

## Verification lessons

- **Verify a reported defect before fixing it.** A reviewer's "P1 ordering bug" did
  not exist; the client-side assertion that produced it was wrong and the engine
  deliberately normalises block order. Reading the two files took a minute; acting on
  the claim would have added a false rule to a contract.
- **Volume is not authority.** Five agents produced ~40 findings. Some were excellent
  (a capped launch being replayed all day, a live bot created before the cap check),
  and none of them noticed the thing the human saw in one second.
- **Tests must assert observable outcomes.** A `disabled` prop computed independently
  of the guard it protects, and a `className` substring, both stay green under a real
  regression. Assert the effect, not the flag.
- **Enumerate every state.** A launch had five UI outcomes and three reachable ones;
  the unreachable ones hid a contract mismatch for an entire review cycle.

## Scope lessons

- **One contract, one place.** The graph rules lived in four places with three
  different rule sets; the quota predicate in two; the tier limits in two. Every
  drift in this feature traced back to a duplicated rule.
- **Large refactors need their own session.** Eight workstreams in one turn produced
  a tree that could not be finished or verified, only reverted.
- **Check where the data actually lives.** Tables were reported as "cloud" after
  querying the default `postgres` database instead of `market_bench_archive`; the
  human had to correct it.
- **Logical replication does not carry DDL.** The MiniPC replica was assumed synced
  because a probe was read as success. It was verified object by object only during
  the revert, and had never received anything.
- **Copy is a contract.** "Limits reset daily" over a rolling 24-hour window is a
  lie the SQL should not have permitted.

## Rule of thumb

If the deliverable is something a person will *look at* rather than *read*, the first
review gate is a human eye on a static artifact. Everything else — tests, agents,
builds, migrations — is downstream of that gate, not a substitute for it.
