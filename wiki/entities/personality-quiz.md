---
tags: [web, personality, quiz, archetypes, recipes, diagnostic]
category: entity
---

# Investing Style Diagnostic (`/personality`)

A **16-question** investing-personality diagnostic, played in four acts of four, that scores a visitor across four behavioural axes, resolves them into one of **16 fixed-order four-letter type codes**, and maps that code to an investing archetype and its starter trading recipe. It is the discovery funnel that turns "I don't know what kind of trader I am" into "here is a bot I can build", linking straight into `/build` and `/recipes`.

> **Grid status:** complete. All 16 cells own an archetype and a starter recipe, the result panel and recipe studio both render the shared 4x4 `TypeCodeGrid`, and the rule-metric vocabulary is validated at load (`RULE_METRIC_LABELS`).

The route lives at `apps/web/src/routes/personality.tsx` and renders `PersonalityQuizPage` (`apps/web/src/features/personality/PersonalityQuizPage.tsx`) on a design-system `SceneStage` (`variant="hero"`, `motionRole="reactive"`) backed by the panoramic **Cedar Sanctuary** [[concepts/living-scene-backdrops]] diorama and an SSR-resolved `initialAtmosphere` from the route `loader` to eliminate SSR/CSR visual flashes ([[concepts/cumulative-layout-shift]]).

The page carries **no visible headline block** — no eyebrow, page title or description precedes the first question, because that copy pushed Act 1 down ~143 px and made the page read as a landing page instead of a test. The first question card starts directly under the scene's top padding (110 px card top at 1600×1000), and the accessible name comes from the route `<title>` plus an `sr-only` `<h1>` ("Investing style diagnostic: discover your best trading bot").

## Route & Search Params

`validateSearch` accepts a single optional `archetype` key and normalizes anything unrecognized to `undefined`:

```ts
validateSearch: (search: Record<string, unknown>): { archetype?: ArchetypeId } => ({
    archetype: isValidArchetypeId(search.archetype) ? search.archetype : undefined,
})
```

The route `loader` resolves `initialAtmosphere: resolveAtmospherePhase(new Date(), 'market-et')` synchronously on the server so hydration matches SSR on first byte with zero layout or atmosphere shift.

`/personality/t/<CODE>` opens the page directly in **inspect** mode for that type (shareable result links); a bare `/personality` starts the quiz at question 1. Legacy `/personality?archetype=<id>` links resolve the slug to its code and `replace`-navigate to the canonical path. The route head declares the title `Investing Style & Best Trading Bot Quiz | Benchify` plus a description naming the four axes.

The homepage links here from the `Take the investing style test` button (`data-testid="take-personality-test"`) inside `home-cta-actions`, and `/lab` lists it as **Investing Style Diagnostic** under `Research & Prediction Engines`.

## The 16-Question Diagnostic (4 acts of 4)

`PERSONALITY_QUESTIONS` (`apps/web/src/features/personality/questions/index.ts`) assembles four per-act arrays — `HORIZON_QUESTIONS`, `SIGNAL_QUESTIONS`, `CONTRARIAN_QUESTIONS`, `CADENCE_QUESTIONS`, one file each under `apps/web/src/features/personality/questions/` — into exactly 16 `QuizQuestion` objects. Each question carries an `id`, an `act` (the axis it primarily probes), a `prompt`, a short `context` label, and exactly four `QuizOption`s with a `label`, a `detail` sentence, and a `deltas` map of signed contributions.

The delta matrix is designed, not handwritten-by-feel:

- **Target loading** — the act axis carries `±14` / `±5` on the four options while cross-loadings stay `<= 4`; the letter is derived from the act's own probes, so cross-loadings can shape the readout but never decide a letter.
- **Symmetry** — every axis's four option deltas are symmetric about zero on every question, which keeps the normalized midpoint a true `50` and the 16 cells near-uniform.
- **Rotation** — half the questions present the high pole first so the low-pole instinct is not always option A.

`QUIZ_ACTS` supplies the four chapter headings (Patience & Horizon, Signal Anchor, Crowd Stance, Execution Tempo) plus a one-line blurb each. The scenarios walk an arc: an opening-bell tariff shock, an empty tape, a thesis that is early, holding period, a single data stream, an unverified headline, conflicting guidance, edge source, a euphoric winner, a panic flush, a crowded narrative, a stop rule, slot count, gate discipline, idle capital, and review rhythm.

## 4-Axis Scoring

`PERSONALITY_AXES` is `['horizon', 'signal', 'contrarian', 'cadence']`, described by `AXIS_DEFINITIONS`:

| Axis | Label | Low end | High end |
| :--- | :--- | :--- | :--- |
| `horizon` | Patience & Horizon | Session Swings | Multi-Quarter Thesis |
| `signal` | Signal Anchor | Balance Sheet & Value | Live Headlines & Catalysts |
| `contrarian` | Crowd Stance | Ride Trend Confirmation | Fade Panic & Euphoria |
| `cadence` | Execution Tempo | Selective Patience | Active Rotation |

`scorePersonalityQuiz(answers)` (`personality-data.ts`) runs three pure stages:

1. **`accumulateAxisTotals`** — sums the chosen option's `deltas` per axis into `rawSum`, and simultaneously accumulates each answered question's own `minBound` / `maxBound` (the minimum and maximum delta any option on that question offers for that axis). This makes the normalization self-calibrating: a question that only offers positive `signal` deltas cannot drag the profile upward just because it was asked.
2. **`normalizeAxisProfile`** — `norm = ((rawSum − minBound) / (maxBound − minBound)) × 100`, rounded and clamped to `0..100`. A zero span or zero answered questions leaves the axis at the neutral `50`.
3. **`rankArchetypesForProfile`** — Euclidean distance in 4-axis space, `distance = sqrt(Σ(profile − idealProfile)² / 4)`, then `fitPercent = round(clamp(100 − distance × 0.95, 18, 99))`. Ties break by `ARCHETYPE_IDS` declaration order.

`QuizScoreResult` is `{ profile, primary, runnerUp, rankings, answeredCount, code, letters, neighbour }`. Because scoring is pure and cheap, the page recomputes it on every render — the live `Leaning: <code>` hint updates after each answer without any extra state.

### Type code, strength and neighbour

`personality-type-grid.ts` owns the letter layer. `TYPE_SLOT_ORDER` is fixed — horizon, signal, stance, tempo — so codes are comparable between people and stable in share URLs. Poles are `L`/`Q` (long thesis / quick swing), `V`/`N` (value sheet / news flow), `M`/`F` (momentum / fade), `P`/`R` (patient / rotating), giving `TYPE_CODES` of 16 codes from `LVFP` to `QNMR`.

- **Letter** = the act's own probes: `letterFromProbes` sums the four dedicated probes' deltas on that axis and takes the sign. Cross-loadings from the other twelve questions shape the 4-axis readout but can never outvote the questions actually asked about that axis (regression-tested). An exact 0 tie falls back to the pooled profile.
- **Strength** = count, and counts only that act's four probes: 4–0 `clear`, 3–1 `moderate`, 2–2 `slight`. A magnitude that contradicts the vote count is reported as `slight` rather than papered over.
- **Toss-up** = the axis value sits within `±2` of the boundary, which the result copy renders as a named toss-up instead of a false certainty.
- **Neighbour** = `neighbourForProfile` flips the weakest letter (smallest distance from 50, ties broken in slot order) to name the adjacent cell, replacing the old distance-based runner-up hook.

`TYPE_GRID` (`personality-archetypes.ts`) joins every code to a corner centroid (`88` high / `12` low) and, where one exists, the archetype that owns it.

## Archetype → Starter Recipe Mapping

`ARCHETYPES` is a `Record<ArchetypeId, InvestingArchetype>` with a strict 1:1 mapping between archetype and starter recipe in `packages/config/starter-recipes.json`. The mapping is validated eagerly at module load — a missing starter recipe throws `Archetype "<id>" references missing starter recipe "<name>"` before any component renders.

| Archetype id | Code | Title | Starter recipe |
| :--- | :--- | :--- | :--- |
| `value-compounder` | `LVFP` | The Patient Compounder | `Quality Value Screener` |
| `value-rotator` | `LVFR` | The Value Rotator | `Value Pullback Rotator` |
| `compound-buyer` | `LVMP` | The Compounder Buyer | `Patient Compound Accumulator` |
| `quality-rotator` | `LVMR` | The Quality Rotator | `Quality Momentum Rotator` |
| `contrarian-diver` | `LNFP` | The Contrarian Diver | `Contrarian Sentiment Fader` |
| `systems-architect` | `LNFR` | The Thesis Auditor | `Claude Agent Portfolio Mirror` |
| `catalyst-holder` | `LNMP` | The Catalyst Holder | `Catalyst Hold Sleeve` |
| `catalyst-quant` | `LNMR` | The Catalyst Quant | `Earnings Catalyst Hunter` |
| `bargain-snapper` | `QVFP` | The Bargain Snapper | `Deep Value Snapback` |
| `deep-value-trader` | `QVFR` | The Deep-Value Trader | `Cheap Tape Rotator` |
| `value-scalper` | `QVMP` | The Value Scalper | `Fundamental Momentum Scalper` |
| `multiple-rotator` | `QVMR` | The Multiple Rotator | `Multiple Re-Rating Rotator` |
| `headline-fader` | `QNFP` | The Headline Fader | `Headline Panic Fader` |
| `news-contrarian` | `QNFR` | The News Contrarian | `Fast News Contrarian` |
| `print-trader` | `QNMP` | The Print Trader | `Print Window Scalper` |
| `news-surfer` | `QNMR` | The Headline Surfer | `Trump & Chips News Momentum` |

