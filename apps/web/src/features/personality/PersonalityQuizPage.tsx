import { type AtmospherePhase, SceneStage } from '@llm-market-bench/ui-design-system';
import { usePostHog } from '@posthog/react';
import { useEffect, useMemo, useRef, useState } from 'react';
import { track } from '~/lib/analytics';
import { PersonalityBackdrop } from '../home/backdrop/PersonalityBackdrop';
import { SceneHudControls } from '../home/backdrop/SceneHudControls';
import { syncUrlSearchParam, useDioramaStage } from '../home/backdrop/useDioramaStage';
import { ActCheckpointPlaque } from './ActCheckpointPlaque';
import { PersonalityQuizStep, QuizSelfDescriptionTrough } from './PersonalityQuizStep';
import { PersonalityResultPanel } from './PersonalityResultPanel';
import {
    ARCHETYPES,
    type ArchetypeId,
    PERSONALITY_QUESTIONS,
    QUIZ_ACTS,
    scorePersonalityQuiz,
} from './personality-data';
import { QuizStepHeightSizer } from './QuizStepHeightSizer';
import {
    clearDraftStorage,
    computeLiveQuizResult,
    createInitialSession,
    deriveQuizViewModel,
    MAX_PENDING_SELF_SEARCHES,
    QUESTIONS_PER_ACT,
    type QuizDraft,
    type QuizSession,
    readDraft,
    syncDraftStorage,
} from './quiz-session-helpers';
import { ResumeDraftBanner } from './ResumeDraftBanner';

export interface PersonalityQuizPageProps {
    /** Optional archetype pre-selected via `?archetype=` shareable URL search param. */
    initialArchetype?: ArchetypeId;
    /** SSR-resolved market-ET atmosphere phase passed from route loader to eliminate initial flash. */
    initialAtmosphere?: AtmospherePhase;
    /** Optional router search updater passed by the `/personality` route to avoid history split-brain. */
    onArchetypeSearchChange?: (archetypeId: ArchetypeId | null) => void;
}

/**
 * Interactive 16-question Investing Personality Test & starter bot matcher on
 * SceneStage with panoramic Cedar Sanctuary backdrop. The page opens straight
 * into Act 1 with no visible headline block — the route title and an sr-only h1
 * carry the name — so the first question sits as close to the fold as the scene
 * allows.
 */
