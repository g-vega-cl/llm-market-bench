import type { QuizQuestion } from './types';

/**
 * Act 1 — Patience & Horizon. Target deltas +-14/+-5 on `horizon`, cross-loadings
 * <= 4, symmetric about zero, half the questions presented high pole first.
 */
export const HORIZON_QUESTIONS: QuizQuestion[] = [
    {
        id: 'a1-opening-shock',
        act: 'horizon',
        prompt: 'At 09:30 ET semiconductors gap down 4% on a sudden export-tariff headline. What does your bot do with the book?',
        context: 'Opening Bell Shock',
        options: [
            {
                id: 'a1-a',
                label: 'Sell the sleeve by the close and wait for the tape to settle',
                detail: 'Tariff headlines resolve within days; cash beats being early.',
                deltas: { horizon: -14, signal: 4, cadence: 4 },
            },
            {
                id: 'a1-b',
                label: 'Trim today, reassess the supply chain when the next session opens',
                detail: 'One session of clarity usually shows whether it is real.',
                deltas: { horizon: -5, signal: 2, cadence: 2 },
            },
            {
                id: 'a1-c',
                label: 'Hold, and only add back if the earnings path survives next quarter',
                detail: 'Let the quarterly numbers decide, not the first headline.',
                deltas: { horizon: 5, signal: -2, cadence: -2 },
            },
            {
                id: 'a1-d',
                label: 'Change nothing — a tariff headline does not move a three-year cash-flow model',
                detail: 'The model was built for quarters. The tape is noise.',
                deltas: { horizon: 14, signal: -4, cadence: -4 },
            },
        ],
    },
    {
        id: 'a1-empty-tape',
        act: 'horizon',
        prompt: 'Three sessions pass with zero setups clearing your rules and cash sits at 100%. What happens next?',
        context: 'Empty Tape',
        options: [
            {
                id: 'a1-empty-a',
                label: 'Wait as long as it takes — a year in cash beats one forced trade',
                detail: 'Discipline is the position. Nothing clears, nothing gets bought.',
                deltas: { horizon: 14, contrarian: 2, cadence: -4 },
            },
            {
                id: 'a1-empty-b',
                label: 'Keep screening the same rules; confluence eventually shows up',
                detail: 'No change in process, only in patience.',
                deltas: { horizon: 5, cadence: -2 },
            },
            {
                id: 'a1-empty-c',
                label: 'Step down to the second tier of setups until something qualifies',
                detail: 'A weaker trade now versus a better one eventually.',
                deltas: { horizon: -5, cadence: 2 },
            },
            {
                id: 'a1-empty-d',
                label: 'Force the best available name — idle capital is a losing position',
                detail: 'Exposure matters more than entry quality.',
                deltas: { horizon: -14, contrarian: -2, cadence: 4 },
            },
        ],
    },
    {
        id: 'a1-quarter-thesis',
        act: 'horizon',
        prompt: 'A position is +6% after two weeks, and your thesis expected 20% over one quarter.',
        context: 'Thesis Horizon',
        options: [
            {
                id: 'a1-quarter-a',
                label: 'Take the 6% now — realised cash beats an unrealised model',
                detail: 'Small wins compound if you actually bank them.',
                deltas: { horizon: -14, contrarian: -2, cadence: 2 },
            },
            {
                id: 'a1-quarter-b',
                label: 'Scale half out and let the rest ride into next week',
                detail: 'De-risk the position without abandoning the story.',
                deltas: { horizon: -5, contrarian: -1, cadence: 1 },
            },
            {
                id: 'a1-quarter-c',
                label: 'Hold for the quarter; the thesis was never time-stamped to a week',
                detail: 'Slow value transfer is still value transfer.',
                deltas: { horizon: 5, contrarian: 1, cadence: -1 },
            },
            {
                id: 'a1-quarter-d',
                label: 'Add on the next fundamental confirmation — the quarter is still young',
                detail: 'Pyramid into a thesis that is working, not out of it.',
                deltas: { horizon: 14, contrarian: 2, cadence: -2 },
            },
        ],
    },
    {
        id: 'a1-holding-period',
        act: 'horizon',
        prompt: 'What should your bot’s realistic average holding period be?',
        context: 'Holding Period',
        options: [
            {
                id: 'a1-hold-a',
                label: 'Years, as long as the compounding engine keeps working',
                detail: 'Ownership, not occupancy.',
                deltas: { horizon: 14, signal: -4, cadence: -4 },
            },
            {
                id: 'a1-hold-b',
                label: 'One to two quarters, straight through an earnings cycle',
                detail: 'Let one full reporting cycle resolve the thesis.',
                deltas: { horizon: 5, signal: -2, cadence: -2 },
            },
            {
                id: 'a1-hold-c',
                label: 'One to two weeks, riding a single catalyst window',
                detail: 'In and out around the event that justified the trade.',
                deltas: { horizon: -5, signal: 2, cadence: 2 },
            },
            {
                id: 'a1-hold-d',
                label: 'Same session to two days, constantly recycled',
                detail: 'Capital should never sit still while the tape moves.',
                deltas: { horizon: -14, signal: 4, cadence: 4 },
            },
        ],
    },
];
