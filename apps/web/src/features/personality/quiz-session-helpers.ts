import type { PersonalitySceneAct } from '../home/backdrop/PersonalityBackdrop';
import {
    ARCHETYPES,
    type ArchetypeId,
    AXIS_DEFINITIONS,
    buildSharedArchetypeResult,
    PERSONALITY_QUESTIONS,
    QUIZ_ACTS,
    type QuizScoreResult,
    scorePersonalityQuiz,
    TYPE_LETTERS,
} from './personality-data';

/**
 * Discriminated union preserving finished quiz answers while browsing other
 * archetypes, making illegal `{ null, null }` result states unrepresentable.
 */
export type QuizSession =
    | {
          phase: 'answering';
          stepIndex: number;
          answers: Record<string, string>;
          /** Index of the act whose checkpoint plaque is showing, if any. */
          checkpoint: number | null;
      }
    | {
          phase: 'result';
          mode: 'quiz_match';
          quizAnswers: Record<string, string>;
      }
    | {
          phase: 'result';
          mode: 'inspect';
          archetypeId: ArchetypeId;
          quizAnswers: Record<string, string> | null;
      };

export interface QuizDraft {
    answers: Record<string, string>;
    stepIndex: number;
    selfDescription: string;
}

export const QUESTIONS_PER_ACT = 4;
export const MAX_PENDING_SELF_SEARCHES = 4;
const RESUME_STORAGE_KEY = 'benchify:personality-draft';
const RESUME_MIN_ANSWERED = 3;

export function createInitialSession(initialArchetype?: ArchetypeId): QuizSession {
    if (initialArchetype) {
        return {
            phase: 'result',
            mode: 'inspect',
            archetypeId: initialArchetype,
            quizAnswers: null,
        };
    }
    return { phase: 'answering', stepIndex: 0, answers: {}, checkpoint: null };
}

export function readDraft(): QuizDraft | null {
    try {
        const raw = window.localStorage.getItem(RESUME_STORAGE_KEY);
        if (!raw) return null;
        const parsed = JSON.parse(raw) as Partial<QuizDraft>;
        const answers = parsed.answers ?? {};
        if (Object.keys(answers).length < RESUME_MIN_ANSWERED) return null;
        if (typeof parsed.stepIndex !== 'number') return null;
        return {
            answers,
            stepIndex: Math.max(0, Math.min(PERSONALITY_QUESTIONS.length - 1, parsed.stepIndex)),
            selfDescription:
                typeof parsed.selfDescription === 'string' ? parsed.selfDescription : '',
        };
    } catch {
        return null;
    }
}

export function syncDraftStorage(session: QuizSession, selfDescription: string): void {
    if (session.phase !== 'answering') return;
    const answered = Object.keys(session.answers).length;
    if (answered === 0) return;
    try {
        window.localStorage.setItem(
            RESUME_STORAGE_KEY,
            JSON.stringify({
                answers: session.answers,
                stepIndex: session.stepIndex,
                selfDescription,
            }),
        );
    } catch {
        // Storage disabled (private mode or quota); resume is a convenience only.
    }
}

export function clearDraftStorage(): void {
    try {
        window.localStorage.removeItem(RESUME_STORAGE_KEY);
    } catch {
        // Storage disabled; nothing to clear.
    }
}

export function computeLiveQuizResult(session: QuizSession): QuizScoreResult {
    if (session.phase === 'answering') {
        return scorePersonalityQuiz(session.answers);
    }
    if (session.mode === 'inspect') {
        return buildSharedArchetypeResult(session.archetypeId);
    }
    return scorePersonalityQuiz(session.quizAnswers);
}

export function computeLiveHint(session: QuizSession, liveQuizResult: QuizScoreResult): string {
    // Only letters whose whole act has been answered are shown, so a visitor is
    // never handed three letters derived from questions they have not seen yet.
    const hintAnswers = session.phase === 'answering' ? session.answers : session.quizAnswers;
    if (!hintAnswers) return '';
    const revealed = liveQuizResult.letters
        .filter((letter) =>
            PERSONALITY_QUESTIONS.filter((q) => q.act === letter.axis).every(
                (q) => hintAnswers[q.id] !== undefined,
            ),
        )
        .map((letter) => letter.letter)
        .join('');
    return revealed ? `Leaning: ${revealed}` : '';
}

export function deriveCheckpointContext(session: QuizSession, liveQuizResult: QuizScoreResult) {
    const checkpointIndex =
        session.phase === 'answering' && session.checkpoint !== null ? session.checkpoint : null;
    const checkpointAct = checkpointIndex !== null ? QUIZ_ACTS[checkpointIndex] : undefined;
    const checkpointLetter = checkpointAct
        ? liveQuizResult.letters.find((letter) => letter.axis === checkpointAct.axis)
        : undefined;
    const checkpointAxis = checkpointAct
        ? AXIS_DEFINITIONS.find((axis) => axis.id === checkpointAct.axis)
        : undefined;
    const checkpointPoleLabel =
        checkpointAxis && checkpointLetter
            ? checkpointLetter.letter === TYPE_LETTERS[checkpointAxis.id].high
                ? checkpointAxis.highLabel
                : checkpointAxis.lowLabel
            : '';
    return { checkpointIndex, checkpointAct, checkpointLetter, checkpointPoleLabel };
}

export function deriveQuizViewModel(
    session: QuizSession,
    liveQuizResult: QuizScoreResult,
    initialArchetype?: ArchetypeId,
) {
    const headingArchetype =
        session.phase === 'result' && session.mode === 'quiz_match'
            ? liveQuizResult.primary.archetype.id
            : initialArchetype;
    const pageHeading = headingArchetype
        ? `${ARCHETYPES[headingArchetype].title} — investing style diagnostic`
        : 'Investing style diagnostic: discover your best trading bot';

    const currentQuestion =
        session.phase === 'answering' ? PERSONALITY_QUESTIONS[session.stepIndex] : undefined;
    const currentActIndex = currentQuestion
        ? Math.max(
              0,
              QUIZ_ACTS.findIndex((act) => act.axis === currentQuestion.act),
          )
        : 0;
    const currentAct = QUIZ_ACTS[currentActIndex];

    const sceneAct: PersonalitySceneAct =
        session.phase === 'result'
            ? 'result'
            : ((session.checkpoint ?? currentActIndex) as PersonalitySceneAct);

    const canReturnToQuizMatch =
        session.phase === 'result' && session.mode === 'inspect' && session.quizAnswers !== null;

    return {
        pageHeading,
        currentActIndex,
        currentAct,
        sceneAct,
        canReturnToQuizMatch,
        liveHint: computeLiveHint(session, liveQuizResult),
        ...deriveCheckpointContext(session, liveQuizResult),
    };
}
