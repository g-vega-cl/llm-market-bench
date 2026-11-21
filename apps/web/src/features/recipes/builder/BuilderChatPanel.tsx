import { Button, Input, SectionHeading } from '@llm-market-bench/ui-design-system';
import { usePostHog } from '@posthog/react';
import { useRouter } from '@tanstack/react-router';
import { useRef } from 'react';
import { track } from '~/lib/analytics';
import { BuilderConversation } from './BuilderConversation';
import { useBuilderChat } from './use-builder-chat';

/**
 * The chat builder, extracted so it can live on /lab and still be reachable at
 * /build. One implementation, two entry points.
 */
export interface BuilderChatPanelProps {
    idea?: string;
    redirectTo: '/build' | '/lab';
    /** Supplied by the route: getRouter() is created without a context object. */
    userId?: string | null;
}

export function BuilderChatPanel({ idea, redirectTo, userId = null }: BuilderChatPanelProps) {
    const router = useRouter();
    const posthog = usePostHog();

    const chat = useBuilderChat({
        idea,
        userId,
        onNeedSignIn: async () => {
            await router.navigate({ to: '/login', search: { redirect: redirectTo } });
        },
    });

    // Fire on first interaction, not on mount: the panel also sits on /lab, and a
    // directory pageview is not a builder opening.
    const opened = useRef(false);
    const onOpen = () => {
        if (opened.current) return;
        opened.current = true;
        track(posthog, 'builder_opened', { seeded: Boolean(idea) });
    };

    return (
        <div className="flex flex-col gap-4">
            <header className="flex flex-col gap-2 border-b-2 border-voxel-bevel-hi pb-4">
                <SectionHeading className="text-sm">Build with chat</SectionHeading>
                <p className="max-w-prose text-xs font-normal text-voxel-muted">
                    Describe the bot in plain English. It gets compiled into a real recipe — one LLM
                    call, point-in-time news, paper cash — which you can edit and run.
                </p>
            </header>

            <BuilderConversation
                messages={chat.messages}
                messageIds={chat.messageIds}
                reply={chat.reply}
                pendingIdea={chat.pendingIdea}
                isSignedIn={Boolean(userId)}
                onSend={(text) => void chat.send(text)}
                onOpenStudio={() => void router.navigate({ to: '/recipes' })}
            />

            {chat.error ? (
                <p role="alert" className="voxel-trough p-3 text-xs font-normal text-danger">
                    {chat.error}
                </p>
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
                        aria-label="Message the strategy builder"
                        placeholder="Describe or refine the bot…"
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
                    Send
                </Button>
            </form>
        </div>
    );
}
