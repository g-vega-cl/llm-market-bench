import { Card, PageLayout } from '@llm-market-bench/ui-design-system';
import { createFileRoute, Link } from '@tanstack/react-router';
import { fetchPublicShowcaseBacktestFn } from '~/features/recipes/api/recipes-quota-api';
import { RecipeBacktestPage } from '~/features/recipes/pages/RecipeBacktestPage';
import { seo } from '~/lib/seo';

export const Route = createFileRoute('/recipes-demo')({
    loader: async () => {
        try {
            return await fetchPublicShowcaseBacktestFn();
        } catch {
            return null;
        }
    },
    head: () => ({
        meta: [
            ...seo({
                title: 'Sample Recipe Backtest (Preview) | Benchify',
                description:
                    'Read-only walkthrough of a 30-slot point-in-time trading recipe backtest with full reasoning traces.',
            }),
        ],
    }),
    component: RouteComponent,
});

function RouteComponent() {
    const showcase = Route.useLoaderData();
    if (!showcase) {
        return (
            <div className="min-h-screen bg-voxel-canvas text-voxel-ink">
                <PageLayout maxWidth="xl" className="flex flex-col gap-6">
                    <Card padding="md" className="flex flex-col gap-3">
                        <h1 className="text-sm font-bold text-voxel-ink">
                            Strategy Recipe Studio — Sample Backtest Preview
                        </h1>
                        <p className="text-xs font-normal text-voxel-muted">
                            No public showcase backtest has been published yet. Sign in free with
                            Google or Email to compose strategies, inspect tool traces, and run
                            2-week point-in-time simulations.
                        </p>
                        <div>
                            <Link
                                to="/recipes"
                                className="voxel-btn inline-flex items-center px-3 py-1.5 text-sm font-bold border-2 border-accent text-accent"
                            >
                                Sign In Free to Open Studio →
                            </Link>
                        </div>
                    </Card>
                </PageLayout>
            </div>
        );
    }

    return (
        <RecipeBacktestPage
            key={showcase.job.id}
            jobId={showcase.job.id}
            initialData={showcase}
            readOnlyShowcase
        />
    );
}
