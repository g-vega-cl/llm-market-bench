import { PERSONALITY_QUESTIONS, QUIZ_ACTS } from './personality-questions';

function longestBy(values: string[]): string {
    return values.reduce((best, value) => (value.length > best.length ? value : best), '');
}

const ALL_OPTIONS = PERSONALITY_QUESTIONS.flatMap((question) => question.options);

/**
 * Upper bound for every variable piece of copy a question card can render.
 *
 * The card reserves these strings in hidden rows (`QuizPinnedRow`) so the answer
 * list starts at the same y on every question and every container width, instead
 * of drifting whenever an act title, context label or prompt gains a line.
 * Deriving them from the full question set means a new question can never be
 * taller than the reserved row by copy alone.
 *
 * `option` is ONE pair shared by every answer row, not the longest label per
 * slot. A per-slot reservation let row A reserve 108 px while row D reserved
 * 128 px, so the four buttons rendered ragged inside the same grid (measured
 * 72-128 px at a 390 px viewport) and the dead space above the pinned footer
 * swung 16-120 px between questions. One pair makes every row the same height
 * at every width.
 */
export const QUIZ_WORST_CASE = {
    actTitle: longestBy(QUIZ_ACTS.map((act) => act.title)),
    context: longestBy(PERSONALITY_QUESTIONS.map((question) => question.context)),
    prompt: longestBy(PERSONALITY_QUESTIONS.map((question) => question.prompt)),
    liveHint: longestBy(['Scoring 4 trading axes', 'Leaning: LVFP']),
    option: {
        label: longestBy(ALL_OPTIONS.map((option) => option.label)),
        detail: longestBy(ALL_OPTIONS.map((option) => option.detail)),
    },
};

export const QUIZ_TOTAL_QUESTION_LABEL = `Question ${String(PERSONALITY_QUESTIONS.length).padStart(
    2,
    '0',
)} / ${String(PERSONALITY_QUESTIONS.length)}`;

/** The four answer slots, in render order, as their option letters. */
export const QUIZ_OPTION_LETTERS = ['A', 'B', 'C', 'D'] as const;