export function PersonalityQuizPage({
    initialArchetype,
    initialAtmosphere,
    onArchetypeSearchChange,
}: PersonalityQuizPageProps) {
    const { atmosphere, motion, cycleAtmosphere, toggleMotion } =
        useDioramaStage(initialAtmosphere);
    const posthog = usePostHog();
    const startedAtRef = useRef<number>(Date.now());
    const [session, setSession] = useState<QuizSession>(() =>
        createInitialSession(initialArchetype),
    );
    const [copiedArchetype, setCopiedArchetype] = useState<ArchetypeId | null>(null);
    const [selfDescription, setSelfDescription] = useState('');
    const [draft, setDraft] = useState<QuizDraft | null>(null);
    const prevInitialRef = useRef<ArchetypeId | undefined>(initialArchetype);
    const pendingSelfSearchesRef = useRef<Array<ArchetypeId | null>>([]);
    const activeResultArchetypeRef = useRef<ArchetypeId | null>(initialArchetype ?? null);

    const updateArchetypeSearch = (archetypeId: ArchetypeId | null) => {
        if (!onArchetypeSearchChange) {
            syncUrlSearchParam('archetype', archetypeId);
            return;
        }
        if (
            pendingSelfSearchesRef.current.length === 0 &&
            (initialArchetype ?? null) === archetypeId
        ) {
            return;
        }
        pendingSelfSearchesRef.current.push(archetypeId);
        if (pendingSelfSearchesRef.current.length > MAX_PENDING_SELF_SEARCHES) {
            pendingSelfSearchesRef.current.splice(
                0,
                pendingSelfSearchesRef.current.length - MAX_PENDING_SELF_SEARCHES,
            );
        }
        onArchetypeSearchChange(archetypeId);
    };

    useEffect(() => {
        if (prevInitialRef.current === initialArchetype) return;
        prevInitialRef.current = initialArchetype;
        const normalized = initialArchetype ?? null;
        // Accept ANY recently self-emitted value so coalesced router updates do
        // not wipe finished quiz answers, while external changes re-seed.
        const idx = pendingSelfSearchesRef.current.indexOf(normalized);
        if (idx !== -1) {
            pendingSelfSearchesRef.current.splice(0, idx + 1);
            return;
        }
        pendingSelfSearchesRef.current = [];
        setSession(createInitialSession(initialArchetype));
        setCopiedArchetype(null);
    }, [initialArchetype]);

    useEffect(() => {
        setDraft(readDraft());
    }, []);

    useEffect(() => {
        track(posthog, 'quiz_started');
    }, [posthog]);

    useEffect(() => {
        syncDraftStorage(session, selfDescription);
    }, [session, selfDescription]);

    const liveQuizResult = useMemo(() => computeLiveQuizResult(session), [session]);
    const currentResultArchetypeId =
        session.phase === 'result' ? liveQuizResult.primary.archetype.id : null;

    useEffect(() => {
        activeResultArchetypeRef.current = currentResultArchetypeId;
    }, [currentResultArchetypeId]);

    const view = deriveQuizViewModel(session, liveQuizResult, initialArchetype);

    const finishQuiz = (answers: Record<string, string>) => {
        const scored = scorePersonalityQuiz(answers);
        updateArchetypeSearch(scored.primary.archetype.id);
        track(posthog, 'quiz_completed', {
            code: scored.code,
            strength: scored.letters.map((letter) => letter.strength).join(','),
            seconds: Math.max(0, Math.round((Date.now() - startedAtRef.current) / 1000)),
        });
        setSession({ phase: 'result', mode: 'quiz_match', quizAnswers: answers });
    };

    const handleSelectOption = (questionId: string, optionId: string) => {
        if (session.phase !== 'answering') return;
        const nextAnswers = { ...session.answers, [questionId]: optionId };
        setCopiedArchetype(null);
        track(posthog, 'quiz_question_answered', {
            index: session.stepIndex,
            act: view.currentAct.axis,
            option: optionId,
        });
        if (session.stepIndex + 1 >= PERSONALITY_QUESTIONS.length) {
            finishQuiz(nextAnswers);
            return;
        }
        if ((session.stepIndex + 1) % QUESTIONS_PER_ACT === 0) {
            const actIndex = Math.floor(session.stepIndex / QUESTIONS_PER_ACT);
            const settled = scorePersonalityQuiz(nextAnswers).letters.find(
                (letter) => letter.axis === QUIZ_ACTS[actIndex].axis,
            );
            track(posthog, 'quiz_act_completed', {
                act: actIndex,
                letter: settled?.letter ?? '',
                strength: settled?.strength ?? '',
            });
            setSession({
                phase: 'answering',
                stepIndex: session.stepIndex,
                answers: nextAnswers,
                checkpoint: actIndex,
            });
            return;
        }
        setSession({
            phase: 'answering',
            stepIndex: session.stepIndex + 1,
            answers: nextAnswers,
            checkpoint: null,
        });
    };

    const handleContinue = () => {
        setSession((prev) =>
            prev.phase === 'answering'
                ? {
                      ...prev,
                      stepIndex: Math.min(PERSONALITY_QUESTIONS.length - 1, prev.stepIndex + 1),
                      checkpoint: null,
                  }
                : prev,
        );
    };

    const handlePrevious = () => {
        if (session.phase !== 'answering') return;
        if (session.checkpoint !== null) {
            setSession({ ...session, checkpoint: null });
            return;
        }
        setSession({ ...session, stepIndex: Math.max(0, session.stepIndex - 1) });
    };

    const handleRetake = () => {
        updateArchetypeSearch(null);
        setCopiedArchetype(null);
        setSelfDescription('');
        setDraft(null);
        clearDraftStorage();
        setSession({ phase: 'answering', stepIndex: 0, answers: {}, checkpoint: null });
    };

    const handleResume = () => {
        if (!draft) return;
        setSession({
            phase: 'answering',
            stepIndex: draft.stepIndex,
            answers: draft.answers,
            checkpoint: null,
        });
        setSelfDescription(draft.selfDescription);
        setDraft(null);
    };

    const handleInspectArchetype = (archetypeId: ArchetypeId) => {
        updateArchetypeSearch(archetypeId);
        setCopiedArchetype(null);
        setSession((prev) => {
            const quizAnswers = prev.phase === 'result' ? prev.quizAnswers : null;
            if (
                quizAnswers &&
                scorePersonalityQuiz(quizAnswers).primary.archetype.id === archetypeId
            ) {
                return { phase: 'result', mode: 'quiz_match', quizAnswers };
            }
            return { phase: 'result', mode: 'inspect', archetypeId, quizAnswers };
        });
    };

    const handleReturnToQuizMatch = () => {
        if (session.phase !== 'result' || !session.quizAnswers) return;
        const scored = scorePersonalityQuiz(session.quizAnswers);
        updateArchetypeSearch(scored.primary.archetype.id);
        setCopiedArchetype(null);
        setSession({ phase: 'result', mode: 'quiz_match', quizAnswers: session.quizAnswers });
    };

    const handleCopyShareUrl = async (archetypeId: ArchetypeId) => {
        if (typeof window === 'undefined' || !navigator.clipboard?.writeText) return;
        const shareUrl = `${window.location.origin}/personality/t/${ARCHETYPES[archetypeId].code}`;
        try {
            await navigator.clipboard.writeText(shareUrl);
            if (activeResultArchetypeRef.current === archetypeId) {
                setCopiedArchetype(archetypeId);
            }
        } catch {
            // Clipboard permission denied or unavailable; omit feedback badge.
        }
    };

    const showResume =
        draft !== null &&
        session.phase === 'answering' &&
        Object.keys(session.answers).length === 0;

    return (
        <SceneStage
            variant="hero"
            atmosphere={atmosphere}
            motionRole="reactive"
            className="flex w-full flex-col text-voxel-ink"
            backdrop={
                <PersonalityBackdrop
                    atmosphere={atmosphere}
                    motion={motion}
                    act={view.sceneAct}
                    className="h-full w-full"
                />
            }
            controls={
                <SceneHudControls
                    atmosphere={atmosphere}
                    motion={motion}
                    onCycleAtmosphere={cycleAtmosphere}
                    onTogglePaused={toggleMotion}
                />
            }
        >
            <div className="flex flex-1 flex-col items-center justify-start gap-6 pb-16">
                <h1 className="sr-only">{view.pageHeading}</h1>

                {session.phase === 'answering' ? (
                    <>
                        <div className="quiz-card-container grid w-full max-w-2xl grid-cols-1 min-w-0">
                            <QuizStepHeightSizer />
                            {view.checkpointIndex !== null &&
                            view.checkpointAct &&
                            view.checkpointLetter ? (
                                <ActCheckpointPlaque
                                    actTitle={view.checkpointAct.title}
                                    actIndex={view.checkpointIndex}
                                    totalActs={QUIZ_ACTS.length}
                                    letter={view.checkpointLetter.letter}
                                    poleLabel={view.checkpointPoleLabel}
                                    strength={view.checkpointLetter.strength}
                                    value={view.checkpointLetter.value}
                                    onContinue={handleContinue}
                                />
                            ) : (
                                <PersonalityQuizStep
                                    question={PERSONALITY_QUESTIONS[session.stepIndex]}
                                    stepIndex={session.stepIndex}
                                    totalQuestions={PERSONALITY_QUESTIONS.length}
                                    actTitle={view.currentAct.title}
                                    actIndex={view.currentActIndex}
                                    totalActs={QUIZ_ACTS.length}
                                    chosenOptionId={
                                        session.answers[PERSONALITY_QUESTIONS[session.stepIndex].id]
                                    }
                                    liveHint={view.liveHint}
                                    onSelectOption={handleSelectOption}
                                    onPrevious={handlePrevious}
                                    onBrowseAll={() => handleInspectArchetype('value-compounder')}
                                />
                            )}
                        </div>

                        {view.checkpointIndex === null && view.currentAct.axis === 'cadence' ? (
                            <QuizSelfDescriptionTrough
                                selfDescription={selfDescription}
                                onChange={setSelfDescription}
                            />
                        ) : null}
                    </>
                ) : (
                    <PersonalityResultPanel
                        result={liveQuizResult}
                        selfDescription={selfDescription}
                        copiedLink={copiedArchetype === liveQuizResult.primary.archetype.id}
                        canReturnToQuizMatch={view.canReturnToQuizMatch}
                        onCopyShareUrl={(id) => void handleCopyShareUrl(id)}
                        onReturnToQuizMatch={handleReturnToQuizMatch}
                        onRetake={handleRetake}
                        onInspectArchetype={handleInspectArchetype}
                    />
                )}

                {showResume && draft ? (
                    <ResumeDraftBanner
                        draft={draft}
                        onResume={handleResume}
                        onDismiss={() => {
                            clearDraftStorage();
                            setDraft(null);
                        }}
                    />
                ) : null}
            </div>
        </SceneStage>
    );
}
