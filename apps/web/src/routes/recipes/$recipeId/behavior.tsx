import {
    Card,
    ErrorCard,
    PageLayout,
    resolveAtmospherePhase,
} from '@llm-market-bench/ui-design-system';
import { createFileRoute, Link } from '@tanstack/react-router';
import { fetchRecipeOverviewFn } from '~/features/recipes/api/recipes-studio-api';
import { RecipeBehaviorPage } from '~/features/recipes/pages/RecipeBehaviorPage';
import { seo } from '~/lib/seo';

export const Route = createFileRoute('/recipes/$recipeId/behavior')({
    loader: async ({ params }) => {
        const initialAtmosphere = resolveAtmospherePhase(new Date(), 'market-et');
        const overview = await fetchRecipeOverviewFn({ data: { recipeId: params.recipeId } }).catch(
            () => null,
        );
        return { initialAtmosphere, overview };
    },
    head: ({ loaderData }) => ({
        meta: [
            ...seo({
                title: loaderData?.overview?.strategy?.name
                    ? `${loaderData.overview.strategy.name} | Behaviour | Benchify`
                    : 'Bot Behaviour | Benchify',
                description:
                    'Tool usage, action mix, ticker focus and exit reasons for a Strategy Recipe bot.',
            }),
        ],
    }),
    component: RouteComponent,
});

function RouteComponent() {
    const { initialAtmosphere, overview } = Route.useLoaderData();

    if (!overview) {
        return (
            <div className="min-h-screen bg-voxel-canvas text-voxel-ink">
                <PageLayout maxWidth="xl" className="flex flex-col gap-6">
                    <ErrorCard
                        title="Bot Not Available"
                        message="This recipe could not be found or is private. Sign in if you own it, or explore starter bots in My Bots."
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
        <RecipeBehaviorPage
            key={overview.recipeId}
            data={overview}
            initialAtmosphere={initialAtmosphere}
        />
    );
}
