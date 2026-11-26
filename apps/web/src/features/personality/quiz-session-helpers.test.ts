import { beforeEach, describe, expect, it } from 'vitest';
import { PERSONALITY_QUESTIONS } from './personality-data';
import {
    clearDraftStorage,
    computeLiveHint,
    computeLiveQuizResult,
    createInitialSession,
    deriveQuizViewModel,
    readDraft,
    syncDraftStorage,
} from './quiz-session-helpers';

describe('quiz-session-helpers', () => {
    beforeEach(() => {
        window.localStorage.clear();
    });

    it('creates inspect sessions for initial archetypes and answering sessions otherwise', () => {
        expect(createInitialSession('value-compounder')).toEqual({
            phase: 'result',
            mode: 'inspect',
            archetypeId: 'value-compounder',
            quizAnswers: null,
        });
        expect(createInitialSession()).toEqual({
            phase: 'answering',
            stepIndex: 0,
            answers: {},
            checkpoint: null,
        });
    });

    it('preserves saved drafts when answering has zero new answers and clears on explicit clear', () => {
        const answers = Object.fromEntries(
            PERSONALITY_QUESTIONS.slice(0, 3).map((q) => [q.id, q.options[0].id]),
        );
        syncDraftStorage({ phase: 'answering', stepIndex: 3, answers, checkpoint: null }, 'value');
        expect(readDraft()).toEqual({ answers, stepIndex: 3, selfDescription: 'value' });

        syncDraftStorage({ phase: 'answering', stepIndex: 0, answers: {}, checkpoint: null }, '');
        expect(readDraft()).not.toBeNull();

        clearDraftStorage();
        expect(readDraft()).toBeNull();
    });

    it('derives checkpoint context and live hint only for fully answered acts', () => {
        const act1Answers = Object.fromEntries(
            PERSONALITY_QUESTIONS.slice(0, 4).map((q) => [q.id, q.options[0].id]),
        );
        const session = {
            phase: 'answering' as const,
            stepIndex: 3,
            answers: act1Answers,
            checkpoint: 0,
        };
        const result = computeLiveQuizResult(session);
        const view = deriveQuizViewModel(session, result);

        expect(computeLiveHint(session, result)).toMatch(/^Leaning: [LQ]$/);
        expect(view.checkpointIndex).toBe(0);
        expect(view.checkpointAct?.axis).toBe('horizon');
        expect(view.sceneAct).toBe(0);
    });
});
