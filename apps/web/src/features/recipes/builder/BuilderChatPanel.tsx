import { type AtmospherePhase, Button, SceneStage } from '@llm-market-bench/ui-design-system';
import { usePostHog } from '@posthog/react';
import { Link, useRouter } from '@tanstack/react-router';
import { type KeyboardEvent, type RefObject, useEffect, useId, useRef } from 'react';
import { GardenBackdrop } from '~/features/home/backdrop/GardenBackdrop';
import { SceneHudControls } from '~/features/home/backdrop/SceneHudControls';
import { useDioramaStage } from '~/features/home/backdrop/useDioramaStage';
import { PERSONALITY_QUESTION_COUNT } from '~/features/personality/personality-type-grid';
import { track } from '~/lib/analytics';
import type { RecipeSummaryItem, RecipeUserQuotaStatus } from '../types';
import { BuilderAlignmentCard } from './BuilderAlignmentCard';
import { BuilderCompilePipeline } from './BuilderCompilePipeline';
import { BuilderConversation } from './BuilderConversation';
import { BuilderStatusStrip } from './BuilderStatusStrip';
import { BuilderStepper } from './BuilderStepper';
import type { BuilderPhase } from './builder-phases';
import { CompiledBotWorkspace } from './CompiledBotWorkspace';
import { MAX_TURN_CHARS } from './compiler';
import { type BuilderChat, useBuilderChat } from './use-builder-chat';

const MAX_TEXTAREA_HEIGHT_PX = 240;

const STARTER_IDEA_CHIPS = [
    {
        label: 'AI Capex Chips',
        prompt: 'Buy profitable semiconductor leaders on AI data-center capex news with RSI under 65 and positive MACD.',
    },
    {
        label: 'Earnings Drift',
        prompt: 'Trade post-earnings drift on profitable tech stocks that beat EPS and raised guidance without already spiking over 8%.',
    },
    {
        label: 'Quality Pullback',
        prompt: 'Buy high-ROE cash-generative companies pulling back below VWAP with RSI under 40.',
    },
    {
        label: 'Contrarian Fear',
        prompt: 'Buy oversold large-cap leaders when market sentiment is fearful and exit into euphoria.',
    },
] as const;

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

function BuilderErrorBanner({
    error,
    isCompiling,
    onRetry,
    onUseTemplate,
}: {
    error: string;
    isCompiling: boolean;
    onRetry: () => void;
    onUseTemplate: () => void;
}) {
    return (
        <div
            role="alert"
            className="voxel-trough bg-voxel-trough flex flex-wrap items-center justify-between gap-2 p-3 min-w-0"
        >
            <p className="text-xs font-normal text-danger min-w-0 break-words">{error}</p>
            <div className="flex flex-wrap items-center gap-2 shrink-0 min-w-0">
                <Button
                    size="sm"
                    variant="outline"
                    colorScheme="neutral"
                    onClick={onRetry}
                    disabled={isCompiling}
                >
                    Try again
                </Button>
                <Button
                    size="sm"
                    variant="outline"
                    colorScheme="neutral"
                    onClick={onUseTemplate}
                    disabled={isCompiling}
                >
                    Use closest template
                </Button>
            </div>
        </div>
    );
}

function BuilderStarterChips({
    disabled,
    onSelect,
}: {
    disabled: boolean;
    onSelect: (prompt: string) => void;
}) {
    return (
        <div
            data-testid="builder-starter-chips"
            className="voxel-trough bg-voxel-trough rounded-none p-3 flex flex-col gap-2 min-w-0"
        >
            <span className="text-xs font-normal text-voxel-muted">
                Start with a template idea or write your own below:
            </span>
            <div className="flex flex-wrap gap-2 min-w-0">
                {STARTER_IDEA_CHIPS.map((chip) => (
                    <Button
                        key={chip.label}
                        type="button"
                        size="sm"
                        variant="outline"
                        colorScheme="neutral"
                        disabled={disabled}
                        onClick={() => onSelect(chip.prompt)}
                    >
                        {chip.label}
                    </Button>
                ))}
            </div>
        </div>
    );
}

