import { createServerFn } from '@tanstack/react-start';
import { getAuthServerClient } from '~/lib/auth';
import { getDbAdminClient } from '~/lib/db';

/**
 * Soft-hide a strategy: remove it from My Strategies without deleting it.
 *
 * Rows are never deleted — the paper ledger, queue history, and alert inbox all
 * reference the recipe. `archived_at` hides it from the studio listing, open
 * queue jobs for it are cancelled so a queued turn cannot outlive the removal,
 * and `is_live` is cleared so the scheduler stops creating new ones.
 * `updated_at` is deliberately untouched: hiding is not a content edit, and
 * bumping it would trip the showcase publisher's graph-drift guard.
 *
 * Restoring is explicit: only `saveRecipe({ restore: true })` clears
 * `archived_at`, so an automatic persist before Run Live or Backtest can never
 * silently resurrect a removed strategy.
 */
export async function archiveRecipe(
    recipeId: string,
    userId: string,
): Promise<{ id: string; archived_at: string; cancelled_jobs: number }> {
    const db = getDbAdminClient();

    const existing = await db
        .from('strategy_recipes')
        .select('user_id')
        .eq('id', recipeId)
        .single();

    if (existing.error || !existing.data) {
        throw new Error(`Recipe not found: ${recipeId}`);
    }
    if ((existing.data as { user_id?: string }).user_id !== userId) {
        throw new Error('Unauthorized: cannot remove a recipe owned by another user');
    }

    const archivedAt = new Date().toISOString();
    const { data, error } = await db
        .from('strategy_recipes')
        .update({ archived_at: archivedAt, is_live: false })
        .eq('id', recipeId)
        .eq('user_id', userId)
        .select('id, archived_at')
        .single();

    if (error || !data) {
        throw new Error(error?.message || 'Failed to remove strategy');
    }

    // A pending or processing turn would otherwise keep spending quota on a
    // strategy the owner can no longer see; the worker honours `cancelled`
    // between slots. A failure here must not undo the removal, so it is logged
    // rather than thrown.
    let cancelledJobs = 0;
    const { data: cancelled, error: cancelError } = await db
        .from('recipe_execution_queue')
        .update({ status: 'cancelled', cancelled_at: archivedAt })
        .eq('recipe_id', recipeId)
        .eq('user_id', userId)
        .in('status', ['pending', 'processing'])
        .select('id');

    if (cancelError) {
        console.error('[recipes] failed to cancel open jobs for removed strategy', cancelError);
    } else if (Array.isArray(cancelled)) {
        cancelledJobs = cancelled.length;
    }

    return {
        id: String((data as { id: string }).id),
        archived_at: String((data as { archived_at: string }).archived_at),
        cancelled_jobs: cancelledJobs,
    };
}

export const archiveRecipeFn = createServerFn({ method: 'POST' })
    .validator((d: { recipeId: string }) => d)
    .handler(async ({ data: { recipeId } }) => {
        const auth = getAuthServerClient();
        const {
            data: { user },
        } = await auth.auth.getUser();
        if (!user?.id) {
            throw new Error('Unauthorized: please sign in to manage recipes');
        }
        return archiveRecipe(recipeId, user.id);
    });
