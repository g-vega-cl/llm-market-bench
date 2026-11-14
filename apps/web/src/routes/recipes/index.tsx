import { createFileRoute } from '@tanstack/react-router';
import { fetchRecentBacktestJobsFn, fetchRecipeByIdFn } from '~/features/recipes/api/recipes-api';
import { RecipeStudioPage } from '~/features/recipes/pages/RecipeStudioPage';
import { seo } from '~/lib/seo';

export const Route = createFileRoute('/recipes/')({
    validateSearch: (search: Record<string, unknown>): { recipeId?: string } => ({
        recipeId:
            typeof search.recipeId === 'string' && search.recipeId ? search.recipeId : undefined,
    }),
    loaderDeps: ({ search }) => ({ recipeId: search.recipeId }),
    loader: async ({ deps }) => {
        const [initialStrategy, recentBacktests] = await Promise.all([
            deps.recipeId
                ? fetchRecipeByIdFn({ data: { recipeId: deps.recipeId } }).catch(() => null)
                : Promise.resolve(null),
            fetchRecentBacktestJobsFn().catch(() => []),
        ]);
        return { initialStrategy, recentBacktests };
    },
    head: () => ({
        meta: [
            ...seo({
                title: 'Strategy Recipe Studio | Benchify',
                description:
                    'Single-call 5-block push strategy builder for news catalyst streams, historical memories, technical criteria, and LLM trading recipes.',
            }),
        ],
    }),
    component: RouteComponent,
});

function RouteComponent() {
    const { initialStrategy, recentBacktests } = Route.useLoaderData();
    return <RecipeStudioPage initialStrategy={initialStrategy} recentBacktests={recentBacktests} />;
}