function BuilderDescribeStep({
    chat,
    userId,
    isInitialStep,
    hintId,
    textareaRef,
    onFocusTextarea,
    onSelectChip,
}: {
    chat: BuilderChat;
    userId: string | null;
    isInitialStep: boolean;
    hintId: string;
    textareaRef: RefObject<HTMLTextAreaElement | null>;
    onFocusTextarea: () => void;
    onSelectChip: (prompt: string) => void;
}) {
    const handleTextareaKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
        if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') {
            event.preventDefault();
            if (chat.draft.trim() && !chat.isCompiling) {
                void chat.send(chat.draft);
            }
        }
    };

    return (
        <>
            <BuilderConversation
                messages={chat.messages}
                messageIds={chat.messageIds}
                reply={chat.reply}
                pendingIdea={chat.pendingIdea}
                isSignedIn={Boolean(userId)}
                isCompiling={chat.isCompiling}
                onSend={(text) => void chat.send(text)}
            />

            {chat.error ? (
                <BuilderErrorBanner
                    error={chat.error}
                    isCompiling={chat.isCompiling}
                    onRetry={chat.retry}
                    onUseTemplate={chat.useTemplate}
                />
            ) : null}

            {userId ? null : (
                <p className="text-xs font-normal text-voxel-muted">
                    Sign in to build — your idea is saved in this browser.
                </p>
            )}

            {isInitialStep && !chat.pendingIdea ? (
                <BuilderStarterChips disabled={chat.isCompiling} onSelect={onSelectChip} />
            ) : null}

            <form
                className="flex flex-col gap-3 min-w-0"
                onSubmit={(event) => {
                    event.preventDefault();
                    void chat.send(chat.draft);
                }}
            >
                <div className="voxel-trough bg-voxel-trough rounded-none flex w-full p-3 transition-colors focus-within:ring-2 focus-within:ring-accent/40">
                    <textarea
                        ref={textareaRef}
                        rows={3}
                        aria-label="Describe your trading bot"
                        aria-describedby={hintId}
                        placeholder="Describe what your bot should trade and when to enter or exit..."
                        value={chat.draft}
                        onChange={(event) => chat.setDraft(event.target.value)}
                        onKeyDown={handleTextareaKeyDown}
                        onFocus={onFocusTextarea}
                        maxLength={MAX_TURN_CHARS}
                        className="w-full min-h-[4.5rem] max-h-60 resize-none overflow-y-auto bg-transparent text-xs font-normal leading-relaxed text-voxel-ink placeholder:text-voxel-muted focus:outline-none"
                    />
                </div>
                <div className="flex flex-wrap items-center justify-between gap-4 min-w-0">
                    <span id={hintId} className="text-xs font-normal text-voxel-muted min-w-0">
                        {`${String(chat.draft.length)} / ${String(MAX_TURN_CHARS)} · Ctrl/⌘+Enter to submit`}
                    </span>
                    <Button
                        type="submit"
                        variant="solid"
                        size="md"
                        colorScheme="accent"
                        className="voxel-btn--hero"
                        isLoading={chat.isCompiling}
                        disabled={!chat.draft.trim()}
                    >
                        {isInitialStep ? 'Continue to Alignment →' : 'Send Answer →'}
                    </Button>
                </div>
            </form>
        </>
    );
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
    const { atmosphere, paused, setPaused, cycleAtmosphere, toggleMotion } =
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
                onStartOver={() => chat.reset()}
            />
        );
    }

    const activeAlignment = chat.activeAlignment;
    const isInitialStep = chat.messages.length === 0;
    const pipelinePhase = chat.phase === 'queued' || chat.phase === 'compiling' ? chat.phase : null;
    const activeStep = activeAlignment ? 2 : 1;
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
                <h1 className="sr-only">Build a trading bot from one sentence</h1>

                <div
                    data-testid="builder-stage-card"
                    className="scene-scrim voxel-card flex w-full max-w-3xl flex-col gap-4 rounded-none p-6 min-w-0"
                >
                    <div
                        aria-hidden="true"
                        data-testid="builder-phase-bar"
                        className={`h-1 w-full rounded-none ${phaseBarClass(chat.phase)}`}
                    />

                    <BuilderStepper activeStep={activeStep} />

                    <BuilderStatusStrip
                        phase={chat.phase}
                        elapsedMs={chat.elapsedMs}
                        detail={chat.statusDetail ?? undefined}
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
                </div>
            </div>
        </SceneStage>
    );
}
