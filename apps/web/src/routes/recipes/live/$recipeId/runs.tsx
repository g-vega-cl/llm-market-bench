import {
    Card,
    ErrorCard,
    PageLayout,
    resolveAtmospherePhase,
} from '@llm-market-bench/ui-design-system';
import { createFileRoute, Link } from '@tanstack/react-router';
import { fetchLivePortfolioAndRunsFn } from '~/features/recipes/api/recipes-studio-api';
import { RecipeLiveRunsPage } from '~/features/recipes/pages/RecipeLiveRunsPage';
import { seo } from '~/lib/seo';

export const Route = createFileRoute('/recipes/live/$recipeId/runs')({
    loader: async ({ params }) => {
        const initialAtmosphere = resolveAtmospherePhase(new Date(), 'market-et');
        const initialData = await fetchLivePortfolioAndRunsFn({
            data: { recipeId: params.recipeId },
        }).catch(() => null);
        return { initialAtmosphere, initialData };
    },
    head: ({ loaderData }) => ({
        meta: [
            ...seo({
                title: loaderData?.initialData?.liveMeta?.recipeName
                    ? `${loaderData.initialData.liveMeta.recipeName} | Run Traces | Benchify`
                    : 'Live Run Traces | Benchify',
                description:
                    'Scheduled live run traces, the paper portfolio and every closed trade for a Strategy Recipe bot.',
            }),
        ],
    }),
    component: RouteComponent,
});

function RouteComponent() {
    const { recipeId } = Route.useParams();
    const { initialAtmosphere, initialData } = Route.useLoaderData();

    if (!initialData) {
        return (
            <div className="min-h-screen bg-voxel-canvas text-voxel-ink">
                <PageLayout maxWidth="xl" className="flex flex-col gap-6">
                    <ErrorCard
                        title="Run Traces Not Available"
                        message="This live bot could not be found or is private. Sign in if you own it, or browse public bots in My Bots."
                    />
                    <Card padding="md" className="flex flex-wrap items-center gap-4">
                        <Link
                            to="/recipes"
                            className="voxel-btn inline-flex items-center px-4 py-2 text-sm font-bold bg-accent text-voxel-trough"
                        >
                            ← Back to My Bots
                        </Link>
                    </Card>
                </PageLayout>
            </div>
        );
    }

    return (
        <RecipeLiveRunsPage
            key={recipeId}
            recipeId={recipeId}
            initialData={initialData}
            initialAtmosphere={initialAtmosphere}
        />
    );
}
