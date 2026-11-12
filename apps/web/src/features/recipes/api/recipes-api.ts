import { createServerFn } from '@tanstack/react-start';
import { getAuthServerClient } from '~/lib/auth';
import { getDbAdminClient, getDbServerClient } from '~/lib/db';
import type { RecipeAlert, RecipeGraph, StrategyRecipeRecord } from '../types';

const ANONYMOUS_USER_ID = '00000000-0000-0000-0000-000000000000';

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

export const fetchRecipeAlertsFn = createServerFn({ method: 'GET' }).handler(
    async (): Promise<RecipeAlert[]> => {
        const auth = getAuthServerClient();
        const {
            data: { user },
        } = await auth.auth.getUser();

        const userId = user?.id || ANONYMOUS_USER_ID;
        const db = getDbAdminClient();

        const { data, error } = await db
            .from('recipe_alerts_inbox')
            .select('*')
            .eq('user_id', userId)
            .order('created_at', { ascending: false })
            .limit(50);

        if (error) {
            throw new Error(error.message);
        }
        return (data || []) as RecipeAlert[];
    },
);

export const markAlertReadFn = createServerFn({ method: 'POST' })
    .validator((d: { alertId: string }) => d)
    .handler(async ({ data: { alertId } }) => {
        const auth = getAuthServerClient();
        const {
            data: { user },
        } = await auth.auth.getUser();
        const userId = user?.id || ANONYMOUS_USER_ID;

        const db = getDbAdminClient();
        const { error } = await db
            .from('recipe_alerts_inbox')
            .update({ is_read: true })
            .eq('id', alertId)
            .eq('user_id', userId);

        if (error) {
            throw new Error(error.message);
        }
        return { success: true };
    });

export const saveRecipeFn = createServerFn({ method: 'POST' })
    .validator((d: { recipe: RecipeGraph; isPublic?: boolean }) => d)
    .handler(async ({ data: { recipe, isPublic = false } }) => {
        const auth = getAuthServerClient();
        const {
            data: { user },
        } = await auth.auth.getUser();

        const userId = user?.id || ANONYMOUS_USER_ID;
        const db = getDbAdminClient();

        if (!recipe.nodes || recipe.nodes.length === 0) {
            throw new Error('Invalid recipe: must contain at least one node');
        }

        const payload = {
            user_id: userId,
            name: recipe.name,
            description: recipe.description || '',
            cadence: recipe.cadence,
            graph_json: recipe,
            concurrency_config: recipe.concurrency || {
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

            if (
                existing.data &&
                existing.data.user_id !== userId &&
                existing.data.user_id !== ANONYMOUS_USER_ID
            ) {
                throw new Error('Unauthorized: cannot modify a recipe owned by another user');
            }

            const { data, error } = await db
                .from('strategy_recipes')
                .update(payload)
                .eq('id', recipe.id)
                .select('*')
                .single();

            if (error) throw new Error(error.message);
            return data as StrategyRecipeRecord;
        }

        const { data, error } = await db
            .from('strategy_recipes')
            .insert(payload)
            .select('*')
            .single();

        if (error) throw new Error(error.message);
        return data as StrategyRecipeRecord;
    });

export const enqueueRecipeJobFn = createServerFn({ method: 'POST' })
    .validator(
        (d: {
            recipeId: string;
            mode: 'preview' | 'backtest' | 'live_turn';
            weeksRequested?: string[];
            openRouterKey?: string;
            openCodeKey?: string;
        }) => d,
    )
    .handler(
        async ({
            data: { recipeId, mode, weeksRequested = ['2026-W10'], openRouterKey, openCodeKey },
        }) => {
            const auth = getAuthServerClient();
            const {
                data: { user },
            } = await auth.auth.getUser();

            const userId = user?.id || ANONYMOUS_USER_ID;
            const db = getDbAdminClient();

            let provider = 'auto-strata';
            if (openRouterKey) {
                provider = 'openrouter';
            } else if (openCodeKey) {
                provider = 'opencode_free';
            }

            const payload = {
                recipe_id: recipeId,
                user_id: userId,
                mode,
                priority: mode === 'live_turn' ? 1 : 10,
                status: 'pending',
                provider,
                model: provider === 'auto-strata' ? 'strata' : '~typesafe/jev-latest',
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
        },
    );

export const getRecipeJobStatusFn = createServerFn({ method: 'GET' })
    .validator((d: { jobId: string }) => d)
    .handler(async ({ data: { jobId } }) => {
        const db = getDbServerClient();
        const { data, error } = await db
            .from('recipe_execution_queue')
            .select('id, status, progress_pct, result_json, error_message')
            .eq('id', jobId)
            .single();

        if (error) throw new Error(error.message);
        return data;
    });

export const submitWaitlistPledgeFn = createServerFn({ method: 'POST' })
    .validator((d: { email: string; intendedTier: string; feedback?: string }) => d)
    .handler(async ({ data: { email, intendedTier, feedback = '' } }) => {
        const auth = getAuthServerClient();
        const {
            data: { user },
        } = await auth.auth.getUser();

        const userId = user?.id || ANONYMOUS_USER_ID;
        const db = getDbAdminClient();

        const { error } = await db.from('recipe_waitlist_pledges').insert({
            user_id: userId,
            email,
            intended_tier: intendedTier,
            feedback,
        });

        if (error) throw new Error(error.message);
        return { success: true };
    });
