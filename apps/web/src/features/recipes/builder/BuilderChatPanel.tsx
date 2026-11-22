import { type AtmospherePhase, Button, Input } from '@llm-market-bench/ui-design-system';
import { usePostHog } from '@posthog/react';
import { Link, useRouter } from '@tanstack/react-router';
import { useRef } from 'react';
import { track } from '~/lib/analytics';
import { useDioramaStage } from '../../home/backdrop/useDioramaStage';
import type { RecipeSummaryItem, RecipeUserQuotaStatus } from '../types';
import { BuildDioramaStage } from './BuildDioramaStage';
import { BuilderCompilePipeline } from './BuilderCompilePipeline';
import { BuilderConversation } from './BuilderConversation';
import { BuilderStarterChips } from './BuilderStarterChips';
import { BuilderStatusStrip } from './BuilderStatusStrip';
import type { BuilderPhase } from './builder-phases';
import { CompiledBotWorkspace } from './CompiledBotWorkspace';
import { useBuilderChat } from './use-builder-chat';

/**
 * The chat builder, extracted so it can be embedded or routed at /build.
 * Hosts a single persistent BuildDioramaStage across Step 1 (chat) and
 * Step 2 (compiled workspace) so atmosphere, paused motion, and offscreen
 * canvases survive compilation and Start Over transitions cleanly.
 */
export interface BuilderChatPanelProps {
    idea?: string;
    redirectTo?: '/build';
    /** Supplied by the route: getRouter() is created without a context object. */
    userId?: string | null;
    initialQuota?: RecipeUserQuotaStatus | null;
    initialUserRecipes?: RecipeSummaryItem[];
    /** SSR-resolved market-ET atmosphere phase passed from route loader to eliminate initial flash. */
    initialAtmosphere?: AtmospherePhase;
}

function phaseBarClass(phase: BuilderPhase): string {
    if (phase === 'queued' || phase === 'compiling') return 'bg-accent';
    if (phase === 'question' || phase === 'declined') return 'bg-warning';
    if (phase === 'error') return 'bg-danger';
    return 'bg-voxel-bevel-hi';
}

export function BuilderChatPanel({
    idea,
    redirectTo = '/build',
    userId = null,
    initialQuota = null,
    initialUserRecipes = [],
    initialAtmosphere,
}: BuilderChatPanelProps) {
    const router = useRouter();
    const posthog = usePostHog();
    const inputRef = useRef<HTMLInputElement>(null);

    const diorama = useDioramaStage(initialAtmosphere);

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

    const compiledReply = chat.reply?.status === 'ok' ? chat.reply : null;
    const isInitialStep = chat.messages.length === 0;
    const pipelinePhase = chat.phase === 'queued' || chat.phase === 'compiling' ? chat.phase : null;

    if (compiledReply) {
        return (
            <CompiledBotWorkspace
                key={compiledReply.strategy.name}
                initialStrategy={compiledReply.strategy}
                initialQuota={initialQuota}
                initialUserRecipes={initialUserRecipes}
                initialAtmosphere={diorama.atmosphere}
                diorama={diorama}
                summary={compiledReply.summary}
                fallback={compiledReply.fallback}
                onStartOver={() => chat.reset()}
            />
        );
    }

    return (
        <BuildDioramaStage diorama={diorama} heroViewport>
            <div className="flex flex-1 flex-col items-center justify-start gap-6 pb-16">
                <header className="flex flex-col items-center gap-2 text-center">
                    <p className="home-hero-copy text-xs font-normal tracking-wider uppercase text-accent">
                        Benchify Strategy Builder
                    </p>
                    <h1 className="home-hero-heading text-lg font-bold text-voxel-ink">
                        Build your trading bot.
                    </h1>
                    <p className="home-hero-copy max-w-prose text-xs font-normal leading-relaxed text-voxel-ink">
                        Describe what your bot should trade and when to enter or exit. We&apos;ll
                        compile it into a point-in-time strategy you can backtest on paper cash
                        right away.
                    </p>
                </header>

                <div
                    data-testid="builder-stage-card"
                    className="scene-scrim voxel-card flex w-full max-w-2xl flex-col gap-4 rounded-none p-6 min-w-0"
                >
                    <div
                        aria-hidden="true"
                        data-testid="builder-phase-bar"
                        className={`h-1 w-full rounded-none ${phaseBarClass(chat.phase)}`}
                    />

                    <BuilderStatusStrip
                        phase={chat.phase}
                        elapsedMs={chat.elapsedMs}
                        detail={chat.statusDetail ?? undefined}
                    />

                    {pipelinePhase ? <BuilderCompilePipeline phase={pipelinePhase} /> : null}

                    {isInitialStep && !pipelinePhase ? (
                        <BuilderStarterChips
                            disabled={chat.isCompiling}
                            onSelect={(prompt) => {
                                onOpen();
                                chat.setDraft(prompt);
                                inputRef.current?.focus();
                            }}
                        />
                    ) : null}

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
                        <div
                            role="alert"
                            className="voxel-trough bg-voxel-trough flex flex-wrap items-center justify-between gap-2 p-3 min-w-0"
                        >
                            <p className="text-xs font-normal text-danger min-w-0 break-words">
                                {chat.error}
                            </p>
                            <div className="flex flex-wrap items-center gap-2 shrink-0 min-w-0">
                                <Button
                                    size="sm"
                                    variant="outline"
                                    colorScheme="neutral"
                                    onClick={chat.retry}
                                    disabled={chat.isCompiling}
                                >
                                    Try again
                                </Button>
                                <Button
                                    size="sm"
                                    variant="outline"
                                    colorScheme="neutral"
                                    onClick={chat.useTemplate}
                                    disabled={chat.isCompiling}
                                >
                                    Use closest template
                                </Button>
                            </div>
                        </div>
                    ) : null}

                    {userId ? null : (
                        <p className="text-xs font-normal text-voxel-muted">
                            Sign in to build — your idea is saved in this browser.
                        </p>
                    )}

                    <form
                        className="flex flex-wrap items-stretch gap-2"
                        onSubmit={(event) => {
                            event.preventDefault();
                            void chat.send(chat.draft);
                        }}
                    >
                        <div className="min-w-0 flex-1">
                            <Input
                                ref={inputRef}
                                aria-label="Describe your trading bot"
                                placeholder="e.g., Buy chipmakers when AI capex news is positive, exit on guidance cuts..."
                                value={chat.draft}
                                onChange={(event) => chat.setDraft(event.target.value)}
                                onFocus={onOpen}
                                maxLength={400}
                            />
                        </div>
                        <Button
                            type="submit"
                            variant="solid"
                            size="md"
                            isLoading={chat.isCompiling}
                            disabled={!chat.draft.trim()}
                        >
                            {isInitialStep ? 'Build My Bot →' : 'Send'}
                        </Button>
                    </form>

                    <p className="text-xs font-normal text-voxel-muted">
                        Not sure where to start?{' '}
                        <Link
                            to="/personality"
                            className="text-accent underline underline-offset-4 hover:text-accent-hover"
                        >
                            Take our 10-question personality test
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
        </BuildDioramaStage>
    );
}
