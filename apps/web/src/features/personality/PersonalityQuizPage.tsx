import { type AtmospherePhase, SceneStage } from '@llm-market-bench/ui-design-system';
import { useEffect, useMemo, useRef, useState } from 'react';
import { GardenBackdrop } from '../home/backdrop/GardenBackdrop';
import { SceneHudControls } from '../home/backdrop/SceneHudControls';
import { syncUrlSearchParam, useDioramaStage } from '../home/backdrop/useDioramaStage';
import { PersonalityQuizStep } from './PersonalityQuizStep';
import { PersonalityResultPanel } from './PersonalityResultPanel';
import {
    type ArchetypeId,
    buildSharedArchetypeResult,
    PERSONALITY_QUESTIONS,
    scorePersonalityQuiz,
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

function createInitialSession(initialArchetype?: ArchetypeId): QuizSession {
    if (initialArchetype) {
        return {
            phase: 'result',
            mode: 'inspect',
            archetypeId: initialArchetype,
            quizAnswers: null,
        };
    }
    return { phase: 'answering', stepIndex: 0, answers: {} };
}

/**
 * Interactive 10-question Investing Personality Test & starter bot matcher on
 * SceneStage with panoramic Cedar Sanctuary backdrop. Uses at most two
 * typography combos (`text-lg font-bold`, `text-xs font-normal`).
 */
export function PersonalityQuizPage({
    initialArchetype,
    initialAtmosphere,
    onArchetypeSearchChange,
}: PersonalityQuizPageProps) {
    const { atmosphere, paused, setPaused, cycleAtmosphere, toggleMotion } =
        useDioramaStage(initialAtmosphere);
    const [session, setSession] = useState<QuizSession>(() =>
        createInitialSession(initialArchetype),
    );
    const [copiedArchetype, setCopiedArchetype] = useState<ArchetypeId | null>(null);
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
            onArchetypeSearchChange(archetypeId);
        } else {
            syncUrlSearchParam('archetype', archetypeId);
        }
    };

    useEffect(() => {
        if (prevInitialRef.current === initialArchetype) return;
        prevInitialRef.current = initialArchetype;
        const normalized = initialArchetype ?? null;
        const idx = pendingSelfSearchesRef.current.indexOf(normalized);
        if (idx !== -1) {
            pendingSelfSearchesRef.current.splice(0, idx + 1);
            return;
        }
        pendingSelfSearchesRef.current = [];
        setSession(createInitialSession(initialArchetype));
        setCopiedArchetype(null);
    }, [initialArchetype]);

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

    const handleSelectOption = (questionId: string, optionId: string) => {
        if (session.phase !== 'answering') return;
        const nextAnswers = { ...session.answers, [questionId]: optionId };
        setCopiedArchetype(null);

        if (session.stepIndex + 1 < PERSONALITY_QUESTIONS.length) {
            setSession({
                phase: 'answering',
                stepIndex: session.stepIndex + 1,
                answers: nextAnswers,
            });
            return;
        }
        const scored = scorePersonalityQuiz(nextAnswers);
        updateArchetypeSearch(scored.primary.archetype.id);
        setSession({
            phase: 'result',
            mode: 'quiz_match',
            quizAnswers: nextAnswers,
        });
    };

    const handlePrevious = () => {
        if (session.phase !== 'answering') return;
        setSession({ ...session, stepIndex: Math.max(0, session.stepIndex - 1) });
    };

    const handleRetake = () => {
        updateArchetypeSearch(null);
        setCopiedArchetype(null);
        setSession({ phase: 'answering', stepIndex: 0, answers: {} });
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
        const shareUrl = `${window.location.origin}/personality?archetype=${archetypeId}`;
        try {
            await navigator.clipboard.writeText(shareUrl);
            if (activeResultArchetypeRef.current === archetypeId) {
                setCopiedArchetype(archetypeId);
            }
        } catch {
            // Clipboard permission denied or unavailable; omit feedback badge.
        }
    };

    const liveHint =
        liveQuizResult.answeredCount > 0
            ? `Leaning: ${liveQuizResult.primary.archetype.title}`
            : '';

    const canReturnToQuizMatch =
        session.phase === 'result' && session.mode === 'inspect' && session.quizAnswers !== null;

    return (
        <SceneStage
            variant="hero"
            atmosphere={atmosphere}
            motionRole="reactive"
            className="min-h-[calc(100dvh-3.875rem)] flex w-full flex-col text-voxel-ink"
            backdrop={
                <GardenBackdrop
                    atmosphere={atmosphere}
                    paused={paused}
                    onPausedChange={setPaused}
                    showControls={false}
                    className="h-full w-full"
                />
            }
            controls={
                <SceneHudControls
                    atmosphere={atmosphere}
                    paused={paused}
                    onCycleAtmosphere={cycleAtmosphere}
                    onTogglePaused={toggleMotion}
                />
            }
        >
            <div className="flex flex-1 flex-col items-center justify-start gap-6 pb-16">
                <header className="flex flex-col items-center gap-2 text-center">
                    <p className="home-hero-copy text-xs font-normal tracking-wider uppercase text-accent">
                        Benchify Investing Diagnostic
                    </p>
                    <h1 className="home-hero-heading text-lg font-bold text-voxel-ink">
                        Discover your investing style &amp; best trading bot.
                    </h1>
                    <p className="home-hero-copy max-w-prose text-xs font-normal leading-relaxed text-voxel-ink">
                        Ten market scenarios score your Horizon, Signal Anchor, Crowd Stance, and
                        Execution Tempo — pairing you with your matched starter trading recipe.
                    </p>
                </header>

                {session.phase === 'answering' ? (
                    <PersonalityQuizStep
                        question={PERSONALITY_QUESTIONS[session.stepIndex]}
                        stepIndex={session.stepIndex}
                        totalQuestions={PERSONALITY_QUESTIONS.length}
                        chosenOptionId={
                            session.answers[PERSONALITY_QUESTIONS[session.stepIndex].id]
                        }
                        liveHint={liveHint}
                        onSelectOption={handleSelectOption}
                        onPrevious={handlePrevious}
                        onBrowseAll={() => handleInspectArchetype('value-compounder')}
                    />
                ) : (
                    <PersonalityResultPanel
                        result={liveQuizResult}
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
