import { createServerFn } from '@tanstack/react-start';
import { getAuthServerClient } from '~/lib/auth';
import { getDbAdminClient } from '~/lib/db';
import type {
    RecipeJobRecord,
    RecipeRunDetail,
    RecipeSummaryItem,
    RecipeUserQuotaStatus,
} from '../types';
import { canActivateTurboEt, getEtDateString } from '../utils/market-hours';
import { assertNoPrevOutputPlaceholder, assertSingleLlmStage } from './recipes-validators';

export const BETA_STARTER_LIMITS = {
    tier: 'beta_starter',
    maxConcurrentBacktests: 1,
    dailyBacktestLimit: 2,
    // Live turns are unbounded per user: the live-bot cap below already bounds
    // regular 30m ET market-hours slots, and Turbo is capped at 1x/day per user.
    dailyLiveTurnLimit: Number.POSITIVE_INFINITY,
    maxLiveRecipes: 3,
    globalQueueCap: 20,
} as const;

interface QuotaOverrideRow {
    tier?: string;
    max_concurrent_backtests?: number;
    daily_backtest_limit?: number;
    daily_live_turn_limit?: number;
    max_live_recipes?: number;
    last_turbo_et_date?: string | null;
}

interface QueueQuotaRow {
    id: string;
    user_id: string;
    mode: 'backtest' | 'live_turn';
    status: string;
    created_at: string;
    started_at?: string | null;
}

export async function fetchRecipeQuotaStatus(userId: string): Promise<RecipeUserQuotaStatus> {
    const db = getDbAdminClient();
    const since24hIso = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString();

    const [
        { data: overrideData },
        { data: userRecentRows },
        { data: userActiveBacktestRows },
        { data: globalActiveRows },
        { data: liveRecipeRows },
    ] = await Promise.all([
        db
            .from('recipe_user_quotas')
            .select(
                'tier, max_concurrent_backtests, daily_backtest_limit, daily_live_turn_limit, max_live_recipes, last_turbo_et_date',
            )
            .eq('user_id', userId)
            .maybeSingle(),
        db
            .from('recipe_execution_queue')
            .select('id, user_id, mode, status, created_at, started_at')
            .eq('user_id', userId)
            .gte('created_at', since24hIso)
            .neq('status', 'cancelled')
            .limit(200),
        db
            .from('recipe_execution_queue')
            .select('id, user_id, mode, status, created_at, started_at')
            .eq('user_id', userId)
            .eq('mode', 'backtest')
            .in('status', ['pending', 'processing'])
            .limit(25),
        db
            .from('recipe_execution_queue')
            .select('id, user_id, mode, status, created_at')
            .eq('mode', 'backtest')
            .in('status', ['pending', 'processing'])
            .order('created_at', { ascending: true })
            .limit(BETA_STARTER_LIMITS.globalQueueCap + 5),
        db
            .from('strategy_recipes')
            .select('id, user_id, is_live')
            .eq('user_id', userId)
            .eq('is_live', true)
            .limit(25),
    ]);

    const override = (overrideData || {}) as QuotaOverrideRow;
    const recent = (userRecentRows || []) as QueueQuotaRow[];
    const userActiveBacktests = (userActiveBacktestRows || []) as QueueQuotaRow[];
    const globalRows = (globalActiveRows || []) as QueueQuotaRow[];

    const activeBacktests = userActiveBacktests.length;
    // A run burns the allowance once it has actually started: completed runs
    // count, and so does a run the user cancelled after it spent LLM calls.
    // Never-started rows and provider failures do not, so a bad free-tier model
    // cannot lock someone out for a day.
    const backtestsLast24h = recent.filter(
        (row) => row.mode === 'backtest' && (row.status === 'completed' || Boolean(row.started_at)),
    ).length;
    const liveTurnsLast24h = recent.filter((row) => row.mode === 'live_turn').length;

    const lastTurboEtDate = override.last_turbo_et_date ?? null;
    const todayEt = getEtDateString(new Date());

    return {
        tier: override.tier || BETA_STARTER_LIMITS.tier,
        activeBacktests,
        maxConcurrentBacktests:
            override.max_concurrent_backtests ?? BETA_STARTER_LIMITS.maxConcurrentBacktests,
        backtestsLast24h,
        dailyBacktestLimit: override.daily_backtest_limit ?? BETA_STARTER_LIMITS.dailyBacktestLimit,
        liveTurnsLast24h,
        dailyLiveTurnLimit:
            override.daily_live_turn_limit ?? BETA_STARTER_LIMITS.dailyLiveTurnLimit,
        activeLiveRecipes: (liveRecipeRows || []).length,
        maxLiveRecipes: override.max_live_recipes ?? BETA_STARTER_LIMITS.maxLiveRecipes,
        globalPendingBacktests: globalRows.length,
        globalQueueCap: BETA_STARTER_LIMITS.globalQueueCap,
        lastTurboEtDate,
        turboUsedToday: lastTurboEtDate === todayEt,
    };
}

