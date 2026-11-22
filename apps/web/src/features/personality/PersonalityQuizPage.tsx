import { type AtmospherePhase, SceneStage } from '@llm-market-bench/ui-design-system';
import { useEffect, useMemo, useState } from 'react';
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
}

/**
 * Discriminated union making incoherent partial-quiz + inspect states unrepresentable.
 */
type QuizSession =
    | {
          phase: 'answering';
          stepIndex: number;
          answers: Record<string, string>;
      }
    | {
          phase: 'result';
          source: 'quiz';
          answers: Record<string, string>;
      }
    | {
          phase: 'result';
          source: 'inspect';
          archetypeId: ArchetypeId;
      };

function createInitialSession(initialArchetype?: ArchetypeId): QuizSession {
    if (initialArchetype) {
        return {
            phase: 'result',
            source: 'inspect',
            archetypeId: initialArchetype,
        };
    }
    return { phase: 'answering', stepIndex: 0, answers: {} };
}

/**
 * Interactive 10-question Investing Personality Test & starter bot matcher on
 * SceneStage with panoramic Cedar Sanctuary backdrop. Uses at most two
 * typography combos (`text-xs font-normal`, `text-sm font-bold`).
 */
export function PersonalityQuizPage({
    initialArchetype,
    initialAtmosphere,
}: PersonalityQuizPageProps) {
    const { atmosphere, paused, setPaused, cycleAtmosphere, toggleMotion } =
        useDioramaStage(initialAtmosphere);
    const [session, setSession] = useState<QuizSession>(() =>
        createInitialSession(initialArchetype),
    );
    const [copiedLink, setCopiedLink] = useState(false);

    useEffect(() => {
        if (initialArchetype) {
            setSession({
                phase: 'result',
                source: 'inspect',
                archetypeId: initialArchetype,
            });
            setCopiedLink(false);
        }
    }, [initialArchetype]);

    const liveQuizResult = useMemo(
        () =>
            session.phase !== 'result' || session.source === 'quiz'
                ? scorePersonalityQuiz(session.answers)
                : buildSharedArchetypeResult(session.archetypeId),
        [session],
    );

    const handleSelectOption = (questionId: string, optionId: string) => {
        if (session.phase !== 'answering') return;
        const nextAnswers = { ...session.answers, [questionId]: optionId };
        setCopiedLink(false);

        if (session.stepIndex + 1 < PERSONALITY_QUESTIONS.length) {
            setSession({
                phase: 'answering',
                stepIndex: session.stepIndex + 1,
                answers: nextAnswers,
            });
            return;
        }
        const scored = scorePersonalityQuiz(nextAnswers);
        syncUrlSearchParam('archetype', scored.primary.archetype.id);
        setSession({
            phase: 'result',
            source: 'quiz',
            answers: nextAnswers,
        });
    };

    const handlePrevious = () => {
        if (session.phase !== 'answering') return;
        setSession({ ...session, stepIndex: Math.max(0, session.stepIndex - 1) });
    };

    const handleRetake = () => {
        syncUrlSearchParam('archetype', null);
        setCopiedLink(false);
        setSession({ phase: 'answering', stepIndex: 0, answers: {} });
    };

    const handleInspectArchetype = (archetypeId: ArchetypeId) => {
        syncUrlSearchParam('archetype', archetypeId);
        setCopiedLink(false);
        setSession({ phase: 'result', source: 'inspect', archetypeId });
    };

    const handleCopyShareUrl = async (archetypeId: ArchetypeId) => {
        if (typeof window === 'undefined' || !navigator.clipboard?.writeText) return;
        const shareUrl = `${window.location.origin}/personality?archetype=${archetypeId}`;
        try {
            await navigator.clipboard.writeText(shareUrl);
            setCopiedLink(true);
        } catch {
            // Clipboard permission denied or unavailable; omit feedback badge.
        }
    };

    const liveHint =
        liveQuizResult.answeredCount > 0
            ? `Leaning: ${liveQuizResult.primary.archetype.title}`
            : '';

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
                    <p className="home-hero-copy text-xs font-normal tracking-[0.24em] uppercase text-accent">
                        Benchify Investing Diagnostic
                    </p>
                    <h1 className="home-hero-heading max-w-[22ch] text-balance text-[clamp(1.75rem,4vw,2.75rem)] font-bold leading-[1.08] text-voxel-ink">
                        Discover your investing style &amp; best trading bot.
                    </h1>
                    <p className="home-hero-copy max-w-[54ch] text-xs font-normal leading-relaxed text-voxel-ink">
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
                        copiedLink={copiedLink}
                        onCopyShareUrl={(id) => void handleCopyShareUrl(id)}
                        onRetake={handleRetake}
                        onInspectArchetype={handleInspectArchetype}
                    />
                )}
            </div>
        </SceneStage>
    );
}
