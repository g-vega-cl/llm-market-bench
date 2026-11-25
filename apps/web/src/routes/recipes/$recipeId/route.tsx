import { createFileRoute, Outlet } from '@tanstack/react-router';

/**
 * Layout for a bot's overview surfaces. The hub (`/recipes/$recipeId`) and the
 * detail page (`/recipes/$recipeId/performance`) own their own loaders and render
 * their own chrome, so this route only hosts the outlet.
 */
export const Route = createFileRoute('/recipes/$recipeId')({
    component: () => <Outlet />,
});
