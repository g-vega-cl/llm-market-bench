import { createFileRoute } from '@tanstack/react-router';
import { fetchLivePortfolioAndRunsFn } from '~/features/recipes/api/recipes-studio-api';
import { RecipeLivePage } from '~/features/recipes/pages/RecipeLivePage';
import { seo } from '~/lib/seo';

export const Route = createFileRoute('/_authed/recipes/live/$recipeId')({
    loader: async ({ params }) => {
        try {
            return await fetchLivePortfolioAndRunsFn({ data: { recipeId: params.recipeId } });
        } catch {
            return null;
        }
    },
    head: () => ({
        meta: [
            ...seo({
                title: 'Live Recipe Status | Benchify',
                description: 'Live paper portfolio and scheduled run history for Strategy Recipes.',
            }),
        ],
    }),
    component: RouteComponent,
});

function RouteComponent() {
    const { recipeId } = Route.useParams();
    const initialData = Route.useLoaderData();
    return <RecipeLivePage key={recipeId} recipeId={recipeId} initialData={initialData} />;
}
