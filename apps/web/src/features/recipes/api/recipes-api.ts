import { createServerFn } from '@tanstack/react-start';
import { getAuthServerClient } from '~/lib/auth';
import { getDbAdminClient, getDbServerClient } from '~/lib/db';
import type { PushStrategy, StrategyRecipeRecord, StrategyStage } from '../types';
import { assertQuotaAllowsJob } from './recipes-quota-api';
import { invalidatePublicRecipeCache } from './recipes-studio-api';
import {
    assertNoPrevOutputPlaceholder,
    assertSingleLlmStage,
    normalizeRecipeName,
} from './recipes-validators';
import { refundToken, reserveToken } from './token-ledger';

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
        invalidatePublicRecipeCache(recipe.id);
        return data as StrategyRecipeRecord;
    }

    const { data, error } = await db
        .from('strategy_recipes')
        .insert({
            ...writePayload,
            is_public: publication !== 'unpublish',
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
    // Publication is an editorial act performed by the showcase publisher CLI;
    // this path cannot flip `is_public`, so a studio persist never changes
    // visibility as a side effect. The owner's public/private opt-out has its
    // own server function, `setRecipeVisibilityFn`.
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

/**
 * Inserts the queue row and owns the token spend around it: reserve after every
 * validation has passed, refund if the insert itself fails. Kept out of
 * `enqueueRecipeJob` so the validation ladder stays under the complexity ceiling.
 */
async function insertQueueRow(
    db: ReturnType<typeof getDbAdminClient>,
    payload: Record<string, unknown>,
    spend?: { ownerKey: string; jobId: string },
) {
    if (spend) await reserveToken(spend.ownerKey, 'backtest', spend.jobId);

    const { data, error } = await db
        .from('recipe_execution_queue')
        .insert(payload)
        .select('*')
        .single();

    if (!error) return data;

    if (spend) {
        try {
            await refundToken(spend.jobId, 'failed');
        } catch (refundError) {
            console.error('Token refund failed after enqueue error', refundError);
        }
    }
    throw new Error(error.message);
}

export async function enqueueRecipeJob(
    recipeId: string,
    mode: 'backtest',
    userId: string,
    weeksRequested: string[] = [],
    spend?: { ownerKey: string; jobId: string },
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

    // Tokens replace the legacy 2/day backtest cap: when a spend is attached the
    // balance and the guest daily budget are the bounds, so the old quota is
    // skipped. Callers without a spend (internal/legacy paths) keep the check.
    if (!spend) await assertQuotaAllowsJob(userId, mode);

    // First run jumps the queue but never preempts a running backtest: priority
    // only reorders pending jobs (pop_next_recipe_job orders priority ASC).
    const { count: completedBacktests } = await db
        .from('recipe_execution_queue')
        .select('id', { count: 'exact', head: true })
        .eq('user_id', userId)
        .eq('mode', 'backtest')
        .eq('status', 'completed');

    const payload = {
        ...(spend ? { id: spend.jobId } : {}),
        recipe_id: recipeId,
        user_id: userId,
        mode,
        priority: (completedBacktests ?? 0) === 0 ? 0 : 10,
        status: 'pending',
        provider: 'free-llm-proxy',
        model: 'auto-go',
        weeks_requested: weeksRequested,
        progress_pct: 0,
    };

    // Spend only after every validation passed, and always against the queue id
    // so a refund can name a row that really exists.
    return insertQueueRow(db, payload, spend);
}

export const enqueueRecipeJobFn = createServerFn({ method: 'POST' })
    .validator((d: { recipeId: string; mode: 'backtest'; weeksRequested?: string[] }) => d)
    .handler(async ({ data: { recipeId, mode, weeksRequested = ['2026-W10'] } }) => {
        const auth = getAuthServerClient();
        const {
            data: { user },
        } = await auth.auth.getUser();
        if (!user?.id) {
            throw new Error('Unauthorized: please sign in to run Strategy Recipes');
        }
        return enqueueRecipeJob(recipeId, mode, user.id, weeksRequested, {
            ownerKey: `user:${user.id}`,
            jobId: crypto.randomUUID(),
        });
    });

/**
 * Sentinel owner for guest queue rows. The queue's user_id has no foreign key to
 * auth.users, so a logged-out run can be queued without inventing an account;
 * the guest's identity lives in the signed cookie and the token ledger.
 */
export const ANONYMOUS_USER_ID = '00000000-0000-0000-0000-000000000000';

/**
 * Runs a public or template recipe for a logged-out visitor, spending one of
 * their five guest tokens. The module is imported dynamically so node:crypto and
 * the server cookie helpers stay out of the client bundle.
 */
export const startGuestBacktestFn = createServerFn({ method: 'POST' })
    .validator((d: { recipeId: string; weeksRequested?: string[] }) => d)
    .handler(async ({ data: { recipeId, weeksRequested = [] } }) => {
        const { ensureGuestSession } = await import('~/shared/auth/guest-session');
        const guest = await ensureGuestSession();
        return enqueueRecipeJob(recipeId, 'backtest', ANONYMOUS_USER_ID, weeksRequested, {
            ownerKey: guest.ownerKey,
            jobId: crypto.randomUUID(),
        });
    });

/**
 * How many guest runs the caller has left. Read-only: it never mints, so a
 * crawler loading the demo does not create a session row.
 */
export const fetchGuestBalanceFn = createServerFn({ method: 'POST' }).handler(async () => {
    const { readGuestBalance } = await import('~/shared/auth/guest-session');
    return readGuestBalance();
});

/**
 * Status read for a guest run. The caller has no account, so the unguessable
 * job id is the whole handle; this returns progress and an error string only,
 * never the result payload or the owner.
 */
export const fetchGuestJobFn = createServerFn({ method: 'POST' })
    .validator((d: { jobId: string }) => d)
    .handler(async ({ data: { jobId } }) => {
        const db = getDbAdminClient();
        const { data, error } = await db
            .from('recipe_execution_queue')
            .select('id, recipe_id, status, progress_pct, error_message')
            .eq('id', jobId)
            .maybeSingle();

        if (error) throw new Error(error.message);
        return data as {
            id: string;
            recipe_id: string;
            status: string;
            progress_pct: number | null;
            error_message: string | null;
        } | null;
    });
