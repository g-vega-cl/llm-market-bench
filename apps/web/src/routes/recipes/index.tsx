import { createFileRoute } from '@tanstack/react-router';
import { RecipeStudioPage } from '~/features/recipes/pages/RecipeStudioPage';
import { seo } from '~/lib/seo';

export const Route = createFileRoute('/recipes/')({
    head: () => ({
        meta: [
            ...seo({
                title: 'Strategy Recipe Studio | Benchify',
                description:
                    'Visual Voxel DAG builder for news catalyst streams, technical indicator gates, and LLM trading recipes.',
            }),
        ],
    }),
    component: RouteComponent,
});

function RouteComponent() {
    return <RecipeStudioPage />;
}
