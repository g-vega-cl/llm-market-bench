import { PageLayout } from '@llm-market-bench/ui-design-system';
import { createFileRoute } from '@tanstack/react-router';
import { BuilderChatPanel } from '~/features/recipes/builder/BuilderChatPanel';
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
    const { user } = Route.useRouteContext();
    return (
        <div className="min-h-screen bg-voxel-canvas text-voxel-ink">
            <PageLayout maxWidth="xl" className="flex flex-col gap-6">
                <BuilderChatPanel idea={idea} redirectTo="/build" userId={user?.id ?? null} />
            </PageLayout>
        </div>
    );
}
