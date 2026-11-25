import { createFileRoute, Outlet } from '@tanstack/react-router';

/**
 * Layout for a bot's live surfaces. The hub (`/recipes/live/$recipeId`) and the
 * run-trace detail page (`/recipes/live/$recipeId/runs`) own their own loaders and
 * chrome, so this route only hosts the outlet.
 */
export const Route = createFileRoute('/recipes/live/$recipeId')({
    component: () => <Outlet />,
});
