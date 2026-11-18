import { createServerFn } from '@tanstack/react-start';
import { getAuthServerClient } from '~/lib/auth';
import { getDbAdminClient, getDbServerClient } from '~/lib/db';
import type { PushStrategy, StrategyRecipeRecord, StrategyStage } from '../types';
import { assertQuotaAllowsJob } from './recipes-quota-api';
import {
    assertNoPrevOutputPlaceholder,
    assertSingleLlmStage,
    normalizeRecipeName,
} from './recipes-validators';

/**
 * Job and run reads live in their own slice; re-exported here because every
 * caller already imports this module for the recipe lifecycle.
 */
export {
    fetchRecentBacktestJobs,
    fetchRecentBacktestJobsFn,
    fetchRecipeRunDetail,
    fetchRecipeRunDetailFn,
    getRecipeJobStatus,
    getRecipeJobStatusFn,
} from './recipe-jobs-api';
export { assertNoPrevOutputPlaceholder, assertSingleLlmStage, normalizeRecipeName };

export async function fetchPublicRecipes(): Promise<StrategyRecipeRecord[]> {
    const db = getDbServerClient();
    const { data, error } = await db
        .from('strategy_recipes')
        .select('*')
        .or('is_public.eq.true,is_template.eq.true')
        // A strategy the owner removed must not resurface on any public surface.
        .is('archived_at', null)
        .order('updated_at', { ascending: false })
        .limit(20);

    if (error) {
        throw new Error(error.message);
    }
    return (data || []) as StrategyRecipeRecord[];
}

/**
 * Publication intent, resolved once below. `'preserve'` is the studio's default:
 * an ordinary save must never change whether a recipe is publicly visible.
 */
export type RecipePublication = 'preserve' | 'publish' | 'unpublish';

export interface SaveRecipeOptions {
    /**
     * Explicitly bring a removed strategy back into My Strategies. Only the
     * studio's Save Recipe button passes this: an automatic persist before Run
     * Live, Backtest, or a schedule toggle must not resurrect what the owner
     * removed.
     */
    restore?: boolean;
}

export async function saveRecipe(
    recipe: PushStrategy,
    userId: string,
    publication: RecipePublication = 'preserve',
    { restore = false }: SaveRecipeOptions = {},
): Promise<StrategyRecipeRecord> {
    assertSingleLlmStage(recipe);
    assertNoPrevOutputPlaceholder(recipe);

    // Strip only the known-obsolete `title` key: a stale browser tab can still
    // hold one and would copy it back into the row, while any stage field the
    // engine adds later must survive the round trip untouched.
    const { title: _obsoleteTitle, ...stage } = recipe.stages[0] as StrategyStage & {
        title?: unknown;
    };
    const sanitizedRecipe: PushStrategy = {
        ...recipe,
        name: normalizeRecipeName(recipe.name),
        stages: [
            {
                ...stage,
                selected_tools: (stage.selected_tools ?? []).filter(
                    (tool) => tool !== 'web_search',
                ),
            },
        ],
    };

    const db = getDbAdminClient();

    const basePayload = {
        name: sanitizedRecipe.name,
        description: sanitizedRecipe.description || '',
        cadence: sanitizedRecipe.cadence,
        graph_json: sanitizedRecipe,
        updated_at: new Date().toISOString(),
    };

    // Only an explicit decision may change publication state, so a published
    // showcase recipe is never silently unpublished by editing it in the studio.
    // Restoring a removed strategy is equally explicit: it is opt-in, never a
    // side effect of the persist that precedes Run Live or Backtest.
    const writePayload = {
        ...basePayload,
        ...(publication === 'preserve' ? {} : { is_public: publication === 'publish' }),
        ...(restore ? { archived_at: null } : {}),
    };

    if (recipe.id) {
        const existing = await db
            .from('strategy_recipes')
            .select('user_id')
            .eq('id', recipe.id)
            .single();

        // Fail closed: an unreadable row must not fall through to the write.
        if (existing.error || !existing.data) {
            throw new Error(`Recipe not found: ${recipe.id}`);
        }
        if (existing.data.user_id !== userId) {
            throw new Error('Unauthorized: cannot modify a recipe owned by another user');
        }

        // user_id and concurrency_config are omitted on update so ownership and custom
        // slot/sizing limits set on the recipe row are preserved across graph edits.
        const { data, error } = await db
            .from('strategy_recipes')
            .update(writePayload)
            .eq('id', recipe.id)
            .eq('user_id', userId)
            .select('*')
            .single();

        if (error) throw new Error(error.message);
        return data as StrategyRecipeRecord;
    }

    const { data, error } = await db
        .from('strategy_recipes')
        .insert({
            ...writePayload,
            is_public: publication === 'publish',
            concurrency_config: {
                max_open_trades: 4,
                max_equity_pct_per_trade: 25.0,
            },
            user_id: userId,
        })
        .select('*')
        .single();

    if (error) throw new Error(error.message);
    return data as StrategyRecipeRecord;
}