export async function assertQuotaAllowsJob(
    userId: string,
    mode: 'backtest',
): Promise<RecipeUserQuotaStatus> {
    const quota = await fetchRecipeQuotaStatus(userId);
    if (mode === 'backtest') {
        if (quota.activeBacktests >= quota.maxConcurrentBacktests) {
            throw new Error(
                `Concurrent backtest limit reached (${quota.activeBacktests}/${quota.maxConcurrentBacktests} active). Cancel or wait for it to finish.`,
            );
        }
        if (quota.backtestsLast24h >= quota.dailyBacktestLimit) {
            throw new Error(
                `Daily backtest limit reached (${quota.backtestsLast24h}/${quota.dailyBacktestLimit} in 24h). Come back tomorrow or request higher capacity via Waitlist.`,
            );
        }
        if (quota.globalPendingBacktests >= quota.globalQueueCap) {
            throw new Error(
                `Backtest queue is currently full (${quota.globalPendingBacktests}/${quota.globalQueueCap}). Live auto-go turns still run normally; please retry shortly or join Waitlist.`,
            );
        }
    }
    return quota;
}

export async function cancelRecipeJob(
    jobId: string,
    userId: string,
): Promise<{ id: string; status: 'cancelled' }> {
    const db = getDbAdminClient();
    const { data, error } = await db
        .from('recipe_execution_queue')
        .update({
            status: 'cancelled',
            cancelled_at: new Date().toISOString(),
        })
        .eq('id', jobId)
        .eq('user_id', userId)
        .in('status', ['pending', 'processing'])
        .select('id, status')
        .single();

    if (error || !data) {
        throw new Error('Unable to cancel job: either already settled or unauthorized.');
    }
    return { id: String((data as { id: string }).id), status: 'cancelled' };
}

export async function toggleLiveSchedule(
    recipeId: string,
    isLive: boolean,
    userId: string,
): Promise<{ id: string; is_live: boolean }> {
    const db = getDbAdminClient();
    const { data: existing, error: fetchErr } = await db
        .from('strategy_recipes')
        .select('id, user_id, is_live, archived_at, graph_json')
        .eq('id', recipeId)
        .single();

    if (fetchErr || !existing) {
        throw new Error(`Recipe not found: ${recipeId}`);
    }
    const row = existing as {
        id: string;
        user_id: string;
        is_live: boolean;
        archived_at?: string | null;
        graph_json: Parameters<typeof assertSingleLlmStage>[0] &
            Parameters<typeof assertNoPrevOutputPlaceholder>[0];
    };
    if (row.user_id !== userId) {
        throw new Error('Unauthorized: cannot modify live schedule for another user');
    }
    if (row.archived_at) {
        throw new Error(
            'This strategy was removed from My Strategies. Save it to restore before scheduling it live.',
        );
    }

    if (isLive) {
        assertSingleLlmStage(row.graph_json);
        assertNoPrevOutputPlaceholder(row.graph_json);
        const quota = await fetchRecipeQuotaStatus(userId);
        if (!row.is_live && quota.activeLiveRecipes >= quota.maxLiveRecipes) {
            throw new Error(
                `Scheduled live limit reached (${quota.activeLiveRecipes}/${quota.maxLiveRecipes}). Pause your existing live recipe first.`,
            );
        }
    }

    const nowIso = new Date().toISOString();
    const updatePayload: Record<string, unknown> = {
        is_live: isLive,
        updated_at: nowIso,
    };
    if (!isLive) {
        updatePayload.turbo_expires_at = null;
    }

    const { data: updated, error: updErr } = await db
        .from('strategy_recipes')
        .update(updatePayload)
        .eq('id', recipeId)
        .eq('user_id', userId)
        .select('id, is_live')
        .single();

    if (updErr || !updated) {
        throw new Error(updErr?.message || 'Failed updating live schedule');
    }

    if (!isLive) {
        const { error: cancelErr } = await db
            .from('recipe_execution_queue')
            .update({ status: 'cancelled', cancelled_at: nowIso })
            .eq('recipe_id', recipeId)
            .eq('user_id', userId)
            .eq('mode', 'live_turn')
            .eq('status', 'pending');
        if (cancelErr) {
            console.error('[recipes] failed cancelling pending live_turn jobs on pause', cancelErr);
        }
    }

    return updated as { id: string; is_live: boolean };
}

