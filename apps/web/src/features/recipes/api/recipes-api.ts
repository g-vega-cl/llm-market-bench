import { createServerFn } from '@tanstack/react-start';
import { getAuthServerClient } from '~/lib/auth';
import { getDbAdminClient, getDbServerClient } from '~/lib/db';
import { buildNewsExcerpt } from '../news-excerpt';
import type { PushStrategy, RecipeAlert, StrategyRecipeRecord, StrategyStage } from '../types';

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

        if (error) throw new Error(error.message);
        return { success: true };
    });

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

export async function getRecipeJobStatus(jobId: string, userId: string) {
    // recipe_execution_queue is service-role only, so this read needs the admin
    // client. It is scoped to the requesting user's rows.
    const db = getDbServerClient({ useServiceRole: true });
    const { data, error } = await db
        .from('recipe_execution_queue')
        .select('id, status, progress_pct, result_json, error_message')
        .eq('id', jobId)
        .eq('user_id', userId)
        .single();

    if (error) throw new Error(error.message);
    return data;
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

function matchesKeywords(haystack: string, keywords: string[]): boolean {
    const cleaned = keywords.map((k) => k.trim().toLowerCase()).filter(Boolean);
    if (cleaned.length === 0) return true;
    const lower = haystack.toLowerCase();
    return cleaned.some((kw) => lower.includes(kw));
}

function hydrateNewsBlockText(
    block: { contains: string[]; recency_hours: number },
    newsRows: Array<{ title?: string; full_text?: string; date_published?: string }>,
    now: number,
): string {
    const floorMs = now - Math.max(1, block.recency_hours) * 3600 * 1000;
    const matched = newsRows
        .filter((r) => {
            const ts = Date.parse(String(r.date_published || ''));
            return (
                !Number.isNaN(ts) &&
                ts >= floorMs &&
                ts <= now &&
                matchesKeywords(`${r.title || ''} ${r.full_text || ''}`, block.contains)
            );
        })
        .slice(0, 15);
    const kw = block.contains.length > 0 ? block.contains.join(', ') : 'ALL';
    const header = `[News (contains: ${kw} | recency: ${block.recency_hours}h)]:`;
    if (matched.length === 0) return `${header}\n- (No matching news in window)`;
    return [
        header,
        ...matched.map((n) => {
            const line = `- [${String(n.date_published).slice(0, 16)}] ${n.title}`;
            const excerpt = buildNewsExcerpt(n.full_text, block.contains);
            return excerpt ? `${line}\n  ${excerpt}` : line;
        }),
    ].join('\n');
}

function hydrateMemoriesBlockText(
    block: { contains: string[]; recency_hours: number; category: string; min_importance: number },
    memoryRows: Array<{
        content?: string;
        created_at?: string;
        memory_type?: string;
        importance_score?: number;
    }>,
    now: number,
): string {
    const floorMs = now - Math.max(1, block.recency_hours) * 3600 * 1000;
    const catNorm = (block.category || 'ALL').toUpperCase();
    const matched = memoryRows
        .filter((m) => {
            const ts = Date.parse(String(m.created_at || ''));
            if (Number.isNaN(ts) || ts < floorMs || ts > now) return false;
            if (Number(m.importance_score ?? 5) < block.min_importance) return false;
            const mt = String(m.memory_type || 'MARKET_EVENT').toUpperCase();
            return (
                (catNorm === 'ALL' || mt === catNorm) &&
                matchesKeywords(String(m.content || ''), block.contains)
            );
        })
        .slice(0, 15);
    const kw = block.contains.length > 0 ? block.contains.join(', ') : 'ALL';
    const header = `[Memories (contains: ${kw} | recency: ${block.recency_hours}h | category: ${block.category} | min_importance: ${block.min_importance})]:`;
    if (matched.length === 0) return `${header}\n- (No matching memories in window)`;
    return [
        header,
        ...matched.map(
            (m) => `- [${m.memory_type || 'EVENT'} | imp=${m.importance_score ?? 5}] ${m.content}`,
        ),
    ].join('\n');
}

export const previewStrategyPromptFn = createServerFn({ method: 'POST' })
    .validator((d: { strategy: PushStrategy }) => d)
    .handler(async ({ data: { strategy } }): Promise<Record<string, string>> => {
        const db = getDbServerClient();
        const now = Date.now();
        const hydrated: Record<string, string> = {};

        // Only pull the corpora the strategy actually references.
        const needsNews = strategy.stages.some((stage) =>
            stage.blocks.some((block) => block.type === 'news'),
        );
        const needsMemories = strategy.stages.some((stage) =>
            stage.blocks.some((block) => block.type === 'memories'),
        );

        let newsRows: Array<{ title?: string; full_text?: string; date_published?: string }> = [];
        if (needsNews) {
            const { data } = await db
                .from('recipe_news_corpus')
                .select('article_id, title, full_text, date_published, tickers')
                .order('date_published', { ascending: false })
                .limit(500);
            newsRows = data ?? [];
        }

        let memoryRows: Array<{
            content?: string;
            created_at?: string;
            memory_type?: string;
            importance_score?: number;
        }> = [];
        if (needsMemories) {
            const { data } = await db
                .from('memories')
                .select('id, content, created_at, memory_type, importance_score')
                .order('created_at', { ascending: false })
                .limit(500);
            memoryRows = data ?? [];
        }

        for (const stage of strategy.stages) {
            for (const block of stage.blocks) {
                if (block.type === 'news') {
                    hydrated[block.id] = hydrateNewsBlockText(block, newsRows, now);
                } else if (block.type === 'memories') {
                    hydrated[block.id] = hydrateMemoriesBlockText(block, memoryRows, now);
                }
            }
        }

        return hydrated;
    });