export const saveRecipeFn = createServerFn({ method: 'POST' })
    // Publication is an editorial act performed by the showcase publisher CLI,
    // never a client-controlled field: the browser may not flip `is_public`.
    // `restore` is the studio's explicit "bring this removed strategy back".
    .validator((d: { recipe: PushStrategy; restore?: boolean }) => d)
    .handler(async ({ data: { recipe, restore = false } }) => {
        // The user is resolved inside the handler on purpose: the TanStack
        // import-protection plugin only allows the server-only auth import when
        // every use of it sits inside a server-function callback.
        const auth = getAuthServerClient();
        const {
            data: { user },
        } = await auth.auth.getUser();
        if (!user?.id) {
            throw new Error('Unauthorized: please sign in to save recipes');
        }
        return saveRecipe(recipe, user.id, 'preserve', { restore });
    });

export async function fetchRecipeById(
    recipeId: string,
    userId: string,
): Promise<PushStrategy | null> {
    const db = getDbServerClient({ useServiceRole: true });
    const { data, error } = await db
        .from('strategy_recipes')
        .select('id, user_id, name, description, cadence, is_public, is_template, graph_json')
        .eq('id', recipeId)
        .single();

    if (error || !data) {
        throw new Error(`Recipe not found: ${recipeId}`);
    }

    const row = data as StrategyRecipeRecord;
    const isOwner = row.user_id === userId;
    if (!isOwner && !row.is_public && !row.is_template) {
        throw new Error('Unauthorized: cannot open this recipe');
    }

    const graph = row.graph_json;
    if (!graph || !Array.isArray(graph.stages) || graph.stages.length !== 1) {
        return null;
    }

    return {
        ...graph,
        // Preserve id only when owned by caller so editing a shared template creates a fork.
        id: isOwner ? row.id : undefined,
        name: row.name || graph.name,
        description: row.description ?? graph.description,
        cadence: row.cadence || graph.cadence,
    };
}

export const fetchRecipeByIdFn = createServerFn({ method: 'GET' })
    .validator((d: { recipeId: string }) => d)
    .handler(async ({ data: { recipeId } }) => {
        const auth = getAuthServerClient();
        const {
            data: { user },
        } = await auth.auth.getUser();
        if (!user?.id) {
            throw new Error('Unauthorized: please sign in to open Strategy Recipes');
        }
        return fetchRecipeById(recipeId, user.id);
    });

export async function enqueueRecipeJob(
    recipeId: string,
    mode: 'live_turn' | 'backtest',
    userId: string,
    weeksRequested: string[] = [],
) {
    const db = getDbAdminClient();

    const { data: recipe, error: recipeError } = await db
        .from('strategy_recipes')
        .select('id, user_id, is_public, is_template, archived_at, graph_json')
        .eq('id', recipeId)
        .single();

    if (recipeError || !recipe) {
        throw new Error(`Recipe not found: ${recipeId}`);
    }

    const isOwner = recipe.user_id === userId;
    if (!isOwner && !recipe.is_public && !recipe.is_template) {
        throw new Error('Unauthorized: cannot run this recipe');
    }

    // Fail closed: a strategy the owner removed from My Strategies must be
    // saved explicitly before it can spend quota again.
    if (isOwner && recipe.archived_at) {
        throw new Error(
            'This strategy was removed from My Strategies. Save it to restore before running it.',
        );
    }

    // A legacy or malformed recipe must not reach the queue: the worker would
    // reject it and leave a failed queue row behind on every cycle.
    const graph = recipe.graph_json as PushStrategy | null;
    if (!graph) throw new Error('Recipe has no strategy graph');
    assertSingleLlmStage(graph);
    assertNoPrevOutputPlaceholder(graph);

    await assertQuotaAllowsJob(userId, mode);

    const payload = {
        recipe_id: recipeId,
        user_id: userId,
        mode,
        priority: mode === 'live_turn' ? 1 : 10,
        status: 'pending',
        provider: 'free-llm-proxy',
        model: mode === 'live_turn' ? 'auto-go' : 'strata-auto-go',
        weeks_requested: weeksRequested,
        progress_pct: 0,
    };

    const { data, error } = await db
        .from('recipe_execution_queue')
        .insert(payload)
        .select('*')
        .single();

    if (error) throw new Error(error.message);
    return data;
}

export const enqueueRecipeJobFn = createServerFn({ method: 'POST' })
    .validator(
        (d: { recipeId: string; mode: 'live_turn' | 'backtest'; weeksRequested?: string[] }) => d,
    )
    .handler(async ({ data: { recipeId, mode, weeksRequested = ['2026-W10'] } }) => {
        const auth = getAuthServerClient();
        const {
            data: { user },
        } = await auth.auth.getUser();
        if (!user?.id) {
            throw new Error('Unauthorized: please sign in to run Strategy Recipes');
        }
        return enqueueRecipeJob(recipeId, mode, user.id, weeksRequested);
    });
