import { createFileRoute } from '@tanstack/react-router';
import { fetchRecentBacktestJobsFn, fetchRecipeByIdFn } from '~/features/recipes/api/recipes-api';
import {
    fetchRecipeQuotaStatusFn,
    fetchUserRecipesFn,
} from '~/features/recipes/api/recipes-quota-api';
import { RecipeGalleryPage } from '~/features/recipes/pages/RecipeGalleryPage';
import { RecipeStudioPage } from '~/features/recipes/pages/RecipeStudioPage';
import { seo } from '~/lib/seo';

/**
 * /recipes is public on purpose: a logged-out visitor can read what a recipe is
 * (prompt, filters, one LLM call) before signing in. The studio's server reads are
 * all `.catch()`-guarded, so an anonymous render degrades to the gallery instead
 * of throwing, and the editors/run buttons remain auth-gated server-side.
 */
export const Route = createFileRoute('/recipes/')({
    validateSearch: (search: Record<string, unknown>): { recipeId?: string } => ({
        recipeId:
            typeof search.recipeId === 'string' && search.recipeId ? search.recipeId : undefined,
    }),
    loaderDeps: ({ search }) => ({ recipeId: search.recipeId }),
    loader: async ({ deps, context }) => {
        // Three server fns would throw Unauthorized for a guest and be discarded;
        // the gallery needs none of them.
        if (!context?.user?.id) {
            return {
                initialStrategy: null,
                recentBacktests: [],
                initialQuota: null,
                initialUserRecipes: [],
            };
        }
        const [initialStrategy, recentBacktests, initialQuota, initialUserRecipes] =
            await Promise.all([
                deps.recipeId
                    ? fetchRecipeByIdFn({ data: { recipeId: deps.recipeId } }).catch(() => null)
                    : Promise.resolve(null),
                fetchRecentBacktestJobsFn().catch(() => []),
                fetchRecipeQuotaStatusFn().catch(() => null),
                fetchUserRecipesFn().catch(() => []),
            ]);
        return {
            initialStrategy,
            recentBacktests,
            initialQuota,
            initialUserRecipes,
        };
    },
    head: () => ({
        meta: [
            ...seo({
                title: 'Strategy Recipes — one LLM call per trading bot | Benchify',
                description:
                    'One LLM call per trading bot: strategies built from news filters, memories and technical criteria, run point-in-time on paper cash. Fork a recipe or describe your own.',
            }),
        ],
    }),
    component: RouteComponent,
});

export function RouteComponent() {
    const { initialStrategy, recentBacktests, initialQuota, initialUserRecipes } =
        Route.useLoaderData();
    const context = Route.useRouteContext() as { user?: { id: string } | null };

    if (!context?.user?.id) {
        return <RecipeGalleryPage />;
    }

    return (
        <RecipeStudioPage
            key={initialStrategy?.id ?? 'starter'}
            initialStrategy={initialStrategy}
            recentBacktests={recentBacktests}
            initialQuota={initialQuota}
            initialUserRecipes={initialUserRecipes}
        />
    );
}
