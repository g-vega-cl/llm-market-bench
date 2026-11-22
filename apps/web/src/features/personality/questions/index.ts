import { CADENCE_QUESTIONS } from './act-cadence';
import { CONTRARIAN_QUESTIONS } from './act-contrarian';
import { HORIZON_QUESTIONS } from './act-horizon';
import { SIGNAL_QUESTIONS } from './act-signal';
import type { QuizActDefinition, QuizQuestion } from './types';

export type { QuizActDefinition, QuizOption, QuizQuestion } from './types';

/**
 * Four acts of four questions. An act is a chapter heading, not a syllabus: its
 * questions stay full market scenarios while ~70% of their delta mass lands on
 * the act's axis (target deltas +-14/+-5, cross-loadings <= 4).
 *
 * Every question's option deltas are symmetric about zero on every axis, so the
 * normalized midpoint is a true 50 and the 16 type cells stay near-uniform.
 * The distribution gate in `personality-data.test.ts` enforces that.
 */
export const QUIZ_ACTS: QuizActDefinition[] = [
    {
        axis: 'horizon',
        title: 'Patience & Horizon',
        blurb: 'How long your capital is allowed to work.',
    },
    {
        axis: 'signal',
        title: 'Signal Anchor',
        blurb: 'Which evidence you trust when the two disagree.',
    },
    {
        axis: 'contrarian',
        title: 'Crowd Stance',
        blurb: 'Whether you follow the tape or fade it.',
    },
    {
        axis: 'cadence',
        title: 'Execution Tempo',
        blurb: 'How hard your bot should work the book.',
    },
];

export const PERSONALITY_QUESTIONS: QuizQuestion[] = [
    ...HORIZON_QUESTIONS,
    ...SIGNAL_QUESTIONS,
    ...CONTRARIAN_QUESTIONS,
    ...CADENCE_QUESTIONS,
];
