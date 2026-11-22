/**
 * Stable import path for the question bank. The bank itself lives in `./questions`,
 * split one file per act so each module stays under the 400-LOC ceiling.
 */
export {
    PERSONALITY_QUESTIONS,
    QUIZ_ACTS,
    type QuizActDefinition,
    type QuizOption,
    type QuizQuestion,
} from './questions';
