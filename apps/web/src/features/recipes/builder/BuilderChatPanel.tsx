import { Button, Input, SectionHeading } from '@llm-market-bench/ui-design-system';
import { usePostHog } from '@posthog/react';
import { Link, useRouter } from '@tanstack/react-router';
import { useRef } from 'react';
import { track } from '~/lib/analytics';
import type { RecipeSummaryItem, RecipeUserQuotaStatus } from '../types';
import { BuilderConversation } from './BuilderConversation';
import { BuilderStatusStrip } from './BuilderStatusStrip';
import { CompiledBotWorkspace } from './CompiledBotWorkspace';
import { useBuilderChat } from './use-builder-chat';

/**
 * The chat builder, extracted so it can be embedded or routed at /build.
 */
export interface BuilderChatPanelProps {
    idea?: string;
    redirectTo?: '/build';
    /** Supplied by the route: getRouter() is created without a context object. */
    userId?: string | null;
    initialQuota?: RecipeUserQuotaStatus | null;
    initialUserRecipes?: RecipeSummaryItem[];
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

    if (chat.reply?.status === 'ok') {
        return (
            <CompiledBotWorkspace
                key={chat.reply.strategy.name}
                initialStrategy={chat.reply.strategy}
                initialQuota={initialQuota}
                initialUserRecipes={initialUserRecipes}
                summary={chat.reply.summary}
                fallback={chat.reply.fallback}
                onStartOver={() => chat.reset()}
            />
        );
    }

    const isInitialStep = chat.messages.length === 0;

    return (
        <div className="flex flex-col gap-5">
            <BuilderStatusStrip phase={chat.phase} elapsedMs={chat.elapsedMs} />
            <header className="flex flex-col gap-2 border-b-2 border-voxel-bevel-hi pb-4">
                <SectionHeading className="text-sm">Build your trading bot</SectionHeading>
                <p className="max-w-prose text-xs font-normal text-voxel-muted">
                    Describe what your bot should trade and when to enter or exit. We&apos;ll
                    compile it into a point-in-time strategy you can backtest on paper cash right
                    away.
                </p>
            </header>

            <BuilderConversation
                messages={chat.messages}
                messageIds={chat.messageIds}
                reply={chat.reply}
                pendingIdea={chat.pendingIdea}
                isSignedIn={Boolean(userId)}
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
                    <Button
                        size="sm"
                        variant="outline"
                        colorScheme="neutral"
                        onClick={chat.retry}
                        disabled={chat.isCompiling}
                    >
                        Try again
                    </Button>
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
    );
}
