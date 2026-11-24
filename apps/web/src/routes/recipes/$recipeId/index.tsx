import {
    Card,
    ErrorCard,
    PageLayout,
    resolveAtmospherePhase,
} from '@llm-market-bench/ui-design-system';
import { createFileRoute, Link } from '@tanstack/react-router';
import {
    fetchRecipeQuotaStatusFn,
    fetchUserRecipesFn,
} from '~/features/recipes/api/recipes-quota-api';
import { fetchRecipeOverviewFn } from '~/features/recipes/api/recipes-studio-api';
import { RecipeOverviewPage } from '~/features/recipes/pages/RecipeOverviewPage';
import { seo } from '~/lib/seo';

export const Route = createFileRoute('/recipes/$recipeId/')({
    loader: async ({ params, context }) => {
        const initialAtmosphere = resolveAtmospherePhase(new Date(), 'market-et');
        const overview = await fetchRecipeOverviewFn({ data: { recipeId: params.recipeId } }).catch(
            () => null,
        );
        if (!context?.user?.id || !overview?.isOwner) {
            return {
                initialAtmosphere,
                overview,
                initialQuota: null,
                initialUserRecipes: [],
            };
        }
        const [initialQuota, initialUserRecipes] = await Promise.all([
            fetchRecipeQuotaStatusFn().catch(() => null),
            fetchUserRecipesFn().catch(() => []),
        ]);
        return {
            initialAtmosphere,
            overview,
            initialQuota,
            initialUserRecipes,
        };
    },
    head: ({ loaderData }) => ({
        meta: [
            ...seo({
                title: loaderData?.overview?.strategy?.name
                    ? `${loaderData.overview.strategy.name} | Bot Overview | Benchify`
                    : 'Bot Overview | Benchify',
                description:
                    'Inspect live paper performance, behavioral insights, open positions, and recent runs for a Strategy Recipe bot.',
            }),
        ],
    }),
    component: RouteComponent,
});

export function RouteComponent() {
    const { initialAtmosphere, overview, initialQuota, initialUserRecipes } = Route.useLoaderData();

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
                        <Link
                            to="/build"
                            className="voxel-btn inline-flex items-center px-4 py-2 text-sm font-bold border border-voxel-bevel-hi bg-voxel-surface text-voxel-ink"
                        >
                            + Build New Bot
                        </Link>
                    </Card>
                </PageLayout>
            </div>
        );
    }

    return (
        <RecipeOverviewPage
            key={overview.recipeId}
            data={overview}
            initialAtmosphere={initialAtmosphere}
            initialQuota={initialQuota}
            initialUserRecipes={initialUserRecipes}
        />
    );
}
