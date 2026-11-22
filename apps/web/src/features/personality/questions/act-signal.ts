import type { QuizQuestion } from './types';

/**
 * Act 2 — Signal Anchor. Target deltas +-14/+-5 on `signal`, cross-loadings
 * <= 4, symmetric about zero, half the questions presented high pole first.
 */
export const SIGNAL_QUESTIONS: QuizQuestion[] = [
    {
        id: 'a2-one-stream',
        act: 'signal',
        prompt: 'Your bot can keep exactly one data stream. Which one is non-negotiable?',
        context: 'Single Data Stream',
        options: [
            {
                id: 'a2-stream-a',
                label: 'Free cash flow, P/E, and 52-week range health',
                detail: 'Hard company math protects the downside better than prose.',
                deltas: { signal: -14, horizon: 4, cadence: -2 },
            },
            {
                id: 'a2-stream-b',
                label: 'Earnings surprise history and guidance revisions',
                detail: 'Recurring event data beats one-off headlines.',
                deltas: { signal: -5, horizon: 2 },
            },
            {
                id: 'a2-stream-c',
                label: 'The sector news menu plus market-event memories',
                detail: 'Narrative velocity reprices a sector faster than filings do.',
                deltas: { signal: 5, horizon: -2 },
            },
            {
                id: 'a2-stream-d',
                label: 'A live headline feed with 48-hour recency',
                detail: 'The freshest tape is the only tape that matters.',
                deltas: { signal: 14, horizon: -4, cadence: 2 },
            },
        ],
    },
    {
        id: 'a2-unverified-headline',
        act: 'signal',
        prompt: 'A name you own jumps 9% on a headline you cannot verify yet.',
        context: 'Unverified Headline',
        options: [
            {
                id: 'a2-headline-a',
                label: 'Buy the second-order beneficiary before the chain reprices',
                detail: 'Narrative diffusion is the whole edge.',
                deltas: { signal: 14, contrarian: -2, cadence: 4 },
            },
            {
                id: 'a2-headline-b',
                label: 'Search the source, then let RVOL confirm before adding',
                detail: 'News plus participation, or no position.',
                deltas: { signal: 5, cadence: 2 },
            },
            {
                id: 'a2-headline-c',
                label: 'Check the 52-week position and P/E before doing anything',
                detail: 'Price location and valuation first, story second.',
                deltas: { signal: -5, cadence: -2 },
            },
            {
                id: 'a2-headline-d',
                label: 'Ignore the pop and re-run the valuation model tonight',
                detail: 'If the model did not change, neither should the book.',
                deltas: { signal: -14, contrarian: 2, cadence: -4 },
            },
        ],
    },
    {
        id: 'a2-guidance-cut',
        act: 'signal',
        prompt: 'Guidance is cut 10%, but free-cash-flow guidance is reaffirmed. Which line does your bot weight?',
        context: 'Conflicting Signals',
        options: [
            {
                id: 'a2-guidance-a',
                label: 'The cash-flow line — guidance noise mean-reverts',
                detail: 'Capital allocation does not change because a slide deck did.',
                deltas: { signal: -14, horizon: -2, cadence: -2 },
            },
            {
                id: 'a2-guidance-b',
                label: 'Both, but the balance sheet decides position size',
                detail: 'Fundamentals set the size, not the entry.',
                deltas: { signal: -5, cadence: -1 },
            },
            {
                id: 'a2-guidance-c',
                label: 'Both, but the cut decides when entries resume',
                detail: 'The event sets the timing; the balance sheet still matters.',
                deltas: { signal: 5, cadence: 1 },
            },
            {
                id: 'a2-guidance-d',
                label: 'The cut — repricing it is the entire trade',
                detail: 'The tape can stay irrational longer than the model stays right.',
                deltas: { signal: 14, horizon: 2, cadence: 2 },
            },
        ],
    },
    {
        id: 'a2-edge-source',
        act: 'signal',
        prompt: 'Where does your edge actually come from?',
        context: 'Edge Source',
        options: [
            {
                id: 'a2-edge-a',
                label: 'Being first to a policy or sector catalyst',
                detail: 'Speed of interpretation is the moat.',
                deltas: { signal: 14, horizon: -4, contrarian: 2, cadence: -2 },
            },
            {
                id: 'a2-edge-b',
                label: 'Mapping headlines to second-order movers faster than the crowd',
                detail: 'Same information, better second derivative.',
                deltas: { signal: 5, horizon: -2 },
            },
            {
                id: 'a2-edge-c',
                label: 'Screening fundamentals systematically and waiting',
                detail: 'The screen does the work; patience does the rest.',
                deltas: { signal: -5, horizon: 2 },
            },
            {
                id: 'a2-edge-d',
                label: 'Reading filings and multiples more carefully than the crowd',
                detail: 'Depth beats latency over a long enough window.',
                deltas: { signal: -14, horizon: 4, contrarian: -2, cadence: 2 },
            },
        ],
    },
];
