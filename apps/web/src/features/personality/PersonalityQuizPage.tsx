import { type AtmospherePhase, Button, SceneStage } from '@llm-market-bench/ui-design-system';
import { usePostHog } from '@posthog/react';
import { useEffect, useMemo, useRef, useState } from 'react';
import { track } from '~/lib/analytics';
import {
    PersonalityBackdrop,
    type PersonalitySceneAct,
} from '../home/backdrop/PersonalityBackdrop';
import { SceneHudControls } from '../home/backdrop/SceneHudControls';
import { syncUrlSearchParam, useDioramaStage } from '../home/backdrop/useDioramaStage';
import { ActCheckpointPlaque } from './ActCheckpointPlaque';
import { PersonalityQuizStep } from './PersonalityQuizStep';
import { PersonalityResultPanel } from './PersonalityResultPanel';
import {
    ARCHETYPES,
    type ArchetypeId,
    AXIS_DEFINITIONS,
    buildSharedArchetypeResult,
    PERSONALITY_QUESTIONS,
    QUIZ_ACTS,
    scorePersonalityQuiz,
    TYPE_LETTERS,
} from './personality-data';

export interface PersonalityQuizPageProps {
    /** Optional archetype pre-selected via `?archetype=` shareable URL search param. */
    initialArchetype?: ArchetypeId;
    /** SSR-resolved market-ET atmosphere phase passed from route loader to eliminate initial flash. */
    initialAtmosphere?: AtmospherePhase;
    /** Optional router search updater passed by the `/personality` route to avoid history split-brain. */
    onArchetypeSearchChange?: (archetypeId: ArchetypeId | null) => void;
}

/**
 * Discriminated union preserving finished quiz answers while browsing other
 * archetypes, making illegal `{ null, null }` result states unrepresentable.
 */
type QuizSession =
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

/**
 * How many self-emitted `?archetype=` values we remember. Bounded so a stale
 * entry can never suppress a genuinely external navigation indefinitely.
 */
const MAX_PENDING_SELF_SEARCHES = 4;

const QUESTIONS_PER_ACT = 4;
const RESUME_STORAGE_KEY = 'benchify:personality-draft';
const RESUME_MIN_ANSWERED = 3;

interface QuizDraft {
    answers: Record<string, string>;
    stepIndex: number;
    selfDescription: string;
}