Codes are unique and the whole grid is validated at module load by `assertValidArchetypeGrid()`: every id has a record, every code is claimed exactly once, every `TYPE_CODES` entry has an owner, and every archetype names a real starter recipe. `systems-architect` keeps its slug for shared links; its title moved to **The Thesis Auditor** because the 16-cell grid has no balanced middle, and its described behaviour (auditing every slot) is high tempo.

Rule metrics are restricted to `RULE_METRIC_LABELS` — RSI, MACD, RVOL, Price vs VWAP, price_52w_pct, P/E, FCF, ROE, market_cap, beta — enforced by `assertKnownRuleMetrics()` inside `validateStrategy`. Without it the field is free-form prose the model can never satisfy, because the indicator is simply absent from every curated tool's output.

Each archetype also carries a `tagline`, a balanced `summary`, three `strengths`, a `watchout`, an `idealProfile` (its 4-axis centroid), and a `builderIdeaPrompt` — a plain-English bot description passed to `/build` as the `idea` search param so the visitor lands in the builder with a pre-filled prompt.

Two pure helpers derive all starter bot technical details directly from `packages/config/starter-recipes.json` with zero duplicated metadata:

- `formatRecipeExecutionSpec(recipe)` formats `News <N>h`, `Memory <N>h`, and every `Rules:` predicate (`metric + operator + target`, plus `News Off` when omitted).
- `summarizeRecipeCoreGate(recipe)` emits a `<= 14`-char badge token so mobile (`360px`) cards never wrap inside a badge.

`buildSharedArchetypeResult(archetypeId)` produces a result directly from an archetype's `idealProfile` with `fitPercent: 98` on the primary match, which is what an `?archetype=` deep link renders.

## Session State Machine

`QuizSession` (registered in [[concepts/state-machines]]) is a strict discriminated union preserving finished quiz answers across inspections while eliminating unrepresentable `null`/`null` states:

```ts
type QuizSession =
    | { phase: 'answering'; stepIndex: number; answers: Record<string, string> }
    | { phase: 'result'; mode: 'quiz_match'; quizAnswers: Record<string, string> }
    | { phase: 'result'; mode: 'inspect'; archetypeId: ArchetypeId; quizAnswers: Record<string, string> | null };
```

`createInitialSession(initialArchetype)` returns `{ phase: 'result', mode: 'inspect', archetypeId: initialArchetype, quizAnswers: null }` when a valid archetype is supplied, otherwise `answering` at step 0. `/personality` wires `Route.useNavigate()` via `onArchetypeSearchChange` (replacing `window.history.replaceState` split-brain), and FIFO `pendingSelfSearchesRef` ensures pipelined router propagation of self-emitted `?archetype=` updates never wipes `quizAnswers`, while external navigation into or back to bare `/personality` re-seeds `session`.

Selecting the last option calls `scorePersonalityQuiz`, updates the `?archetype=` search param, and transitions to `mode: 'quiz_match'`. `handleInspectArchetype` writes the param and sets `mode: 'inspect'` (or returns directly to `mode: 'quiz_match'` when clicking your own matched archetype), preserving `quizAnswers` for `Back to my quiz match`. Clipboard feedback updates `copiedArchetype` only when `activeResultArchetypeRef` (synced in `useEffect`) matches.

## Result Panel & Zero-CLS Switcher Architecture

`PersonalityResultPanel` renders inside a single `.scene-scrim .voxel-card` plaque (`data-testid="personality-result"`) whose children are recessed `Card variant="outlined"` / `.voxel-trough` surfaces using intrinsic vertical flow (`h-full flex flex-col justify-between`) — zero nested `.voxel-card`, zero explicit media breakpoints, and zero scrollbars, per `.agents/rules/design-spec.md`.

