import { createFileRoute } from '@tanstack/react-router';
import { fetchRecentBacktestJobsFn } from '~/features/recipes/api/recipes-api';
import {
    fetchRecipeQuotaStatusFn,
    fetchUserRecipesFn,
} from '~/features/recipes/api/recipes-quota-api';
import { RecipeDashboardPage } from '~/features/recipes/pages/RecipeDashboardPage';
import { RecipeGalleryPage } from '~/features/recipes/pages/RecipeGalleryPage';
import { seo } from '~/lib/seo';

/**
 * /recipes is public on purpose: a logged-out visitor sees example recipes and
 * one primary CTA to start building, while a signed-in user sees their My Bots
 * dashboard.
 */
export const Route = createFileRoute('/recipes/')({
    loader: async ({ context }) => {
        if (!context?.user?.id) {
            return {
                recentBacktests: [],
                initialQuota: null,
                initialUserRecipes: [],
            };
        }
        const [recentBacktests, initialQuota, initialUserRecipes] = await Promise.all([
            fetchRecentBacktestJobsFn().catch(() => []),
            fetchRecipeQuotaStatusFn().catch(() => null),
            fetchUserRecipesFn().catch(() => []),
        ]);
        return {
            recentBacktests,
            initialQuota,
            initialUserRecipes,
        };
    },
    head: () => ({
        meta: [
            ...seo({
                title: 'My Bots & Strategy Recipes | Benchify',
                description:
                    'One LLM call per trading bot: strategies built from news filters, memories and technical criteria, run point-in-time on paper cash. Build your own or manage your live bots.',
            }),
        ],
    }),
    component: RouteComponent,
});

export function RouteComponent() {
    const { recentBacktests, initialQuota, initialUserRecipes } = Route.useLoaderData();
    const context = Route.useRouteContext() as { user?: { id: string } | null };

    if (!context?.user?.id) {
        return <RecipeGalleryPage />;
    }

    return (
        <RecipeDashboardPage
            recentBacktests={recentBacktests}
            initialQuota={initialQuota}
            initialUserRecipes={initialUserRecipes}
        />
    );
}
