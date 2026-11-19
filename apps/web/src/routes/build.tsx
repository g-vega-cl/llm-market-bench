import { Button, Input, PageLayout, SectionHeading } from '@llm-market-bench/ui-design-system';
import { usePostHog } from '@posthog/react';
import { createFileRoute, useRouter } from '@tanstack/react-router';
import { useEffect } from 'react';
import { BuilderConversation } from '~/features/recipes/builder/BuilderConversation';
import { useBuilderChat } from '~/features/recipes/builder/use-builder-chat';
import { track } from '~/lib/analytics';
import { seo } from '~/lib/seo';

export const Route = createFileRoute('/build')({
    validateSearch: (search: Record<string, unknown>): { idea?: string } => ({
        idea:
            typeof search.idea === 'string' && search.idea.trim() ? search.idea.trim() : undefined,
    }),
    head: () => ({
        meta: [
            ...seo({
                title: 'Build a trading bot from one sentence | Benchify',
                description:
                    'Describe the bot you want. The builder asks one or two questions, then compiles a runnable point-in-time recipe you can edit and backtest.',
            }),
        ],
    }),
    component: RouteComponent,
});

export function RouteComponent() {
    const { idea } = Route.useSearch();
    const context = Route.useRouteContext() as { user?: { id: string } | null };
    const router = useRouter();
    const posthog = usePostHog();
    const userId = context?.user?.id ?? null;

    const chat = useBuilderChat({
        idea,
        userId,
        onNeedSignIn: async () => {
            await router.navigate({ to: '/login', search: { redirect: '/build' } });
        },
    });

    useEffect(() => {
        track(posthog, 'builder_opened', { seeded: Boolean(idea) });
    }, [posthog, idea]);

    return (
        <div className="min-h-screen bg-voxel-canvas text-voxel-ink">
            <PageLayout maxWidth="xl" className="flex flex-col gap-6">
                <header className="flex flex-col gap-2 pb-4 border-b-2 border-voxel-bevel-hi">
                    <SectionHeading className="text-sm">Strategy builder</SectionHeading>
                    <p className="text-xs font-normal text-voxel-muted max-w-prose">
                        Describe the bot in plain English. It gets compiled into a real recipe — one
                        LLM call, point-in-time news, paper cash — which you can edit and run.
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
                    <div className="flex-1 min-w-0">
                        <Input
                            aria-label="Message the strategy builder"
                            placeholder="Describe or refine the bot…"
                            value={chat.draft}
                            onChange={(event) => chat.setDraft(event.target.value)}
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
            </PageLayout>
        </div>
    );
}