- **Top-anchored Archetype switcher** (`data-testid="archetype-switcher"`) — pinned at the top of `PersonalityResultPanel`, one button per `ARCHETYPE_IDS` entry labelled with `arch.title`, active one solid accent (`aria-pressed`), maintaining an invariant 5-button strip across every inspection click.
- **Header & Meta Actions** — displays the `N% style fit` badge alongside wrap-safe `Best Bot: <recipeName>` (`data-testid="header-best-bot"`), paired with `Back to my quiz match` (`data-testid="return-to-quiz-match"` when inspecting an alternate style), `Share link` / `Link copied`, and `Retake 10Q quiz` (`data-testid="retake-quiz"`).
- **4-Axis Diagnostic Profile & Edge/Blind Spot** — paired in a responsive 2-column `items-stretch` grid covering four `flex-wrap min-w-0` axis rows (`N/100` + `whitespace-nowrap` pole labels) and the archetype's three strengths + `watchout`.
- **Top-2 Matched Trading Bots** — `#1 Best Bot Match` and `#2 Runner-Up Match` cards (`BotRecommendationCard`), each showing `match.recipe.name`, canonical `match.recipe.description`, the derived `formatRecipeExecutionSpec(match.recipe)` trough, a 3-stat badge strip (`Backtest: <cadence>`, `N live tools`, `summarizeRecipeCoreGate(match.recipe)`), plus `Build this bot` (`/build?idea=<builderIdeaPrompt>`) and `Open Recipe Studio` (`/recipes`) links.

## Components

- `PersonalityQuizPage.tsx` — non-destructive `'quiz_match' | 'inspect'` state machine, router-synced search params, race-guarded clipboard handling, and `Cedar Sanctuary` stage composition (`text-sm font-bold` + `text-xs font-normal`, no visible `h1` — an `sr-only` heading carries the page name).
- `PersonalityQuizStep.tsx` — single-question card (`data-testid="personality-quiz-card"`) with an `Act N of 4` badge, the act title, a four-pip act track (`data-testid="quiz-act-track"`), the `Question NN / 16` counter with its scenario label, `quiz-live-world-hint`, an accessible `role="progressbar"`, four full-width option buttons inheriting `text-voxel-trough` contrast on `bg-accent` selection, `Previous question`, and `Browse all 16 types`.
- `PersonalityResultPanel.tsx` — the result plaque: 4x4 `TypeCodeGrid` at the top, code/title/summary header, 4-axis readout annotated with each letter, one matched bot card, and the **one-letter-away neighbour** trough (`data-testid="neighbour-type"`) that replaces the old distance-based runner-up.
- `apps/web/src/components/ui/TypeCodeGrid.tsx` — shared 4x4 code grid (16 cells, row/column headers, `aria-pressed` active cell, in-flow description). Used by the result panel and by `TemplatePickerBar`, so the recipe studio's template picker shows codes instead of sixteen full-name buttons.
- `personality-data.ts` — scoring (`profileFromAnswers`, `scorePersonalityQuiz`, `lettersForAnswers`), ranking, share-result builder, and the eager archetype-code + recipe-integrity checks; re-exports the whole public surface.
- `personality-axes.ts` — the four axes, `AxisProfile`, `AXIS_DEFINITIONS`.
- `personality-type-grid.ts` — letters, `TYPE_CODES`, centroids, `codeFromProfile`, `neighbourForProfile`, `isValidTypeCode`.
- `personality-archetypes.ts` — `ARCHETYPES`, `TYPE_GRID`, `assertValidArchetypeGrid`, `isValidArchetypeId`.
- `personality-recipe-spec.ts` — `formatRecipeExecutionSpec` and `summarizeRecipeCoreGate`.
- `personality-questions.ts` — stable import path that re-exports the per-act question bank in `apps/web/src/features/personality/questions/`.
- `personality-archetypes-long.ts` / `personality-archetypes-quick.ts` — the 16 archetype records, split by horizon row so neither catalogue crosses the 400-LOC ceiling.

Each file stays within at most two typography combinations (`text-sm font-bold` + `text-xs font-normal`) and `border-2` borders; the page hero deliberately carries no `text-lg font-bold` title.

## Tests

