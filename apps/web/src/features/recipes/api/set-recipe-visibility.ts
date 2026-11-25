import { createServerFn } from '@tanstack/react-start';
import { getAuthServerClient } from '~/lib/auth';
import { getDbAdminClient } from '~/lib/db';
import { invalidatePublicRecipeCache } from './recipes-studio-api';

/**
 * Owner-controlled publication of a bot.
 *
 * `is_public` decides whether a stranger can read the bot's overview,
 * performance, behaviour and run-trace pages, and whether the bot is eligible
 * for the leaderboard (`get_llm_leaderboard_metrics` filters user bots to
 * `is_public = TRUE`). The column defaults to TRUE, so this call is the opt-out.
 *
 * Ownership is checked against the stored row rather than trusted from the
 * caller, and neither starter templates (public by definition) nor removed bots
 * can be republished through this path — removal has its own `restore` flow.
 * `updated_at` is deliberately untouched: visibility is not a content edit, and
 * bumping it would trip the showcase publisher's graph-drift guard.
 */
export async function setRecipeVisibility(
    recipeId: string,
    userId: string,
    isPublic: boolean,
): Promise<{ id: string; isPublic: boolean }> {
    const db = getDbAdminClient();

    const existing = await db
        .from('strategy_recipes')
        .select('user_id, is_template, archived_at, is_public')
        .eq('id', recipeId)
        .single();

    if (existing.error || !existing.data) {
        throw new Error(`Recipe not found: ${recipeId}`);
    }

    const row = existing.data as {
        user_id?: string;
        is_template?: boolean;
        archived_at?: string | null;
        is_public?: boolean | null;
    };
    if (row.user_id !== userId) {
        throw new Error('Unauthorized: cannot change visibility of a recipe owned by another user');
    }
    if (row.is_template) {
        throw new Error('Cannot change the visibility of a starter template');
    }
    if (row.archived_at) {
        throw new Error('A removed bot cannot change visibility; restore it first');
    }

    const { data, error } = await db
        .from('strategy_recipes')
        .update({ is_public: isPublic })
        .eq('id', recipeId)
        .eq('user_id', userId)
        .select('id, is_public')
        .single();

    if (error || !data) {
        // The PostgREST message is not user-facing copy: log it, return none.
        console.error('[recipes] visibility change failed', error);
        throw new Error('Failed to change bot visibility');
    }

    const nextPublic = Boolean((data as { is_public: boolean }).is_public);
    // An opt-out is a security-relevant transition, so leave a trace even
    // though there is no audit table for it yet.
    console.info(
        `[recipes] visibility ${row.is_public ? 'public' : 'private'} -> ${
            nextPublic ? 'public' : 'private'
        } recipe=${recipeId} user=${userId}`,
    );
    invalidatePublicRecipeCache(recipeId);
    return { id: String((data as { id: string }).id), isPublic: nextPublic };
}

/** A strict boolean or the request is rejected: a coerced `'false'` publishes. */
export function readVisibilityPayload(input: unknown): { recipeId: string; isPublic: boolean } {
    const payload = input as { recipeId?: unknown; isPublic?: unknown } | null;
    if (!payload || typeof payload.recipeId !== 'string' || payload.recipeId.length === 0) {
        throw new Error('Invalid request: recipeId must be a non-empty string');
    }
    if (typeof payload.isPublic !== 'boolean') {
        throw new Error('Invalid request: isPublic must be a boolean');
    }
    return { recipeId: payload.recipeId, isPublic: payload.isPublic };
}

export const setRecipeVisibilityFn = createServerFn({ method: 'POST' })
    .validator(readVisibilityPayload)
    .handler(async ({ data: { recipeId, isPublic } }) => {
        const auth = getAuthServerClient();
        const {
            data: { user },
        } = await auth.auth.getUser();
        if (!user?.id) {
            throw new Error('Unauthorized: please sign in to manage recipes');
        }
        return setRecipeVisibility(recipeId, user.id, isPublic);
    });
