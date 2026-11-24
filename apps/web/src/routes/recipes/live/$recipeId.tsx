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
import { fetchLivePortfolioAndRunsFn } from '~/features/recipes/api/recipes-studio-api';
import { RecipeLivePage } from '~/features/recipes/pages/RecipeLivePage';
import { seo } from '~/lib/seo';

export const Route = createFileRoute('/recipes/live/$recipeId')({
    loader: async ({ params, context }) => {
        const initialAtmosphere = resolveAtmospherePhase(new Date(), 'market-et');
        const initialData = await fetchLivePortfolioAndRunsFn({
            data: { recipeId: params.recipeId },
        }).catch(() => null);

        if (!context?.user?.id || !initialData?.liveMeta?.isOwner) {
            return {
                initialAtmosphere,
                initialData,
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
            initialData,
            initialQuota,
            initialUserRecipes,
        };
    },
    head: ({ loaderData }) => ({
        meta: [
            ...seo({
                title: loaderData?.initialData?.liveMeta?.recipeName
                    ? `${loaderData.initialData.liveMeta.recipeName} | Live Runs | Benchify`
                    : 'Live Recipe Status | Benchify',
                description: 'Live paper portfolio and scheduled run history for Strategy Recipes.',
            }),
        ],
    }),
    component: RouteComponent,
});

function RouteComponent() {
    const { recipeId } = Route.useParams();
    const { initialAtmosphere, initialData, initialQuota, initialUserRecipes } =
        Route.useLoaderData();

    if (!initialData) {
        return (
            <div className="min-h-screen bg-voxel-canvas text-voxel-ink">
                <PageLayout maxWidth="xl" className="flex flex-col gap-6">
                    <ErrorCard
                        title="Live Runs Not Available"
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
        <RecipeLivePage
            key={recipeId}
            recipeId={recipeId}
            initialData={initialData}
            initialAtmosphere={initialAtmosphere}
            initialQuota={initialQuota}
            initialUserRecipes={initialUserRecipes}
        />
    );
}
