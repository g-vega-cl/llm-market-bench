import { createServerFn } from '@tanstack/react-start';
import { getAuthServerClient } from '~/lib/auth';
import { getDbAdminClient } from '~/lib/db';
import type {
    RecipeJobRecord,
    RecipeRunDetail,
    RecipeSummaryItem,
    RecipeUserQuotaStatus,
} from '../types';
import { assertNoPrevOutputPlaceholder, assertSingleLlmStage } from './recipes-validators';

export const BETA_STARTER_LIMITS = {
    tier: 'beta_starter',
    maxConcurrentBacktests: 1,
    dailyBacktestLimit: 2,
    dailyLiveTurnLimit: 3,
    maxLiveRecipes: 1,
    globalQueueCap: 20,
} as const;

interface QuotaOverrideRow {
    tier?: string;
    max_concurrent_backtests?: number;
    daily_backtest_limit?: number;
    daily_live_turn_limit?: number;
    max_live_recipes?: number;
}

interface QueueQuotaRow {
    id: string;
    user_id: string;
    mode: 'backtest' | 'live_turn';
    status: string;
    created_at: string;
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
                'tier, max_concurrent_backtests, daily_backtest_limit, daily_live_turn_limit, max_live_recipes',
            )
            .eq('user_id', userId)
            .maybeSingle(),
        db
            .from('recipe_execution_queue')
            .select('id, user_id, mode, status, created_at')
            .eq('user_id', userId)
            .gte('created_at', since24hIso)
            .neq('status', 'cancelled')
            .limit(200),
        db
            .from('recipe_execution_queue')
            .select('id, user_id, mode, status, created_at')
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
    const backtestsLast24h = recent.filter((row) => row.mode === 'backtest').length;
    const liveTurnsLast24h = recent.filter((row) => row.mode === 'live_turn').length;

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
    };
}

export async function assertQuotaAllowsJob(
    userId: string,
    mode: 'live_turn' | 'backtest',
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
    } else if (quota.liveTurnsLast24h >= quota.dailyLiveTurnLimit) {
        throw new Error(
            `Daily live turn limit reached (${quota.liveTurnsLast24h}/${quota.dailyLiveTurnLimit} in 24h). Starter tier matches 1 active 3x/day ET strategy.`,
        );
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
        .select('id, user_id, is_live, graph_json')
        .eq('id', recipeId)
        .single();

    if (fetchErr || !existing) {
        throw new Error(`Recipe not found: ${recipeId}`);
    }
    const row = existing as {
        id: string;
        user_id: string;
        is_live: boolean;
        graph_json: Parameters<typeof assertSingleLlmStage>[0] &
            Parameters<typeof assertNoPrevOutputPlaceholder>[0];
    };
    if (row.user_id !== userId) {
        throw new Error('Unauthorized: cannot modify live schedule for another user');
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

    const { data: updated, error: updErr } = await db
        .from('strategy_recipes')
        .update({ is_live: isLive, updated_at: new Date().toISOString() })
        .eq('id', recipeId)
        .eq('user_id', userId)
        .select('id, is_live')
        .single();

    if (updErr || !updated) {
        throw new Error(updErr?.message || 'Failed updating live schedule');
    }
    return updated as { id: string; is_live: boolean };
}

export async function fetchUserRecipes(userId: string): Promise<RecipeSummaryItem[]> {
    const db = getDbAdminClient();
    const { data, error } = await db
        .from('strategy_recipes')
        .select('id, name, cadence, is_live, trial_count, updated_at')
        .eq('user_id', userId)
        .order('updated_at', { ascending: false })
        .limit(20);

    if (error) throw new Error(error.message);
    return (data || []) as RecipeSummaryItem[];
}

export async function fetchPublicShowcaseBacktest(): Promise<RecipeRunDetail | null> {
    const db = getDbAdminClient();
    const { data: pubRecipes } = await db
        .from('strategy_recipes')
        .select('id, name, cadence')
        .eq('is_public', true)
        .order('trial_count', { ascending: false })
        .limit(10);

    const recipes = (pubRecipes || []) as Array<{
        id: string;
        name: string;
        cadence: RecipeRunDetail['recipeCadence'];
    }>;
    if (recipes.length === 0) return null;

    const recipeMap = new Map(recipes.map((r) => [r.id, r]));
    const { data: jobs } = await db
        .from('recipe_execution_queue')
        .select(
            'id, recipe_id, mode, status, progress_pct, provider, model, result_json, error_message, created_at, started_at, completed_at',
        )
        .in(
            'recipe_id',
            recipes.map((r) => r.id),
        )
        .eq('mode', 'backtest')
        .eq('status', 'completed')
        .order('completed_at', { ascending: false })
        .limit(5);

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
