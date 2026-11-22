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

Each archetype also carries a `tagline`, a `summary`, three `strengths`, a `watchout`, an `idealProfile` (its 4-axis centroid), and a `builderIdeaPrompt` — a plain-English bot description passed to `/build` as the `idea` search param so the visitor lands in the builder with a pre-filled prompt.

`buildSharedArchetypeResult(archetypeId)` produces a result directly from an archetype's `idealProfile` with `fitPercent: 98` on the primary match, which is what an `?archetype=` deep link renders.

## Session State Machine

`QuizSession` is a discriminated union that makes incoherent partial-quiz + inspect states unrepresentable:

```ts
type QuizSession =
    | { phase: 'answering'; stepIndex: number; answers: Record<string, string> }
    | { phase: 'result'; source: 'quiz'; answers: Record<string, string> }
    | { phase: 'result'; source: 'inspect'; archetypeId: ArchetypeId };
```

`createInitialSession(initialArchetype)` returns an `inspect` result when a valid archetype is supplied, otherwise `answering` at step 0. A `useEffect` keyed on `initialArchetype` re-seeds the session when the search param changes, so navigating between share links never leaves a half-answered quiz on screen.

Selecting the last option calls `scorePersonalityQuiz`, writes the winning archetype into the URL via `syncUrlSearchParam('archetype', id)`, and transitions to `result:quiz`. `handleRetake` clears the param and resets to `answering` at step 0. `handleInspectArchetype` writes the param and switches to `result:inspect`. Atmosphere cycling (`Sky:`) and motion controls come from `useDioramaStage(initialAtmosphere)` rendered over the panoramic `Cedar Sanctuary` backdrop.

## Result Panel Actions

`PersonalityResultPanel` renders inside a single `.scene-scrim .voxel-card` plaque (`data-testid="personality-result"`) whose children are recessed `Card variant="outlined"` / `.voxel-trough` surfaces — zero nested `.voxel-card`, per `.agents/rules/design-spec.md`.

- **4-Axis Diagnostic Profile** (`data-testid="axis-breakdown"`) — one labelled bar per axis with the `N/100` score and the low/high pole labels.
- **Edge & Blind Spot** — the archetype's three strengths plus its `watchout`.
- **Top-2 Matched Trading Bots** — `#1 Best Bot Match` and `#2 Runner-Up Match` cards, each showing the recipe name, description, prompt snippet, `Backtest: <cadence>` and `N live tools` badges, block summaries (`News (Nh)`, `Memories (<category>)`, technical rule strings), a `Build this bot` link to `/build?idea=<builderIdeaPrompt>`, and an `Open Recipe Studio` link.
- **Header actions** — `Copy share link` (writes `/personality?archetype=<id>` to the clipboard and flips to `Share link copied`) and `Retake 10Q quiz` (`data-testid="retake-quiz"`).
- **Archetype switcher** — one button per `ARCHETYPE_IDS` entry labelled with `arch.title`, active one solid accent, driving `onInspectArchetype`.

## Components

- `PersonalityQuizPage.tsx` — session state machine, URL sync, clipboard handling, and `Cedar Sanctuary` stage composition.
- `PersonalityQuizStep.tsx` — single-question card (`data-testid="personality-quiz-card"`) with a `Question NN / 10` badge, `context`, `quiz-live-world-hint` (`Leaning: …` or `Scoring 4 trading axes`), accessible `role="progressbar"`, four full-width option buttons (`data-testid="quiz-option-<id>"`), `Previous question`, and `Browse all 5 styles` (`data-testid="skip-to-all-archetypes"`).
- `PersonalityResultPanel.tsx` — the result plaque described above.
- `personality-data.ts` — axes, archetypes, scoring, ranking, share-result builder, and the eager recipe-integrity check.
- `personality-questions.ts` — the 10 questions and their option deltas.

Typography stays inside two combinations (`text-xs font-normal`, `text-sm font-bold`) and the cards use a single `border-2` border style, per the design budget.

## Tests

- `apps/web/src/features/personality/personality-data.test.ts` — 10 questions with 4 options each; `AXIS_DEFINITIONS` length 4; every mapped recipe name exists in `STARTER_RECIPES`; all five archetypes are reachable by answering toward their centroid with distinct top-2 matches and bounded `0..100` axes; `buildSharedArchetypeResult` returns `fitPercent: 98` with a different runner-up for every id.
- `apps/web/src/features/personality/PersonalityQuizPage.test.tsx` — steps through all 10 questions with back navigation and a live `Leaning:` hint, reveals `#1 Best Bot Match` / `#2 Runner-Up Match` with a `/build?idea=` link, retakes back to Q1; verifies `initialAtmosphere` and `cedar-sanctuary` backdrop parity; checks `?archetype=contrarian-diver` hydration and zero nested `.voxel-card` elements; verifies switching to `news-surfer` mid-quiz replaces session cleanly.

## Related

- [[concepts/living-scene-backdrops]] — panoramic Cedar Sanctuary diorama and `SceneStage` HUD controls
- [[concepts/cumulative-layout-shift]] — SSR loader parity and zero-flash hydration guarantee
- [[entities/recipe-studio]] — the starter templates the archetypes map onto and the `/build` builder the CTA targets
- [[entities/web-app]] — the dashboard that hosts the `/personality` route
- [[entities/design-system]] — `SceneStage`, `Card`, `Badge`, and the zero-nested-card rule
- [[concepts/state-machines]] — the `QuizSession` discriminated union
