import { useQuery } from '@tanstack/react-query';
import { fetchLivePortfolioAndRunsFn } from '../api/recipes-studio-api';
import { type RecipeLiveSummary, toLiveSummary } from '../builder/live-summary';

/**
 * The workspace's live facts, seeded by the loader and re-read on window focus
 * once the copy is older than a minute. Deliberately no interval: the money line
 * carries an "as of" stamp, and a slot timer would make every idle tab pay the
 * live read every 30 minutes.
 */
export function useRecipeLiveSummary(
    recipeId: string | undefined,
    initial: RecipeLiveSummary | null,
): RecipeLiveSummary | null {
    const query = useQuery({
        queryKey: ['recipe-live-summary', recipeId],
        queryFn: async () =>
            toLiveSummary(
                await fetchLivePortfolioAndRunsFn({ data: { recipeId: recipeId as string } }),
            ),
        enabled: Boolean(recipeId),
        initialData: initial ?? undefined,
        staleTime: 60_000,
    });

    return query.data ?? initial ?? null;
}