export async function activateRecipeTurbo(
    recipeId: string,
    userId: string,
    now: Date = new Date(),
): Promise<{ recipeId: string; turboExpiresAt: string; enqueuedJobId: string | null }> {
    if (!canActivateTurboEt(now)) {
        throw new Error('Turbo is only available during US market hours (Mon-Fri 09:30-15:55 ET).');
    }

    const db = getDbAdminClient();
    const { data, error } = await db.rpc('activate_recipe_turbo', {
        p_user_id: userId,
        p_recipe_id: recipeId,
    });

    if (error) {
        throw new Error(error.message || 'Failed activating Turbo mode');
    }

    const rows = Array.isArray(data) ? data : data ? [data] : [];
    const row = rows[0] as
        | { recipe_id?: string; turbo_expires_at?: string; enqueued_job_id?: string | null }
        | undefined;
    if (!row?.recipe_id || !row?.turbo_expires_at) {
        throw new Error('Failed activating Turbo mode: empty response');
    }

    return {
        recipeId: String(row.recipe_id),
        turboExpiresAt: String(row.turbo_expires_at),
        enqueuedJobId: row.enqueued_job_id ? String(row.enqueued_job_id) : null,
    };
}

export async function fetchUserRecipes(userId: string): Promise<RecipeSummaryItem[]> {
    const db = getDbAdminClient();
    const { data, error } = await db
        .from('strategy_recipes')
        .select('id, name, cadence, is_live, trial_count, updated_at, turbo_expires_at')
        .eq('user_id', userId)
        // Removed strategies stay in the database; they are only hidden here.
        .is('archived_at', null)
        .order('updated_at', { ascending: false })
        .limit(20);

    if (error) throw new Error(error.message);
    return (data || []) as RecipeSummaryItem[];
}

const SHOWCASE_PIN_ROW_ID = 1;

interface ShowcasePinRow {
    job_id: string | null;
    recipe_id: string | null;
    headline: string | null;
    recipe_name: string | null;
}

const SHOWCASE_JOB_COLUMNS =
    'id, recipe_id, mode, status, progress_pct, provider, model, result_json, error_message, created_at, started_at, completed_at';

/** A silent read failure here is exactly the empty-page bug this path exists to fix. */
function logShowcaseReadFailure(step: string, error: { message: string } | null): void {
    if (error) console.error(`[recipes-demo] showcase ${step} read failed; degrading`, error);
}

async function fetchPinnedShowcaseBacktest(
    db: ReturnType<typeof getDbAdminClient>,
): Promise<RecipeRunDetail | null> {
    // The pin table may not exist before its migration lands. A failed read must
    // degrade to the is_public heuristic instead of breaking the public route.
    const { data: pin, error: pinError } = await db
        .from('recipe_showcase')
        .select('job_id, recipe_id, headline, recipe_name')
        .eq('id', SHOWCASE_PIN_ROW_ID)
        .maybeSingle();
    logShowcaseReadFailure('pin', pinError);

    const pinned = pin as ShowcasePinRow | null;
    if (!pinned?.job_id) return null;

    const { data: jobRow, error: jobError } = await db
        .from('recipe_execution_queue')
        .select(SHOWCASE_JOB_COLUMNS)
        .eq('id', pinned.job_id)
        .maybeSingle();
    logShowcaseReadFailure('pinned job', jobError);

    const job = jobRow as RecipeJobRecord | null;
    if (!job || job.mode !== 'backtest' || job.status !== 'completed' || !job.result_json) {
        return null;
    }

    const recipeId = pinned.recipe_id || job.recipe_id || '';
    const { data: recipeRow, error: recipeError } = recipeId
        ? await db
              .from('strategy_recipes')
              .select('id, name, cadence')
              .eq('id', recipeId)
              .maybeSingle()
        : { data: null, error: null };
    logShowcaseReadFailure('pinned recipe', recipeError);

    const recipe = recipeRow as {
        id: string;
        name: string;
        cadence: RecipeRunDetail['recipeCadence'];
    } | null;

    return {
        job,
        // The pin freezes the name at publish time, so a later studio rename
        // cannot restyle a run it did not produce.
        recipeName:
            pinned.headline || pinned.recipe_name || recipe?.name || 'Public Showcase Backtest',
        recipeCadence: recipe?.cadence ?? '3h',
        queuePosition: null,
        globalActiveBacktests: 0,
    };
}

