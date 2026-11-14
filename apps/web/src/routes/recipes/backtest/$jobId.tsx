import { createFileRoute } from '@tanstack/react-router';
import { fetchRecipeRunDetailFn } from '~/features/recipes/api/recipes-api';
import { RecipeBacktestPage } from '~/features/recipes/pages/RecipeBacktestPage';
import { seo } from '~/lib/seo';

export const Route = createFileRoute('/recipes/backtest/$jobId')({
    loader: async ({ params }) => {
        try {
            return await fetchRecipeRunDetailFn({ data: { jobId: params.jobId } });
        } catch {
            return null;
        }
    },
    head: () => ({
        meta: [
            ...seo({
                title: 'Live Recipe Backtest | Benchify',
                description:
                    'Live day-by-day point-in-time backtest telemetry, tool execution traces, and equity progression for Strategy Recipes.',
            }),
        ],
    }),
    component: RouteComponent,
});

function RouteComponent() {
    const { jobId } = Route.useParams();
    const initialData = Route.useLoaderData();
    return <RecipeBacktestPage key={jobId} jobId={jobId} initialData={initialData} />;
}
