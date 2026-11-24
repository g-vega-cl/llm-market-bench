import { type AtmospherePhase, SceneStage } from '@llm-market-bench/ui-design-system';
import { usePostHog } from '@posthog/react';
import { Link, useRouter } from '@tanstack/react-router';
import { useEffect, useId, useRef } from 'react';
import { CedarRidgeBackdrop } from '~/features/home/backdrop/CedarRidgeBackdrop';
import { SceneHudControls } from '~/features/home/backdrop/SceneHudControls';
import { useDioramaStage } from '~/features/home/backdrop/useDioramaStage';
import { PERSONALITY_QUESTION_COUNT } from '~/features/personality/personality-type-grid';
import { track } from '~/lib/analytics';
import type { RecipeSummaryItem, RecipeUserQuotaStatus } from '../types';
import { BuilderAlignmentCard } from './BuilderAlignmentCard';
import { BuilderCompilePipeline } from './BuilderCompilePipeline';
import { BuilderDescribeStep, BuilderErrorBanner } from './BuilderDescribeStep';
import { BuilderStatusStrip } from './BuilderStatusStrip';
import { BuilderStepper } from './BuilderStepper';
import type { BuilderPhase } from './builder-phases';
import { CompiledBotWorkspace } from './CompiledBotWorkspace';
import { useBuilderChat } from './use-builder-chat';

const MAX_TEXTAREA_HEIGHT_PX = 240;

export interface BuilderChatPanelProps {
    idea?: string;
    redirectTo?: '/build';
    /** Supplied by the route: getRouter() is created without a context object. */
    userId?: string | null;
    initialAtmosphere?: AtmospherePhase;
    initialQuota?: RecipeUserQuotaStatus | null;
    initialUserRecipes?: RecipeSummaryItem[];
}

function phaseBarClass(phase: BuilderPhase): string {
    if (phase === 'queued' || phase === 'compiling' || phase === 'align') return 'bg-accent';
    if (phase === 'question' || phase === 'declined') return 'bg-warning';
    if (phase === 'error') return 'bg-danger';
    return 'bg-voxel-bevel-hi';
}

function resolveIdleStrip(
    phase: BuilderPhase,
    restoredFromBrowser: boolean,
    statusDetail: string | null,
): { label?: string; tone?: 'accent'; detail?: string } {
    if (phase !== 'idle') {
        return { detail: statusDetail ?? undefined };
    }
    if (restoredFromBrowser) {
        return {
            label: 'SAVED IN BROWSER',
            tone: 'accent',
            detail: 'Your saved idea is loaded below — edit or submit to continue.',
        };
    }
    return {
        label: 'STEP 1 · NOW',
        tone: 'accent',
        detail: 'Describe the bot you want — one sentence is enough.',
    };
}

/**
 * Steps 1 & 2 of `/build`: framed on Benchify's Cedar Sanctuary SceneStage so
 * the builder opens with the same living atmosphere as the homepage, then
 * transitions cleanly to the focused CompiledBotWorkspace once compiled.
 */
