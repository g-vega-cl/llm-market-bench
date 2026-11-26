import { PERSONALITY_QUESTIONS, QUIZ_ACTS } from './personality-questions';

function longestBy(values: string[]): string {
    return values.reduce((best, value) => (value.length > best.length ? value : best), '');
}

/**
 * Upper bound for every variable piece of copy a question card can render.
 *
 * The card reserves these strings in hidden rows (`QuizPinnedRow`) so the answer
 * list starts at the same y on every question and every container width, instead
 * of drifting whenever an act title, context label or prompt gains a line.
 * Deriving them from the full question set means a new question can never be
 * taller than the reserved row by copy alone.
 */
export const QUIZ_WORST_CASE = {
    actTitle: longestBy(QUIZ_ACTS.map((act) => act.title)),
    context: longestBy(PERSONALITY_QUESTIONS.map((question) => question.context)),
    prompt: longestBy(PERSONALITY_QUESTIONS.map((question) => question.prompt)),
    liveHint: longestBy(['Scoring 4 trading axes', 'Leaning: LVFP']),
    options: [0, 1, 2, 3].map((slot) => ({
        label: longestBy(
            PERSONALITY_QUESTIONS.map((question) => question.options[slot]?.label ?? ''),
        ),
        detail: longestBy(
            PERSONALITY_QUESTIONS.map((question) => question.options[slot]?.detail ?? ''),
        ),
    })),
};

export const QUIZ_TOTAL_QUESTION_LABEL = `Question ${String(PERSONALITY_QUESTIONS.length).padStart(
    2,
    '0',
)} / ${String(PERSONALITY_QUESTIONS.length)}`;
