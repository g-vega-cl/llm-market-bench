import { createServerFn } from '@tanstack/react-start';
import { getAuthServerClient } from '~/lib/auth';
import { getDbAdminClient, getDbServerClient } from '~/lib/db';
import type {
    PushStrategy,
    RecipeCadence,
    RecipeJobRecord,
    RecipeRunDetail,
    StrategyRecipeRecord,
    StrategyStage,
} from '../types';

const ANONYMOUS_USER_ID = '00000000-0000-0000-0000-000000000000';
const PREV_OUTPUT_PLACEHOLDER = '{{prev_output}}';
const MAX_OPEN_JOBS_PER_USER = 5;

export function assertSingleLlmStage(recipe: { stages: readonly StrategyStage[] }): void {
    if (!Array.isArray(recipe.stages) || recipe.stages.length !== 1) {
        throw new Error('Invalid strategy: must contain exactly one LLM stage');
    }
}

export function assertNoPrevOutputPlaceholder(recipe: { stages: readonly StrategyStage[] }): void {
    for (const stage of recipe.stages ?? []) {
        for (const block of stage.blocks ?? []) {
            if (block.type === 'prompt' && block.text.includes(PREV_OUTPUT_PLACEHOLDER)) {
                throw new Error(
                    'Invalid strategy: prev_output is not available in a single-stage strategy',
                );
            }
        }
    }
}

export async function fetchPublicRecipes(): Promise<StrategyRecipeRecord[]> {
    const db = getDbServerClient();
    const { data, error } = await db
        .from('strategy_recipes')
        .select('*')
        .or('is_public.eq.true,is_template.eq.true')
        .order('updated_at', { ascending: false })
        .limit(20);

    if (error) {
        throw new Error(error.message);
    }
    return (data || []) as StrategyRecipeRecord[];
}

export async function saveRecipe(
    recipe: PushStrategy,
    userId: string,
    isPublic = false,
): Promise<StrategyRecipeRecord> {
    assertSingleLlmStage(recipe);
    assertNoPrevOutputPlaceholder(recipe);

    const db = getDbAdminClient();

    const payload = {
        name: recipe.name,
        description: recipe.description || '',
        cadence: recipe.cadence,
        graph_json: recipe,
        concurrency_config: {
            max_open_trades: 3,
            max_equity_pct_per_trade: 33.3,
        },
        is_public: isPublic,
        updated_at: new Date().toISOString(),
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

        // user_id is deliberately absent from the update payload: ownership is
        // never transferred, and the row is scoped to the owner it was read with.
        const { data, error } = await db
            .from('strategy_recipes')
            .update(payload)
            .eq('id', recipe.id)
            .eq('user_id', userId)
            .select('*')
            .single();

        if (error) throw new Error(error.message);
        return data as StrategyRecipeRecord;
    }

    const { data, error } = await db
        .from('strategy_recipes')
        .insert({ ...payload, user_id: userId })
        .select('*')
        .single();

    if (error) throw new Error(error.message);
    return data as StrategyRecipeRecord;
}

export const saveRecipeFn = createServerFn({ method: 'POST' })
    .validator((d: { recipe: PushStrategy; isPublic?: boolean }) => d)
    .handler(async ({ data: { recipe, isPublic = false } }) => {
        // The user is resolved inside the handler on purpose: the TanStack
        // import-protection plugin only allows the server-only auth import when
        // every use of it sits inside a server-function callback.
        const auth = getAuthServerClient();
        const {
            data: { user },
        } = await auth.auth.getUser();
        const userId = user?.id || ANONYMOUS_USER_ID;
        return saveRecipe(recipe, userId, isPublic);
    });

export async function getRecipeJobStatus(jobId: string, userId: string): Promise<RecipeJobRecord> {
    // recipe_execution_queue is service-role only, so this read needs the admin
    // client. It is scoped to the requesting user's rows.
    const db = getDbServerClient({ useServiceRole: true });
    const { data, error } = await db
        .from('recipe_execution_queue')
        .select(
            'id, recipe_id, mode, status, progress_pct, provider, model, result_json, error_message, created_at, started_at, completed_at',
        )
        .eq('id', jobId)
        .eq('user_id', userId)
        .single();

    if (error) throw new Error(error.message);
    return data as RecipeJobRecord;
}