export function BuilderChatPanel({
    idea,
    redirectTo = '/build',
    userId = null,
    initialAtmosphere,
    initialQuota = null,
    initialUserRecipes = [],
}: BuilderChatPanelProps) {
    const router = useRouter();
    const posthog = usePostHog();
    const textareaRef = useRef<HTMLTextAreaElement>(null);
    const hintId = useId();
    const { atmosphere, paused, cycleAtmosphere, toggleMotion } =
        useDioramaStage(initialAtmosphere);

    const chat = useBuilderChat({
        idea,
        userId,
        onNeedSignIn: async () => {
            await router.navigate({ to: '/login', search: { redirect: redirectTo } });
        },
    });

    // Fire on first interaction, not on mount.
    const opened = useRef(false);
    const onOpen = () => {
        if (opened.current) return;
        opened.current = true;
        track(posthog, 'builder_opened', { seeded: Boolean(idea) });
    };

    // Auto-expand textarea height to fit content up to MAX_TEXTAREA_HEIGHT_PX.
    useEffect(() => {
        const el = textareaRef.current;
        if (!el) return;
        el.style.height = 'auto';
        if (!chat.draft) return;
        const nextHeight = Math.min(el.scrollHeight, MAX_TEXTAREA_HEIGHT_PX);
        if (nextHeight > 0) {
            el.style.height = `${nextHeight}px`;
        }
    }, [chat.draft]);

    const compiledReply = chat.reply?.status === 'ok' ? chat.reply : null;
    if (compiledReply) {
        return (
            <CompiledBotWorkspace
                key={`${compiledReply.strategy.name}-${chat.compileNonce}`}
                initialStrategy={compiledReply.strategy}
                initialQuota={initialQuota}
                initialUserRecipes={initialUserRecipes}
                summary={compiledReply.summary}
                fallback={compiledReply.fallback}
                warning={compiledReply.warning}
                onStartOver={() => chat.reset()}
            />
        );
    }

    const activeAlignment = chat.activeAlignment;
    const isInitialStep = chat.messages.length === 0;
    const pipelinePhase = chat.phase === 'queued' || chat.phase === 'compiling' ? chat.phase : null;
    const activeStep = activeAlignment ? 2 : 1;
    const stripProps = resolveIdleStrip(chat.phase, chat.restoredFromBrowser, chat.statusDetail);
    const alignmentKey = activeAlignment
        ? activeAlignment.questions.map((q) => q.id).join('|')
        : 'align';

    const handleSelectChip = (prompt: string) => {
        onOpen();
        chat.setDraft(prompt);
        textareaRef.current?.focus();
    };

    return (
        <SceneStage
            variant="hero"
            atmosphere={atmosphere}
            motionRole="reactive"
            className="build-stage-viewport flex w-full flex-col text-voxel-ink"
            backdrop={
                <CedarRidgeBackdrop
                    atmosphere={atmosphere}
                    paused={paused}
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
            <div className="flex flex-1 flex-col items-center justify-start gap-[clamp(1rem,2.4vw,1.5rem)] pb-[clamp(0.75rem,4vw,4rem)]">
                <h1 className="sr-only">Build a trading bot from one sentence</h1>

                <div
                    data-testid="builder-stage-card"
                    className="scene-scrim voxel-card flex w-full max-w-3xl flex-col gap-[clamp(0.75rem,1.4vw,1rem)] rounded-none p-[clamp(1rem,2.2vw,1.5rem)] min-w-0"
                >
                    <div
                        aria-hidden="true"
                        data-testid="builder-phase-bar"
                        className={`h-1 w-full rounded-none ${phaseBarClass(chat.phase)}`}
                    />

                    <BuilderStatusStrip
                        phase={chat.phase}
                        elapsedMs={chat.elapsedMs}
                        label={stripProps.label}
                        tone={stripProps.tone}
                        detail={stripProps.detail}
                    />

                    {pipelinePhase ? <BuilderCompilePipeline phase={pipelinePhase} /> : null}

                    {activeAlignment ? (
                        <>
                            {chat.error ? (
                                <BuilderErrorBanner
                                    error={chat.error}
                                    isCompiling={chat.isCompiling}
                                    onRetry={chat.retry}
                                    onUseTemplate={chat.useTemplate}
                                />
                            ) : null}
                            <BuilderAlignmentCard
                                key={alignmentKey}
                                intro={activeAlignment.intro}
                                questions={activeAlignment.questions}
                                isCompiling={chat.isCompiling}
                                onSubmit={(answers) => void chat.submitAlignment(answers)}
                                onSkip={() => void chat.skipAlignment()}
                            />
                        </>
                    ) : (
                        <BuilderDescribeStep
                            chat={chat}
                            userId={userId}
                            isInitialStep={isInitialStep}
                            hintId={hintId}
                            textareaRef={textareaRef}
                            onFocusTextarea={onOpen}
                            onSelectChip={handleSelectChip}
                        />
                    )}

                    <p className="text-xs font-normal text-voxel-muted">
                        Not sure where to start?{' '}
                        <Link
                            to="/personality"
                            className="text-accent underline underline-offset-4 hover:text-accent-hover"
                        >
                            {`Take our ${String(PERSONALITY_QUESTION_COUNT)}-question personality test`}
                        </Link>{' '}
                        or{' '}
                        <Link
                            to="/chat"
                            className="text-accent underline underline-offset-4 hover:text-accent-hover"
                        >
                            talk to our AI advisor
                        </Link>
                        .
                    </p>

                    <BuilderStepper activeStep={activeStep} />
                </div>
            </div>
        </SceneStage>
    );
}
