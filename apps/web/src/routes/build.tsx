import { PageLayout } from '@llm-market-bench/ui-design-system';
import { createFileRoute } from '@tanstack/react-router';
import { fetchRecipeByIdFn } from '~/features/recipes/api/recipes-api';
import {
    fetchRecipeQuotaStatusFn,
    fetchUserRecipesFn,
} from '~/features/recipes/api/recipes-quota-api';
import { BuilderChatPanel } from '~/features/recipes/builder/BuilderChatPanel';
import { CompiledBotWorkspace } from '~/features/recipes/builder/CompiledBotWorkspace';
import { seo } from '~/lib/seo';

export const Route = createFileRoute('/build')({
    validateSearch: (search: Record<string, unknown>): { idea?: string; recipeId?: string } => ({
        idea:
            typeof search.idea === 'string' && search.idea.trim() ? search.idea.trim() : undefined,
        recipeId:
            typeof search.recipeId === 'string' && search.recipeId.trim()
                ? search.recipeId.trim()
                : undefined,
    }),
    loaderDeps: ({ search }) => ({ recipeId: search.recipeId }),
    loader: async ({ deps, context }) => {
        if (!context?.user?.id) {
            return {
                initialStrategy: null,
                initialQuota: null,
                initialUserRecipes: [],
            };
        }
        const [initialStrategy, initialQuota, initialUserRecipes] = await Promise.all([
            deps.recipeId
                ? fetchRecipeByIdFn({ data: { recipeId: deps.recipeId } }).catch(() => null)
                : Promise.resolve(null),
            fetchRecipeQuotaStatusFn().catch(() => null),
            fetchUserRecipesFn().catch(() => []),
        ]);
        return {
            initialStrategy,
            initialQuota,
            initialUserRecipes,
        };
    },
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
    const { initialStrategy, initialQuota, initialUserRecipes } = Route.useLoaderData();
    const { user } = Route.useRouteContext();
    return (
        <div className="min-h-screen bg-voxel-canvas text-voxel-ink">
            <PageLayout maxWidth="xl" className="flex flex-col gap-6">
                {initialStrategy ? (
                    <CompiledBotWorkspace
                        key={initialStrategy.id ?? initialStrategy.name}
                        initialStrategy={initialStrategy}
                        initialQuota={initialQuota}
                        initialUserRecipes={initialUserRecipes}
                    />
                ) : (
                    <BuilderChatPanel
                        idea={idea}
                        redirectTo="/build"
                        userId={user?.id ?? null}
                        initialQuota={initialQuota}
                        initialUserRecipes={initialUserRecipes}
                    />
                )}
            </PageLayout>
        </div>
    );
}
