import type { QuizQuestion } from './types';

/**
 * Act 4 — Execution Tempo. Target deltas +-14/+-5 on `cadence`, cross-loadings
 * <= 4, symmetric about zero, half the questions presented high pole first.
 */
export const CADENCE_QUESTIONS: QuizQuestion[] = [
    {
        id: 'a4-slot-count',
        act: 'cadence',
        prompt: 'How many positions should a bot hold and rotate?',
        context: 'Slot Count',
        options: [
            {
                id: 'a4-slot-a',
                label: 'Two or three deep positions, changed rarely',
                detail: 'Concentration forces you to know the thesis cold.',
                deltas: { cadence: -14, horizon: 4, signal: -2 },
            },
            {
                id: 'a4-slot-b',
                label: 'Four core slots, reviewed each cycle',
                detail: 'Enough breadth to diversify, enough focus to care.',
                deltas: { cadence: -5, horizon: 2 },
            },
            {
                id: 'a4-slot-c',
                label: 'Six to eight slots, rotated as catalysts shift',
                detail: 'Breadth across themes with regular turnover.',
                deltas: { cadence: 5, horizon: -2 },
            },
            {
                id: 'a4-slot-d',
                label: 'Ten or more tactical tickets, recycled constantly',
                detail: 'Always deployed, always hunting the next catalyst.',
                deltas: { cadence: 14, horizon: -4, signal: 2 },
            },
        ],
    },
    {
        id: 'a4-gate-miss',
        act: 'cadence',
        prompt: 'A setup misses your entry gate by two points. Next cycle it is still two points short.',
        context: 'Gate Discipline',
        options: [
            {
                id: 'a4-gate-a',
                label: 'Loosen the gate now — it is costing you trades',
                detail: 'A rule that never fires is not protecting anything.',
                deltas: { cadence: 14, contrarian: -2, horizon: 2 },
            },
            {
                id: 'a4-gate-b',
                label: 'Test a looser variant in the same cycle',
                detail: 'Run both rules and compare the output.',
                deltas: { cadence: 5, horizon: 1 },
            },
            {
                id: 'a4-gate-c',
                label: 'Review the gate quarterly, not daily',
                detail: 'Rules earn their keep over samples, not sessions.',
                deltas: { cadence: -5, horizon: -1 },
            },
            {
                id: 'a4-gate-d',
                label: 'Leave it alone; it exists because it works',
                detail: 'The gate is the edge. Move the gate, lose the edge.',
                deltas: { cadence: -14, contrarian: 2, horizon: -2 },
            },
        ],
    },
    {
        id: 'a4-idle-cash',
        act: 'cadence',
        prompt: 'Cash sits at 60% for a week. What should the bot do?',
        context: 'Idle Capital',
        options: [
            {
                id: 'a4-cash-a',
                label: 'Nothing — cash is a position',
                detail: 'The absence of a trade is itself a decision.',
                deltas: { cadence: -14, horizon: 2 },
            },
            {
                id: 'a4-cash-b',
                label: 'Keep screening the same universe',
                detail: 'Same rules, more patience.',
                deltas: { cadence: -5, horizon: 1 },
            },
            {
                id: 'a4-cash-c',
                label: 'Widen the universe to find qualifying names',
                detail: 'Keep the bar, expand the hunting ground.',
                deltas: { cadence: 5, horizon: -1 },
            },
            {
                id: 'a4-cash-d',
                label: 'Lower the bar until capital is deployed',
                detail: 'Idle capital is the real risk.',
                deltas: { cadence: 14, horizon: -2 },
            },
        ],
    },
    {
        id: 'a4-review-rhythm',
        act: 'cadence',
        prompt: 'How often should a bot audit open theses after a trade closes?',
        context: 'Review Rhythm',
        options: [
            {
                id: 'a4-review-a',
                label: 'Every cycle — audit open theses at each slot',
                detail: 'A thesis nobody re-reads is a thesis nobody owns.',
                deltas: { cadence: 14, signal: -2, contrarian: 2, horizon: -2 },
            },
            {
                id: 'a4-review-b',
                label: 'Weekly review of signals and exits',
                detail: 'Frequent enough to catch drift, rare enough to be cheap.',
                deltas: { cadence: 5, horizon: -1 },
            },
            {
                id: 'a4-review-c',
                label: 'Monthly review of the rule set',
                detail: 'Audit the process, not each position.',
                deltas: { cadence: -5, horizon: 1 },
            },
            {
                id: 'a4-review-d',
                label: 'Quarterly post-mortem is enough',
                detail: 'Long cycles deserve long feedback loops.',
                deltas: { cadence: -14, signal: 2, contrarian: -2, horizon: 2 },
            },
        ],
    },
];
