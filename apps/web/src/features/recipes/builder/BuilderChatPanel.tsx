import { Button } from '@llm-market-bench/ui-design-system';
import { usePostHog } from '@posthog/react';
import { Link, useRouter } from '@tanstack/react-router';
import { type KeyboardEvent, useEffect, useId, useRef } from 'react';
import { PERSONALITY_QUESTION_COUNT } from '~/features/personality/personality-type-grid';
import { track } from '~/lib/analytics';
import type { RecipeSummaryItem, RecipeUserQuotaStatus } from '../types';
import { BuilderCompilePipeline } from './BuilderCompilePipeline';
import { BuilderConversation } from './BuilderConversation';
import { BuilderStatusStrip } from './BuilderStatusStrip';
import type { BuilderPhase } from './builder-phases';
import { CompiledBotWorkspace } from './CompiledBotWorkspace';
import { MAX_TURN_CHARS } from './compiler';
import { useBuilderChat } from './use-builder-chat';

const MAX_TEXTAREA_HEIGHT_PX = 240;

/**
 * The chat builder, extracted so it can be embedded or routed at /build.
 * Sits transparently over the global fixed dot-matrix background.
 */
export interface BuilderChatPanelProps {
    idea?: string;
    redirectTo?: '/build';
    /** Supplied by the route: getRouter() is created without a context object. */
    userId?: string | null;
    initialQuota?: RecipeUserQuotaStatus | null;
    initialUserRecipes?: RecipeSummaryItem[];
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
}: BuilderChatPanelProps) {
    const router = useRouter();
    const posthog = usePostHog();
    const textareaRef = useRef<HTMLTextAreaElement>(null);
    const hintId = useId();

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
    const isInitialStep = chat.messages.length === 0;
    const pipelinePhase = chat.phase === 'queued' || chat.phase === 'compiling' ? chat.phase : null;

    const handleTextareaKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
        if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') {
            event.preventDefault();
            if (chat.draft.trim() && !chat.isCompiling) {
                void chat.send(chat.draft);
            }
        }
    };

    if (compiledReply) {
        return (
            <CompiledBotWorkspace
                key={compiledReply.strategy.name}
                initialStrategy={compiledReply.strategy}
                initialQuota={initialQuota}
                initialUserRecipes={initialUserRecipes}
                summary={compiledReply.summary}
                fallback={compiledReply.fallback}
                onStartOver={() => chat.reset()}
            />
        );
    }

    return (
        <div className="flex flex-1 flex-col items-center justify-start gap-6 pb-8">
            <h1 className="sr-only">Build a trading bot from one sentence</h1>

            <div
                data-testid="builder-stage-card"
                className="voxel-card flex w-full max-w-2xl flex-col gap-4 rounded-none p-6 min-w-0"
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
                    className="flex flex-col gap-3"
                    onSubmit={(event) => {
                        event.preventDefault();
                        void chat.send(chat.draft);
                    }}
                >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                        <span id={hintId} className="text-xs font-normal text-voxel-muted">
                            {`${String(chat.draft.length)} / ${String(MAX_TURN_CHARS)} · Ctrl/⌘+Enter to submit`}
                        </span>
                        <Button
                            type="submit"
                            variant="solid"
                            size="md"
                            isLoading={chat.isCompiling}
                            disabled={!chat.draft.trim()}
                        >
                            {isInitialStep ? 'Build My Bot →' : 'Send'}
                        </Button>
                    </div>
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
                            onFocus={onOpen}
                            maxLength={MAX_TURN_CHARS}
                            className="w-full min-h-[4.5rem] max-h-60 resize-none overflow-y-auto bg-transparent text-xs font-normal leading-relaxed text-voxel-ink placeholder:text-voxel-muted focus:outline-none"
                        />
                    </div>
                </form>

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
    );
}