/**
 * Cheap cache probe for the SSR document middleware: is a showcase pinned?
 *
 * Costs one small round-trip and runs only on a cache miss, so it never appears
 * on the hot path. A failed read must not cache the page (`false`), otherwise a
 * transient PostgREST error would be frozen into the CDN for 72 hours.
 */
export async function hasPublishedShowcase(): Promise<boolean> {
    const db = getDbAdminClient();
    const { data, error } = await db
        .from('recipe_showcase')
        .select('job_id')
        .eq('id', SHOWCASE_PIN_ROW_ID)
        .maybeSingle();

    if (error) {
        console.error('[recipes-demo] showcase pin probe failed; not caching the page', error);
        return false;
    }

    return Boolean((data as { job_id: string | null } | null)?.job_id);
}

export async function fetchPublicShowcaseBacktest(): Promise<RecipeRunDetail | null> {
    const db = getDbAdminClient();

    const pinned = await fetchPinnedShowcaseBacktest(db);
    if (pinned) return pinned;

    const { data: pubRecipes, error: recipesError } = await db
        .from('strategy_recipes')
        .select('id, name, cadence')
        .eq('is_public', true)
        // A removed strategy must never fall through to the public showcase.
        .is('archived_at', null)
        .order('trial_count', { ascending: false })
        .limit(10);
    logShowcaseReadFailure('public recipes', recipesError);

    const recipes = (pubRecipes || []) as Array<{
        id: string;
        name: string;
        cadence: RecipeRunDetail['recipeCadence'];
    }>;
    if (recipes.length === 0) return null;

    const recipeMap = new Map(recipes.map((r) => [r.id, r]));
    const { data: jobs, error: jobsError } = await db
        .from('recipe_execution_queue')
        .select(SHOWCASE_JOB_COLUMNS)
        .in(
            'recipe_id',
            recipes.map((r) => r.id),
        )
        .eq('mode', 'backtest')
        .eq('status', 'completed')
        .order('completed_at', { ascending: false })
        .limit(5);
    logShowcaseReadFailure('public runs', jobsError);

    const picked = ((jobs || []) as RecipeJobRecord[]).find((j) => Boolean(j.result_json));
    if (!picked) return null;
    const meta = picked.recipe_id ? recipeMap.get(picked.recipe_id) : undefined;
    return {
        job: picked,
        recipeName: meta?.name ?? 'Public Showcase Backtest',
        recipeCadence: meta?.cadence ?? '3h',
        queuePosition: null,
        globalActiveBacktests: 0,
    };
}

export const fetchRecipeQuotaStatusFn = createServerFn({ method: 'GET' }).handler(async () => {
    const auth = getAuthServerClient();
    const {
        data: { user },
    } = await auth.auth.getUser();
    if (!user?.id) throw new Error('Unauthorized: please sign in to access Strategy Recipes');
    return fetchRecipeQuotaStatus(user.id);
});

export const cancelRecipeJobFn = createServerFn({ method: 'POST' })
    .validator((d: { jobId: string }) => d)
    .handler(async ({ data: { jobId } }) => {
        const auth = getAuthServerClient();
        const {
            data: { user },
        } = await auth.auth.getUser();
        if (!user?.id) throw new Error('Unauthorized: please sign in to cancel jobs');
        return cancelRecipeJob(jobId, user.id);
    });

export const toggleLiveScheduleFn = createServerFn({ method: 'POST' })
    .validator((d: { recipeId: string; isLive: boolean }) => d)
    .handler(async ({ data: { recipeId, isLive } }) => {
        const auth = getAuthServerClient();
        const {
            data: { user },
        } = await auth.auth.getUser();
        if (!user?.id) throw new Error('Unauthorized: please sign in to manage live schedules');
        return toggleLiveSchedule(recipeId, isLive, user.id);
    });

export const activateRecipeTurboFn = createServerFn({ method: 'POST' })
    .validator((d: { recipeId: string }) => d)
    .handler(async ({ data: { recipeId } }) => {
        const auth = getAuthServerClient();
        const {
            data: { user },
        } = await auth.auth.getUser();
        if (!user?.id) throw new Error('Unauthorized: please sign in to activate Turbo');
        return activateRecipeTurbo(recipeId, user.id);
    });

export const fetchUserRecipesFn = createServerFn({ method: 'GET' }).handler(async () => {
    const auth = getAuthServerClient();
    const {
        data: { user },
    } = await auth.auth.getUser();
    if (!user?.id) throw new Error('Unauthorized: please sign in to view saved recipes');
    return fetchUserRecipes(user.id);
});

export const fetchPublicShowcaseBacktestFn = createServerFn({ method: 'GET' }).handler(() =>
    fetchPublicShowcaseBacktest(),
);