function createInitialSession(initialArchetype?: ArchetypeId): QuizSession {
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

function readDraft(): QuizDraft | null {
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
        if (onArchetypeSearchChange) {
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
        } else {
            syncUrlSearchParam('archetype', archetypeId);
        }
    };

    useEffect(() => {
        if (prevInitialRef.current === initialArchetype) return;
        prevInitialRef.current = initialArchetype;
        const normalized = initialArchetype ?? null;
        // The router can coalesce, dedupe or reorder rapid navigations, so accept
        // ANY recently self-emitted value rather than only the head. The queue is
        // bounded (see `MAX_PENDING_SELF_SEARCHES`) so a stale entry cannot
        // suppress a genuinely external navigation forever.
        const idx = pendingSelfSearchesRef.current.indexOf(normalized);
        if (idx !== -1) {
            pendingSelfSearchesRef.current.splice(0, idx + 1);
            return;
        }
        pendingSelfSearchesRef.current = [];
        setSession(createInitialSession(initialArchetype));
        setCopiedArchetype(null);
    }, [initialArchetype]);

    // Resume is read only after hydration: touching storage during render would
    // desync SSR from the client. A draft needs >= RESUME_MIN_ANSWERED answers.
    useEffect(() => {
        setDraft(readDraft());
    }, []);

    useEffect(() => {
        track(posthog, 'quiz_started');
    }, [posthog]);

    useEffect(() => {
        if (session.phase !== 'answering') return;
        const answered = Object.keys(session.answers).length;
        try {
            if (answered === 0) {
                window.localStorage.removeItem(RESUME_STORAGE_KEY);
                return;
            }
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
    }, [session, selfDescription]);

    const liveQuizResult = useMemo(() => {
        if (session.phase === 'answering') {
            return scorePersonalityQuiz(session.answers);
        }
        if (session.mode === 'inspect') {
            return buildSharedArchetypeResult(session.archetypeId);
        }
        return scorePersonalityQuiz(session.quizAnswers);
    }, [session]);

    const currentResultArchetypeId =
        session.phase === 'result' ? liveQuizResult.primary.archetype.id : null;

    useEffect(() => {
        activeResultArchetypeRef.current = currentResultArchetypeId;
    }, [currentResultArchetypeId]);

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
            act: currentAct.axis,
            option: optionId,
        });

        if (session.stepIndex + 1 >= PERSONALITY_QUESTIONS.length) {
            finishQuiz(nextAnswers);
            return;
        }

        // Closing an act shows its checkpoint plaque before the next question,
        // so the visitor sees the letter they just earned in place.
        const closesAct = (session.stepIndex + 1) % QUESTIONS_PER_ACT === 0;
        if (closesAct) {
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
        try {
            window.localStorage.removeItem(RESUME_STORAGE_KEY);
        } catch {
            // Storage disabled; nothing to clear.
        }
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
            return {
                phase: 'result',
                mode: 'inspect',
                archetypeId,
                quizAnswers,
            };
        });
    };

    const handleReturnToQuizMatch = () => {
        if (session.phase !== 'result' || !session.quizAnswers) return;
        const scored = scorePersonalityQuiz(session.quizAnswers);
        updateArchetypeSearch(scored.primary.archetype.id);
        setCopiedArchetype(null);
        setSession({
            phase: 'result',
            mode: 'quiz_match',
            quizAnswers: session.quizAnswers,
        });
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

    // Only letters whose whole act has been answered are shown, so a visitor is
    // never handed three letters derived from questions they have not seen yet.
    const hintAnswers = session.phase === 'answering' ? session.answers : session.quizAnswers;
    const revealedLetters = hintAnswers
        ? liveQuizResult.letters
              .filter((letter) =>
                  PERSONALITY_QUESTIONS.filter((q) => q.act === letter.axis).every(
                      (q) => hintAnswers[q.id] !== undefined,
                  ),
              )
              .map((letter) => letter.letter)
              .join('')
        : '';
    const liveHint = revealedLetters ? `Leaning: ${revealedLetters}` : '';

    // The share route (/personality/t/<CODE>) has an archetype-specific document
    // title, so its page heading names the same archetype instead of the generic
    // tool. A retake keeps the URL, so follow the live result once the visitor has
    // scored a new one — otherwise the heading would name the archetype they left.
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

    // The backdrop follows the quiz, never the sky: the Sky HUD stays the sole
    // owner of atmosphere. A checkpoint holds the just-settled act; the result
    // lights all four landmarks. A zero-act fallback guards an act-less render.
    const sceneAct: PersonalitySceneAct =
        session.phase === 'result'
            ? 'result'
            : ((session.checkpoint ?? currentActIndex) as PersonalitySceneAct);

    const checkpointAct =
        session.phase === 'answering' && session.checkpoint !== null
            ? QUIZ_ACTS[session.checkpoint]
            : undefined;
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

    const showResume =
        draft !== null &&
        session.phase === 'answering' &&
        Object.keys(session.answers).length === 0;
    const draftActNumber = draft ? Math.floor(draft.stepIndex / QUESTIONS_PER_ACT) + 1 : 1;

    const canReturnToQuizMatch =
        session.phase === 'result' && session.mode === 'inspect' && session.quizAnswers !== null;

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
                    act={sceneAct}
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
                <h1 className="sr-only">{pageHeading}</h1>

                {showResume && draft ? (
                    <div
                        data-testid="resume-quiz"
                        className="scene-scrim voxel-trough flex w-full max-w-2xl flex-col gap-2 rounded-none p-4"
                    >
                        <p className="text-sm font-bold text-voxel-ink">
                            {`You left off in Act ${String(draftActNumber)}`}
                        </p>
                        <p className="text-xs font-normal text-voxel-muted">
                            {`${String(Object.keys(draft.answers).length)} of ${String(
                                PERSONALITY_QUESTIONS.length,
                            )} answers saved on this device.`}
                        </p>
                        <div className="flex flex-wrap gap-2">
                            <Button
                                type="button"
                                size="sm"
                                variant="solid"
                                colorScheme="accent"
                                data-testid="resume-quiz-button"
                                onClick={handleResume}
                            >
                                {`Resume Act ${String(draftActNumber)}`}
                            </Button>
                            <Button
                                type="button"
                                size="sm"
                                variant="outline"
                                colorScheme="neutral"
                                onClick={() => setDraft(null)}
                            >
                                Start over
                            </Button>
                        </div>
                    </div>
                ) : null}

                {session.phase === 'answering' ? (
                    session.checkpoint !== null && checkpointAct && checkpointLetter ? (
                        <ActCheckpointPlaque
                            actTitle={checkpointAct.title}
                            actIndex={session.checkpoint}
                            totalActs={QUIZ_ACTS.length}
                            letter={checkpointLetter.letter}
                            poleLabel={checkpointPoleLabel}
                            strength={checkpointLetter.strength}
                            value={checkpointLetter.value}
                            onContinue={handleContinue}
                        />
                    ) : (
                        <PersonalityQuizStep
                            question={PERSONALITY_QUESTIONS[session.stepIndex]}
                            stepIndex={session.stepIndex}
                            totalQuestions={PERSONALITY_QUESTIONS.length}
                            actTitle={currentAct.title}
                            actIndex={currentActIndex}
                            totalActs={QUIZ_ACTS.length}
                            chosenOptionId={
                                session.answers[PERSONALITY_QUESTIONS[session.stepIndex].id]
                            }
                            liveHint={liveHint}
                            showSelfDescription={currentAct.axis === 'cadence'}
                            selfDescription={selfDescription}
                            onSelfDescriptionChange={setSelfDescription}
                            onSelectOption={handleSelectOption}
                            onPrevious={handlePrevious}
                            onBrowseAll={() => handleInspectArchetype('value-compounder')}
                        />
                    )
                ) : (
                    <PersonalityResultPanel
                        result={liveQuizResult}
                        selfDescription={selfDescription}
                        copiedLink={copiedArchetype === liveQuizResult.primary.archetype.id}
                        canReturnToQuizMatch={canReturnToQuizMatch}
                        onCopyShareUrl={(id) => void handleCopyShareUrl(id)}
                        onReturnToQuizMatch={handleReturnToQuizMatch}
                        onRetake={handleRetake}
                        onInspectArchetype={handleInspectArchetype}
                    />
                )}
            </div>
        </SceneStage>
    );
}
