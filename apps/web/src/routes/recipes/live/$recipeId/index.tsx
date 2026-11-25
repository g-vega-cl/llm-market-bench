import { createFileRoute, redirect } from '@tanstack/react-router';

/**
 * The Live Runs hub is retired. It carried a copy of the Overview card plus a
 * "→ run traces" link; the tab row now points straight at the traces page, so this
 * URL only exists to keep old links and bookmarks working.
 */
export const Route = createFileRoute('/recipes/live/$recipeId/')({
    beforeLoad: ({ params }) => {
        throw redirect({
            to: '/recipes/live/$recipeId/runs',
            params: { recipeId: params.recipeId },
        });
    },
});
