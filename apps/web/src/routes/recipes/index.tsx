import { createFileRoute } from '@tanstack/react-router';
import { RecipeStudioPage } from '~/features/recipes/pages/RecipeStudioPage';
import { seo } from '~/lib/seo';

export const Route = createFileRoute('/recipes/')({
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
    return <RecipeStudioPage />;
}
