import { useQuery } from '@tanstack/react-query';
import { assertServerFnResult } from '~/lib/server-fn';
import { fetchLatestRecipeRunFn } from '../api/recipe-jobs-api';
import type { RecipeJobRecord } from '../types';

const POLL_MS = 5000;

export interface LatestRecipeRun {
    run: RecipeJobRecord | null;
    isRunning: boolean;
}

function isInFlight(run: RecipeJobRecord | null | undefined): boolean {
    return run?.status === 'pending' || run?.status === 'processing';
}

/**
 * The latest backtest run for one recipe, polled only while that run is queued or
 * running. Background work has to stay visible on /build, so a run in flight is
 * re-read every few seconds and a settled (or absent) run is not polled at all.
 *
 * Uses the shared query client rather than a hand-rolled interval, so a hidden tab
 * pauses, an expired session retries with backoff instead of looping silently, and
 * every mount shares one cache entry. The read is per recipe: a global "recent
 * jobs" window would drop an older run that is still pending.
 */
export function useLatestRecipeRun(recipeId: string | undefined): LatestRecipeRun {
    const query = useQuery({
        queryKey: ['recipe-latest-run', recipeId],
        queryFn: async () => {
            const result = await fetchLatestRecipeRunFn({
                data: { recipeId: recipeId as string },
            });
            // An envelope-less reply resolves to `undefined`; throwing here keeps
            // the previous row and lets the query retry instead of blanking the strip.
            return assertServerFnResult(result, 'The latest backtest run');
        },
        enabled: Boolean(recipeId),
        staleTime: POLL_MS,
        refetchInterval: (q) => (isInFlight(q.state.data) ? POLL_MS : false),
    });

    const run = query.data ?? null;
    return { run, isRunning: isInFlight(run) };
}
