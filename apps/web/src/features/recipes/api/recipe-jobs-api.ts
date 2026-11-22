import { createServerFn } from '@tanstack/react-start';
import { getAuthServerClient } from '~/lib/auth';
import { getDbServerClient } from '~/lib/db';
import type { RecipeCadence, RecipeJobRecord, RecipeRunDetail } from '../types';

/**
 * Read slice for recipe execution jobs.
 *
 * `recipe_execution_queue` is service-role only, so every read here goes through
 * the admin client and is scoped to the requesting user's rows.
 */

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
        if (!user?.id) {
            throw new Error('Unauthorized: please sign in to view job status');
        }
        return getRecipeJobStatus(jobId, user.id);
    });

/**
 * The newest run for one recipe, used by the /build status strip. Reading per
 * recipe keeps it index-aligned and correct once a user's recent-jobs window is
 * full — a global top-N window would drop a still-pending older run.
 */
export async function fetchLatestRecipeRun(
    recipeId: string,
    userId: string,
): Promise<RecipeJobRecord | null> {
    const db = getDbServerClient({ useServiceRole: true });
    const { data, error } = await db
        .from('recipe_execution_queue')
        .select(
            'id, recipe_id, mode, status, progress_pct, provider, model, result_json, error_message, created_at, started_at, completed_at',
        )
        .eq('recipe_id', recipeId)
        .eq('user_id', userId)
        .eq('mode', 'backtest')
        .order('created_at', { ascending: false })
        .limit(1)
        .maybeSingle();

    if (error) throw new Error(`${error.code ?? 'error'}: ${error.message}`);
    return (data as RecipeJobRecord | null) ?? null;
}

export const fetchLatestRecipeRunFn = createServerFn({ method: 'GET' })
    .validator((d: { recipeId: string }) => d)
    .handler(async ({ data: { recipeId } }) => {
        const auth = getAuthServerClient();
        const {
            data: { user },
        } = await auth.auth.getUser();
        if (!user?.id) {
            throw new Error('Unauthorized: please sign in to view backtest runs');
        }
        return fetchLatestRecipeRun(recipeId, user.id);
    });

async function resolveQueuePosition(
    db: ReturnType<typeof getDbServerClient>,
    job: RecipeJobRecord,
): Promise<{ queuePosition: number | null; globalActiveBacktests: number }> {
    if (job.mode === 'live_turn' || (job.status !== 'pending' && job.status !== 'processing')) {
        return { queuePosition: null, globalActiveBacktests: 0 };
    }
    const { data: activeRows } = await db
        .from('recipe_execution_queue')
        .select('id, priority, status, created_at')
        .eq('mode', 'backtest')
        .in('status', ['pending', 'processing'])
        .order('priority', { ascending: true })
        .order('created_at', { ascending: true })
        .limit(100);

    const rows = Array.isArray(activeRows)
        ? (activeRows as Array<{
              id: string;
              priority?: number;
              status: string;
              created_at?: string;
          }>)
        : [];
    if (rows.length === 0) {
        return { queuePosition: null, globalActiveBacktests: 0 };
    }
    const globalActiveBacktests = rows.filter((r) => r.status === 'processing').length;
    if (job.status === 'processing') {
        return { queuePosition: 0, globalActiveBacktests };
    }
    const selfRow = rows.find((r) => r.id === job.id);
    const selfPriority = selfRow?.priority ?? 10;
    const createdAt = job.created_at || '';
    const aheadCount = rows.filter(
        (r) =>
            r.status === 'processing' ||
            (r.id !== job.id &&
                ((r.priority ?? 10) < selfPriority ||
                    ((r.priority ?? 10) === selfPriority && (r.created_at || '') < createdAt))),
    ).length;
    return { queuePosition: aheadCount + 1, globalActiveBacktests };
}

export async function fetchRecipeRunDetail(
    jobId: string,
    userId: string,
): Promise<RecipeRunDetail> {
    const job = await getRecipeJobStatus(jobId, userId);
    const db = getDbServerClient({ useServiceRole: true });
    const queueMeta = await resolveQueuePosition(db, job);
    if (!job.recipe_id) {
        return { job, recipeName: null, recipeCadence: null, ...queueMeta };
    }
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
        ...queueMeta,
    };
}

export const fetchRecipeRunDetailFn = createServerFn({ method: 'GET' })
    .validator((d: { jobId: string }) => d)
    .handler(async ({ data: { jobId } }) => {
        const auth = getAuthServerClient();
        const {
            data: { user },
        } = await auth.auth.getUser();
        if (!user?.id) {
            throw new Error('Unauthorized: please sign in to view backtest runs');
        }
        return fetchRecipeRunDetail(jobId, user.id);
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
    if (!user?.id) {
        throw new Error('Unauthorized: please sign in to view backtest history');
    }
    return fetchRecentBacktestJobs(user.id);
});