- `apps/web/src/features/personality/personality-data.test.ts` — 16 questions in 4 acts of 4 with unique ids; every question's deltas symmetric per axis with target loading and cross-loadings `<= 4`; all 16 `TYPE_CODES` with fixed-order letters and one archetype per claimed cell; the **distribution gate** (seeded xorshift32, 200,000 samples through `codeFromAnswers`: every cell `>= 2%` share and `>= 500` observations — measured range after the review fixes was 3.40% `LNFR` to 10.60% `QVMP`); probe-dominance regression (four impatient horizon probes plus maximised horizon cross-loadings still yield `Q`); letters always match their act's delta sign over 2,000 random answer sets; **all 120 archetype recipe pairs differ on at least two of {news window, memories window, rule set, tool set}**; 16 distinct titles, recipe names, builder prompts and recipe prompts; every archetype reachable toward its centroid emitting its own cell code; code/strength emission, `±2` toss-up marking and weakest-letter neighbour flips; `formatRecipeExecutionSpec` and `<= 14`-char `summarizeRecipeCoreGate` parity; `buildSharedArchetypeResult` returning `fitPercent: 98` with a one-letter-away neighbour.
- `apps/web/src/features/personality/PersonalityQuizPage.test.tsx` — steps through all 16 questions with back navigation, checks the first completed act reveals exactly one leaning letter (and that nothing is revealed before then), reveals the matched bot card plus the neighbour trough with a `/build?idea=` link, retakes back to Q1; verifies `initialAtmosphere` and `cedar-sanctuary` backdrop parity; checks `?archetype=contrarian-diver` hydration and zero nested `.voxel-card` elements; verifies router search sync without wiping `quizAnswers` (propagating each self-emitted search back like the real router), a coalesced/deduped delivery still preserving a finished quiz, non-destructive self-reselection and `Back to my quiz match`, reset when `initialArchetype` clears, invariant 16-cell grid across switches, 4-badge count (`3` data badges in strip), and `.flex-wrap` / `.whitespace-nowrap` meta rows.
- `apps/web/src/components/ui/TypeCodeGrid.test.tsx` — 16 cells, single `aria-pressed` active cell, selection reports the code, in-flow description with no `title` attribute.
- `apps/web/src/features/recipes/api/recipes-validators.test.ts` — every sanctioned metric accepted, `FCF_yield` and unknown indicators rejected, prompt-only recipes ignored.

## Act checkpoints, the visitor's own words, and resume

Three engagement mechanisms sit on top of the 16-question flow:

- **Act checkpoint plaque** (`ActCheckpointPlaque.tsx`) — closing an act (question 4, 8, 12) replaces the question card *in place* with a plaque naming the letter just settled, its pole label, the strength and one filled voxel bar. "Keep going" advances to the next act. It is a sibling card at the same level as the step, never nested inside one, so there is no layout shift and no new page block. Backing out of a plaque returns to the act's last question rather than losing the answer.
- **Act-4 free text** — an optional 180-character field at the top of Act 4 ("anything you want the bot to be like"). It is never scored, never changes the type, and is appended verbatim to `builderIdeaPrompt` as `In their words: "..."` when the visitor opens `/build`; the result panel echoes it back as **Your words**.
- **Deferred resume** — answers are written to `localStorage` (`benchify:personality-draft`) after hydration only. On return, a draft with `>= 3` answers offers an in-flow *Resume Act N* trough above the quiz; the trough never renders during SSR, so hydration stays byte-identical.

## Analytics and share paths

- Events: `quiz_started`, `quiz_question_answered{index, act, option}`, `quiz_act_completed{act, letter, strength}`, `quiz_completed{code, strength, seconds}` — emitted through `track()` and no-ops outside a PostHog provider.
- Canonical share path: `/personality/t/CODE` (`routes/personality.t.$code.tsx`). Lowercase codes are normalised, unknown codes throw `notFound()`. The copy-link button emits this path. Routing shape: `personality.tsx` is a layout that owns `validateSearch`, `personality.index.tsx` is the quiz, `personality.t.$code.tsx` is the shared result — no `_`-suffix filename tricks.
- Legacy `?archetype=<slug>` renders inspect mode **in place**, deliberately without redirecting to the canonical path: that navigation remounts the page and drops in-progress result state (the Act-4 words were lost this way until it was caught in the visual pass).

## Related

- [[concepts/living-scene-backdrops]] — panoramic Cedar Sanctuary diorama and `SceneStage` HUD controls
- [[concepts/cumulative-layout-shift]] — SSR loader parity and zero-flash hydration guarantee
- [[entities/recipe-studio]] — the starter templates the archetypes map onto and the `/build` builder the CTA targets
- [[entities/web-app]] — the dashboard that hosts the `/personality` route
- [[entities/design-system]] — `SceneStage`, `Card`, `Badge`, and the zero-nested-card rule
- [[concepts/state-machines]] — the `QuizSession` discriminated union
