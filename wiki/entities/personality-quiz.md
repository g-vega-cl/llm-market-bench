---
tags: [web, personality, quiz, archetypes, recipes, diagnostic]
category: entity
---

# Investing Style Diagnostic (`/personality`)

A 10-question investing-personality diagnostic that scores a visitor across four behavioural axes, matches them to an investing archetype, and recommends the two starter trading recipes that best fit their temperament. It is the discovery funnel that turns "I don't know what kind of trader I am" into "here is a bot I can build", linking straight into `/build` and `/recipes`.

The route lives at `apps/web/src/routes/personality.tsx` and renders `PersonalityQuizPage` (`apps/web/src/features/personality/PersonalityQuizPage.tsx`) on a design-system `SceneStage` (`variant="hero"`, `motionRole="reactive"`) backed by the panoramic **Cedar Sanctuary** [[concepts/living-scene-backdrops]] diorama and an SSR-resolved `initialAtmosphere` from the route `loader` to eliminate SSR/CSR visual flashes ([[concepts/cumulative-layout-shift]]).

## Route & Search Params

`validateSearch` accepts a single optional `archetype` key and normalizes anything unrecognized to `undefined`:

```ts
validateSearch: (search: Record<string, unknown>): { archetype?: ArchetypeId } => ({
    archetype: isValidArchetypeId(search.archetype) ? search.archetype : undefined,
})
```

The route `loader` resolves `initialAtmosphere: resolveAtmospherePhase(new Date(), 'market-et')` synchronously on the server so hydration matches SSR on first byte with zero layout or atmosphere shift.

`/personality?archetype=<id>` opens the page directly in **inspect** mode for that archetype (shareable result links), while a bare `/personality` starts the quiz at question 1. The route head declares the title `Investing Style & Best Trading Bot Quiz | Benchify` plus a description naming the four axes.

The homepage links here from the `Take the investing style test` button (`data-testid="take-personality-test"`) inside `home-cta-plaque`, and `/lab` lists it as **Investing Style Diagnostic** under `Research & Prediction Engines`.

## The 10-Question Diagnostic

`PERSONALITY_QUESTIONS` (`apps/web/src/features/personality/personality-questions.ts`) is a fixed array of exactly 10 `QuizQuestion` objects, each with an `id`, a `prompt`, a short `context` label (e.g. `Opening Bell Shock · Framing`, `Exit Psychology`, `Prompt Constitution`), and exactly four `QuizOption`s. Every option carries a `label`, a `detail` sentence, and a `deltas` map of signed contributions to one or more axes.

The scenarios walk a coherent arc: opening-bell tariff shock, idle-cash patience, a fourth consecutive EPS beat, a 9% drawdown on no company news, a forced single-data-stream choice, a +14% euphoric winner, preferred portfolio construction, worst-regret profile, ideal bot clock rhythm, and one iron prompt rule.

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

`QuizScoreResult` is `{ profile, primary, runnerUp, rankings, answeredCount }`. Because scoring is pure and cheap, the page recomputes it on every render — the live `Leaning: <title>` hint updates after each answer without any extra state.

## Archetype → Starter Recipe Mapping

`ARCHETYPES` is a `Record<ArchetypeId, InvestingArchetype>` with a strict 1:1 mapping between archetype and starter recipe in `packages/config/starter-recipes.json`. The mapping is validated eagerly at module load — a missing starter recipe throws `Archetype "<id>" references missing starter recipe "<name>"` before any component renders.

| Archetype id | Title | Starter recipe |
| :--- | :--- | :--- |
| `value-compounder` | The Patient Compounder | `Quality Value Screener` |
| `news-surfer` | The Headline Surfer | `Trump & Chips News Momentum` |
| `contrarian-diver` | The Contrarian Diver | `Contrarian Sentiment Fader` |
| `catalyst-quant` | The Catalyst Quant | `Earnings Catalyst Hunter` |
| `systems-architect` | The Systems Architect | `Claude Agent Portfolio Mirror` |

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

- `PersonalityQuizPage.tsx` — non-destructive `'quiz_match' | 'inspect'` state machine, router-synced search params, race-guarded clipboard handling, and `Cedar Sanctuary` stage composition (`text-lg font-bold` `h1`, `text-xs font-normal`).
- `PersonalityQuizStep.tsx` — single-question card (`data-testid="personality-quiz-card"`) with a `Question NN / 10` badge, wrap-safe meta header, `quiz-live-world-hint`, accessible `role="progressbar"`, four full-width option buttons inheriting `text-voxel-trough` contrast on `bg-accent` selection, `Previous question`, and `Browse all 5 styles`.
- `PersonalityResultPanel.tsx` — the top-switcher result plaque described above (`text-sm font-bold`, `text-xs font-normal`).
- `personality-data.ts` — axes, archetypes, derived recipe formatters (`formatRecipeExecutionSpec`, `summarizeRecipeCoreGate`), scoring, ranking, share-result builder, and the eager recipe-integrity check.
- `personality-questions.ts` — the 10 questions and their option deltas.

Each file stays within at most two typography combinations (`text-sm font-bold` + `text-xs font-normal`, or `text-lg font-bold` + `text-xs font-normal` on the page hero) and `border-2` borders.

## Tests

- `apps/web/src/features/personality/personality-data.test.ts` — 10 questions with 4 options each; `AXIS_DEFINITIONS` length 4; every mapped recipe name exists in `STARTER_RECIPES`; all five archetypes are reachable by answering toward their centroid with distinct top-2 matches and bounded `0..100` axes; verifies `formatRecipeExecutionSpec` and `<= 14`-char `summarizeRecipeCoreGate` parity (including `price_52w_pct` operator preservation and 3-digit news windows); `buildSharedArchetypeResult` returns `fitPercent: 98` with a different runner-up for every id.
- `apps/web/src/features/personality/PersonalityQuizPage.test.tsx` — steps through all 10 questions with back navigation and a live `Leaning:` hint, reveals `#1 Best Bot Match` / `#2 Runner-Up Match` with a `/build?idea=` link, retakes back to Q1; verifies `initialAtmosphere` and `cedar-sanctuary` backdrop parity; checks `?archetype=contrarian-diver` hydration and zero nested `.voxel-card` elements; verifies router search sync without wiping `quizAnswers`, non-destructive self-reselection and `Back to my quiz match`, reset when `initialArchetype` clears, invariant `archetype-switcher` button count and placement, 4-badge count (`3` data badges in strip), and `.flex-wrap` / `.whitespace-nowrap` meta rows.

## Related

- [[concepts/living-scene-backdrops]] — panoramic Cedar Sanctuary diorama and `SceneStage` HUD controls
- [[concepts/cumulative-layout-shift]] — SSR loader parity and zero-flash hydration guarantee
- [[entities/recipe-studio]] — the starter templates the archetypes map onto and the `/build` builder the CTA targets
- [[entities/web-app]] — the dashboard that hosts the `/personality` route
- [[entities/design-system]] — `SceneStage`, `Card`, `Badge`, and the zero-nested-card rule
- [[concepts/state-machines]] — the `QuizSession` discriminated union
