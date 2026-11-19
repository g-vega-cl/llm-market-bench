import { createServerFn } from '@tanstack/react-start';
import { getAuthServerClient } from '~/lib/auth';
import { getDbAdminClient } from '~/lib/db';
import {
    assertNoPrevOutputPlaceholder,
    assertSingleLlmStage,
    normalizeRecipeName,
} from './recipes-validators';

const FORK_PREFIX = 'Copy of ';

/**
 * Copy a public/template/own recipe into a new row owned by the caller.
 *
 * Forking is the cheapest path from "that looks interesting" to "this is mine":
 * the visitor lands in the studio with a working five-block graph and changes
 * one thing. The copy never inherits live scheduling or publication state.
 */
export async function forkRecipe(recipeId: string, userId: string) {
    const db = getDbAdminClient();

    const { data: source, error } = await db
        .from('strategy_recipes')
        .select(
            'id, user_id, name, description, cadence, graph_json, is_public, is_template, archived_at',
        )
        .eq('id', recipeId)
        .single();

    if (error || !source) throw new Error(`Recipe not found: ${recipeId}`);

    const row = source as {
        user_id: string | null;
        name: string;
        description: string | null;
        cadence: string;
        graph_json: Record<string, unknown> | null;
        is_public: boolean;
        is_template: boolean;
        archived_at: string | null;
    };

    const isOwner = row.user_id === userId;
    if (!isOwner && !row.is_public && !row.is_template) {
        throw new Error('Unauthorized: cannot fork a private recipe');
    }
    if (isOwner && row.archived_at) {
        throw new Error('This strategy was removed from My Strategies. Restore it instead.');
    }
    if (!row.graph_json) throw new Error('Recipe has no strategy graph');
    // Fail closed on a legacy/malformed public graph: forking it would only burn
    // a queue row on every run attempt.
    const graph = row.graph_json as { stages: readonly unknown[] };
    assertSingleLlmStage(graph as never);
    assertNoPrevOutputPlaceholder(graph as never);

    const name = normalizeRecipeName(`${FORK_PREFIX}${row.name}`);

    const { data: created, error: insertError } = await db
        .from('strategy_recipes')
        .insert({
            user_id: userId,
            name,
            description: row.description || '',
            cadence: row.cadence || '3h',
            graph_json: row.graph_json,
            is_public: false,
            is_template: false,
            is_live: false,
            concurrency_config: {
                max_open_trades: 4,
                max_equity_pct_per_trade: 25.0,
            },
            paper_cash: 10000,
            paper_positions: [],
            paper_trades: [],
            paper_equity_curve: [],
        })
        .select('id, name')
        .single();

    if (insertError || !created) {
        throw new Error(insertError?.message || 'Failed to fork recipe');
    }
    return created as { id: string; name: string };
}

export const forkRecipeFn = createServerFn({ method: 'POST' })
    .validator((d: { recipeId: string }) => d)
    .handler(async ({ data: { recipeId } }) => {
        const auth = getAuthServerClient();
        const {
            data: { user },
        } = await auth.auth.getUser();
        if (!user?.id) {
            throw new Error('Unauthorized: sign in to fork a recipe');
        }
        return forkRecipe(recipeId, user.id);
    });
