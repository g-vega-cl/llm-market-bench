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
import { RecipeEditPage } from '~/features/recipes/pages/RecipeEditPage';
import { seo } from '~/lib/seo';

export const Route = createFileRoute('/_authed/recipes/$recipeId/edit')({
    loader: async ({ params }) => {
        const initialAtmosphere = resolveAtmospherePhase(new Date(), 'market-et');
        const [overview, initialQuota, initialUserRecipes] = await Promise.all([
            fetchRecipeOverviewFn({ data: { recipeId: params.recipeId } }).catch(() => null),
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
                    ? `Edit ${loaderData.overview.strategy.name} | Blueprint | Benchify`
                    : 'Edit Bot Blueprint | Benchify',
                description:
                    'Edit strategy blocks, data tools, and prompt instructions for your Strategy Recipe trading bot.',
            }),
        ],
    }),
    component: RouteComponent,
});

export function RouteComponent() {
    const { recipeId } = Route.useParams();
    const { initialAtmosphere, overview, initialQuota, initialUserRecipes } = Route.useLoaderData();

    if (!overview?.isOwner) {
        return (
            <div className="min-h-screen bg-voxel-canvas text-voxel-ink">
                <PageLayout maxWidth="xl" className="flex flex-col gap-6">
                    <ErrorCard
                        title="Cannot Edit Blueprint"
                        message="Only the owner of this bot can edit its blocks and prompt."
                    />
                    <Card padding="md" className="flex flex-wrap items-center gap-4">
                        <Link
                            to="/recipes/$recipeId"
                            params={{ recipeId }}
                            className="voxel-btn inline-flex items-center px-4 py-2 text-sm font-bold bg-accent text-voxel-trough"
                        >
                            ← Back to Bot Overview
                        </Link>
                    </Card>
                </PageLayout>
            </div>
        );
    }

    return (
        <RecipeEditPage
            key={overview.recipeId}
            recipeId={overview.recipeId}
            initialStrategy={overview.strategy}
            initialIsLive={overview.isLive}
            initialAtmosphere={initialAtmosphere}
            initialQuota={initialQuota}
            initialUserRecipes={initialUserRecipes}
        />
    );
}