export const getRecipeJobStatusFn = createServerFn({ method: 'GET' })
    .validator((d: { jobId: string }) => d)
    .handler(async ({ data: { jobId } }) => {
        const auth = getAuthServerClient();
        const {
            data: { user },
        } = await auth.auth.getUser();
        const userId = user?.id || ANONYMOUS_USER_ID;
        return getRecipeJobStatus(jobId, userId);
    });

export async function fetchRecipeRunDetail(
    jobId: string,
    userId: string,
): Promise<RecipeRunDetail> {
    const job = await getRecipeJobStatus(jobId, userId);
    if (!job.recipe_id) {
        return { job, recipeName: null, recipeCadence: null };
    }
    const db = getDbServerClient({ useServiceRole: true });
    const { data } = await db
        .from('strategy_recipes')
        .select('id, name, cadence')
        .eq('id', job.recipe_id)
        .single();

    const row = data as { id?: string; name?: string; cadence?: RecipeCadence } | null;
    return {
        job,
        recipeName: row?.name ?? null,
        recipeCadence: row?.cadence ?? null,
    };
}

export const fetchRecipeRunDetailFn = createServerFn({ method: 'GET' })
    .validator((d: { jobId: string }) => d)
    .handler(async ({ data: { jobId } }) => {
        const auth = getAuthServerClient();
        const {
            data: { user },
        } = await auth.auth.getUser();
        const userId = user?.id || ANONYMOUS_USER_ID;
        return fetchRecipeRunDetail(jobId, userId);
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
        const userId = user?.id || ANONYMOUS_USER_ID;
        return fetchRecipeById(recipeId, userId);
    });

export async function fetchRecentBacktestJobs(
    userId: string,
    limit = 8,
): Promise<RecipeJobRecord[]> {
    const db = getDbServerClient({ useServiceRole: true });
    const { data, error } = await db
        .from('recipe_execution_queue')
        .select(
            'id, recipe_id, mode, status, progress_pct, provider, model, result_json, error_message, created_at, started_at, completed_at',
        )
        .eq('user_id', userId)
        .eq('mode', 'backtest')
        .order('created_at', { ascending: false })
        .limit(limit);

    if (error) throw new Error(error.message);
    return (data || []) as RecipeJobRecord[];
}

export const fetchRecentBacktestJobsFn = createServerFn({ method: 'GET' }).handler(async () => {
    const auth = getAuthServerClient();
    const {
        data: { user },
    } = await auth.auth.getUser();
    const userId = user?.id || ANONYMOUS_USER_ID;
    return fetchRecentBacktestJobs(userId);
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
        .select('id, user_id, is_public, is_template, graph_json')
        .eq('id', recipeId)
        .single();

    if (recipeError || !recipe) {
        throw new Error(`Recipe not found: ${recipeId}`);
    }

    const isOwner = recipe.user_id === userId;
    if (!isOwner && !recipe.is_public && !recipe.is_template) {
        throw new Error('Unauthorized: cannot run this recipe');
    }

    // A legacy or malformed recipe must not reach the queue: the worker would
    // reject it and leave a failed queue row behind on every cycle.
    const graph = recipe.graph_json as PushStrategy | null;
    if (!graph) throw new Error('Recipe has no strategy graph');
    assertSingleLlmStage(graph);
    assertNoPrevOutputPlaceholder(graph);

    const { data: openJobs } = await db
        .from('recipe_execution_queue')
        .select('id')
        .eq('user_id', userId)
        .in('status', ['pending', 'processing'])
        .limit(MAX_OPEN_JOBS_PER_USER + 1);

    if ((openJobs?.length ?? 0) >= MAX_OPEN_JOBS_PER_USER) {
        throw new Error('Too many queued recipe jobs. Wait for the running jobs to finish.');
    }

    const payload = {
        recipe_id: recipeId,
        user_id: userId,
        mode,
        priority: mode === 'live_turn' ? 1 : 10,
        status: 'pending',
        provider: 'auto-strata',
        model: 'strata',
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
        const userId = user?.id || ANONYMOUS_USER_ID;
        return enqueueRecipeJob(recipeId, mode, userId, weeksRequested);
    });
