import { beforeEach, describe, expect, it, vi } from 'vitest';
import { STARTER_RECIPES } from '../starter-templates';
import {
    assertQuotaAllowsJob,
    cancelRecipeJob,
    fetchPublicShowcaseBacktest,
    fetchRecipeQuotaStatus,
    fetchUserRecipes,
    hasPublishedShowcase,
    toggleLiveSchedule,
} from './recipes-quota-api';

let mockAdminDb: unknown;
vi.mock('~/lib/db', () => ({
    getDbAdminClient: () => mockAdminDb,
}));

interface QueueRow {
    id: string;
    user_id: string;
    recipe_id?: string;
    mode: 'backtest' | 'live_turn';
    status: string;
    created_at: string;
    result_json?: Record<string, unknown> | null;
}

type MaybeSingleSources = {
    quotaRow: Record<string, unknown> | null;
    showcasePin: Record<string, unknown> | null;
    jobsById: Record<string, Record<string, unknown>>;
    recipesById: Record<string, Record<string, unknown>>;
};

function resolveMaybeSingle(
    table: string,
    filters: Record<string, unknown>,
    sources: MaybeSingleSources,
): Record<string, unknown> | null {
    if (table === 'recipe_user_quotas') return sources.quotaRow;
    if (table === 'recipe_showcase') return sources.showcasePin;
    const id = typeof filters.id === 'string' ? filters.id : null;
    if (!id) return null;
    if (table === 'recipe_execution_queue') return sources.jobsById[id] ?? null;
    if (table === 'strategy_recipes') return sources.recipesById[id] ?? null;
    return null;
}

function filterMockRows(rows: Array<Record<string, unknown>>, filters: Record<string, unknown>) {
    // `archived_at IS NULL` is applied first so the remaining predicate keeps
    // its original complexity budget.
    const visible =
        filters['is:archived_at'] === null ? rows.filter((row) => !row.archived_at) : rows;
    return visible.filter((row) => {
        if (filters.user_id && row.user_id !== filters.user_id) return false;
        if (filters.mode && row.mode !== filters.mode) return false;
        if (Array.isArray(filters.status) && !filters.status.includes(row.status)) return false;
        if (filters['neq:status'] && row.status === filters['neq:status']) return false;
        if (typeof filters.is_live === 'boolean' && row.is_live !== filters.is_live) return false;
        return true;
    });
}

function createQuotaMockDb({
    quotaRow = null as Record<string, unknown> | null,
    queueRows = [] as QueueRow[],
    recipeRows = [] as Array<Record<string, unknown>>,
    singleRecipe = null as Record<string, unknown> | null,
    updateResult = { data: { id: 'job-1', status: 'cancelled' }, error: null },
    showcasePin = null as Record<string, unknown> | null,
    showcasePinError = null as { message: string } | null,
    jobsById = {} as Record<string, Record<string, unknown>>,
    recipesById = {} as Record<string, Record<string, unknown>>,
} = {}) {
    const calls: Array<{ table: string; op: string; payload?: unknown }> = [];

    const db = {
        from(table: string) {
            const state = {
                table,
                op: 'select',
                filters: {} as Record<string, unknown>,
                payload: undefined as unknown,
            };
            const chain = {
                select: () => chain,
                update: (payload: unknown) => {
                    state.op = 'update';
                    state.payload = payload;
                    return chain;
                },
                eq: (col: string, val: unknown) => {
                    state.filters[col] = val;
                    return chain;
                },
                neq: (col: string, val: unknown) => {
                    state.filters[`neq:${col}`] = val;
                    return chain;
                },
                is: (col: string, val: unknown) => {
                    state.filters[`is:${col}`] = val;
                    return chain;
                },
                in: (col: string, vals: unknown[]) => {
                    state.filters[col] = vals;
                    return chain;
                },
                gte: (col: string, val: unknown) => {
                    state.filters[`gte:${col}`] = val;
                    return chain;
                },
                order: () => chain,
                limit: () => {
                    calls.push({ table, op: state.op, payload: state.payload });
                    if (table === 'recipe_execution_queue') {
                        return Promise.resolve({
                            data: filterMockRows(
                                queueRows as unknown as Array<Record<string, unknown>>,
                                state.filters,
                            ),
                            error: null,
                        });
                    }
                    if (table === 'strategy_recipes') {
                        return Promise.resolve({
                            data: filterMockRows(recipeRows, state.filters),
                            error: null,
                        });
                    }
                    return Promise.resolve({ data: [], error: null });
                },
                maybeSingle: () => {
                    calls.push({ table, op: state.op, payload: state.payload });
                    if (table === 'recipe_showcase' && showcasePinError) {
                        return Promise.resolve({ data: null, error: showcasePinError });
                    }
                    return Promise.resolve({
                        data: resolveMaybeSingle(table, state.filters, {
                            quotaRow,
                            showcasePin,
                            jobsById,
                            recipesById,
                        }),
                        error: null,
                    });
                },
                single: () => {
                    calls.push({ table, op: state.op, payload: state.payload });
                    if (state.op === 'update') {
                        return Promise.resolve(updateResult);
                    }
                    if (table === 'strategy_recipes') {
                        return Promise.resolve({ data: singleRecipe, error: null });
                    }
                    return Promise.resolve({ data: null, error: null });
                },
            };
            return chain;
        },
    };

    return { db, calls };
}

beforeEach(() => {
    vi.clearAllMocks();
});

describe('recipes-quota-api', () => {
    it('computes default beta starter limits and current usage counts', async () => {
        const nowIso = new Date().toISOString();
        const { db } = createQuotaMockDb({
            queueRows: [
                {
                    id: 'q1',
                    user_id: 'user-1',
                    mode: 'backtest',
                    status: 'completed',
                    created_at: nowIso,
                },
                {
                    id: 'q2',
                    user_id: 'user-1',
                    mode: 'live_turn',
                    status: 'completed',
                    created_at: nowIso,
                },
                {
                    id: 'q3',
                    user_id: 'other-user',
                    mode: 'backtest',
                    status: 'processing',
                    created_at: nowIso,
                },
            ],
            recipeRows: [{ id: 'rec-live', user_id: 'user-1', is_live: true }],
        });
        mockAdminDb = db;

        const status = await fetchRecipeQuotaStatus('user-1');
        expect(status).toEqual({
            tier: 'beta_starter',
            activeBacktests: 0,
            maxConcurrentBacktests: 1,
            backtestsLast24h: 1,
            dailyBacktestLimit: 2,
            liveTurnsLast24h: 1,
            dailyLiveTurnLimit: Number.POSITIVE_INFINITY,
            activeLiveRecipes: 1,
            maxLiveRecipes: 3,
            globalPendingBacktests: 1,
            globalQueueCap: 20,
        });
    });

    it('blocks queueing when daily backtest or live turn cap is reached or global queue is full', async () => {
        const nowIso = new Date().toISOString();
        mockAdminDb = createQuotaMockDb({
            queueRows: [
                {
                    id: 'q1',
                    user_id: 'user-1',
                    mode: 'backtest',
                    status: 'completed',
                    created_at: nowIso,
                },
                {
                    id: 'q2',
                    user_id: 'user-1',
                    mode: 'backtest',
                    status: 'completed',
                    created_at: nowIso,
                },
            ],
        }).db;

        await expect(assertQuotaAllowsJob('user-1', 'backtest')).rejects.toThrow(
            'Daily backtest limit reached (2/2 in 24h)',
        );

        const fullGlobalRows: QueueRow[] = Array.from({ length: 20 }, (_, idx) => ({
            id: `g-${idx}`,
            user_id: `other-${idx}`,
            mode: 'backtest',
            status: idx === 0 ? 'processing' : 'pending',
            created_at: nowIso,
        }));
        mockAdminDb = createQuotaMockDb({ queueRows: fullGlobalRows }).db;
        await expect(assertQuotaAllowsJob('user-1', 'backtest')).rejects.toThrow(
            'Backtest queue is currently full (20/20)',
        );
    });

    it('allows a second live bot but enforces the three-bot cap', async () => {
        mockAdminDb = createQuotaMockDb({
            singleRecipe: {
                id: 'rec-2',
                user_id: 'user-1',
                is_live: false,
                graph_json: STARTER_RECIPES[0],
            },
            recipeRows: [{ id: 'rec-1', user_id: 'user-1', is_live: true }],
        }).db;

        await expect(toggleLiveSchedule('rec-2', true, 'user-1')).resolves.toBeDefined();

        mockAdminDb = createQuotaMockDb({
            singleRecipe: {
                id: 'rec-4',
                user_id: 'user-1',
                is_live: false,
                graph_json: STARTER_RECIPES[0],
            },
            recipeRows: [
                { id: 'rec-1', user_id: 'user-1', is_live: true },
                { id: 'rec-2', user_id: 'user-1', is_live: true },
                { id: 'rec-3', user_id: 'user-1', is_live: true },
            ],
        }).db;

        await expect(toggleLiveSchedule('rec-4', true, 'user-1')).rejects.toThrow(
            'Scheduled live limit reached (3/3)',
        );
    });

    it('refuses to schedule a strategy the owner removed from My Strategies', async () => {
        mockAdminDb = createQuotaMockDb({
            singleRecipe: {
                id: 'rec-archived',
                user_id: 'user-1',
                is_live: false,
                archived_at: '2026-11-17T14:00:00.000Z',
                graph_json: STARTER_RECIPES[0],
            },
            recipeRows: [],
        }).db;

        await expect(toggleLiveSchedule('rec-archived', true, 'user-1')).rejects.toThrow(
            'removed from My Strategies',
        );
    });

    it('cancels an owned pending or processing job and records cancelled_at', async () => {
        const { db, calls } = createQuotaMockDb({
            updateResult: { data: { id: 'job-1', status: 'cancelled' }, error: null },
        });
        mockAdminDb = db;

        const res = await cancelRecipeJob('job-1', 'user-1');
        expect(res).toEqual({ id: 'job-1', status: 'cancelled' });
        const updateCall = calls.find((c) => c.op === 'update');
        expect(updateCall?.payload).toMatchObject({ status: 'cancelled' });
    });

    it('hides archived strategies from My Strategies without removing the row', async () => {
        const rows = [
            {
                id: 'rec-visible',
                user_id: 'user-1',
                name: 'Visible Strategy',
                cadence: '3h',
                is_live: false,
                trial_count: 2,
                updated_at: '2026-11-17T12:00:00.000Z',
            },
            {
                id: 'rec-hidden',
                user_id: 'user-1',
                name: 'Removed Strategy',
                cadence: '3h',
                is_live: false,
                trial_count: 5,
                updated_at: '2026-11-17T13:00:00.000Z',
                archived_at: '2026-11-17T14:00:00.000Z',
            },
        ];
        mockAdminDb = createQuotaMockDb({ recipeRows: rows }).db;

        const list = await fetchUserRecipes('user-1');

        expect(list.map((r) => r.id)).toEqual(['rec-visible']);
        // The archived row still exists in the table: hiding is not deletion.
        expect(rows).toHaveLength(2);
    });
});

describe('fetchPublicShowcaseBacktest', () => {
    const completedBacktest = {
        id: 'job-pinned',
        recipe_id: 'rec-pinned',
        mode: 'backtest',
        status: 'completed',
        result_json: { total_return_pct_net: 5.43, day_steps: [] },
        completed_at: '2026-11-17T01:34:37.000Z',
    };

    it('returns the pinned job even when a newer public run exists', async () => {
        mockAdminDb = createQuotaMockDb({
            showcasePin: {
                job_id: 'job-pinned',
                recipe_id: 'rec-pinned',
                headline: 'News momentum, long-only',
            },
            jobsById: { 'job-pinned': completedBacktest },
            recipesById: {
                'rec-pinned': { id: 'rec-pinned', name: 'Private copy', cadence: '3h' },
            },
            recipeRows: [{ id: 'rec-public', name: 'Public recipe', cadence: '3h' }],
            queueRows: [
                {
                    id: 'job-newer',
                    user_id: 'user-1',
                    recipe_id: 'rec-public',
                    mode: 'backtest',
                    status: 'completed',
                    created_at: '2026-11-17T09:00:00.000Z',
                },
            ],
        }).db;

        const showcase = await fetchPublicShowcaseBacktest();

        expect(showcase?.job.id).toBe('job-pinned');
        expect(showcase?.recipeName).toBe('News momentum, long-only');
        expect(showcase?.recipeCadence).toBe('3h');
    });

    it('falls back to the newest public run when the pin is stale', async () => {
        mockAdminDb = createQuotaMockDb({
            showcasePin: { job_id: 'job-dead', recipe_id: 'rec-pinned', headline: '' },
            jobsById: {
                'job-dead': { ...completedBacktest, id: 'job-dead', status: 'pending' },
            },
            recipesById: {
                'rec-pinned': { id: 'rec-pinned', name: 'Private copy', cadence: '3h' },
            },
            recipeRows: [{ id: 'rec-public', name: 'Public recipe', cadence: '3h' }],
            queueRows: [
                {
                    id: 'job-newer',
                    user_id: 'user-1',
                    recipe_id: 'rec-public',
                    mode: 'backtest',
                    status: 'completed',
                    created_at: '2026-11-17T09:00:00.000Z',
                    result_json: { total_return_pct_net: 2.01 },
                },
            ],
        }).db;

        const showcase = await fetchPublicShowcaseBacktest();

        expect(showcase?.job.id).toBe('job-newer');
        expect(showcase?.recipeName).toBe('Public recipe');
    });

    it('still serves the pinned run when its recipe name is unreadable', async () => {
        mockAdminDb = createQuotaMockDb({
            showcasePin: { job_id: 'job-pinned', recipe_id: 'rec-pinned', headline: '' },
            jobsById: { 'job-pinned': completedBacktest },
        }).db;

        const showcase = await fetchPublicShowcaseBacktest();

        expect(showcase?.job.id).toBe('job-pinned');
        expect(showcase?.recipeName).toBe('Public Showcase Backtest');
    });

    it('prefers the pinned recipe name over a since-edited live name', async () => {
        mockAdminDb = createQuotaMockDb({
            showcasePin: {
                job_id: 'job-pinned',
                recipe_id: 'rec-pinned',
                headline: '',
                recipe_name: 'Frozen showcase title',
            },
            jobsById: { 'job-pinned': completedBacktest },
            recipesById: {
                'rec-pinned': { id: 'rec-pinned', name: 'Renamed later', cadence: '3h' },
            },
        }).db;

        const showcase = await fetchPublicShowcaseBacktest();

        expect(showcase?.recipeName).toBe('Frozen showcase title');
    });

    it('falls back to the public heuristic and logs when the pin read fails', async () => {
        const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
        mockAdminDb = createQuotaMockDb({
            showcasePinError: { message: 'PGRST205 recipe_showcase missing from schema cache' },
            recipeRows: [{ id: 'rec-public', name: 'Public recipe', cadence: '3h' }],
            queueRows: [
                {
                    id: 'job-newer',
                    user_id: 'user-1',
                    recipe_id: 'rec-public',
                    mode: 'backtest',
                    status: 'completed',
                    created_at: '2026-11-17T09:00:00.000Z',
                    result_json: { total_return_pct_net: 2.01 },
                },
            ],
        }).db;

        const showcase = await fetchPublicShowcaseBacktest();

        expect(showcase?.job.id).toBe('job-newer');
        expect(errorSpy).toHaveBeenCalledWith(
            expect.stringContaining('pin'),
            expect.objectContaining({ message: expect.stringContaining('PGRST205') }),
        );
        errorSpy.mockRestore();
    });
});

describe('hasPublishedShowcase', () => {
    it('reports true only while a job is pinned', async () => {
        mockAdminDb = createQuotaMockDb({
            showcasePin: { job_id: 'job-1', recipe_id: 'rec-1', headline: '', recipe_name: '' },
        }).db;
        await expect(hasPublishedShowcase()).resolves.toBe(true);

        mockAdminDb = createQuotaMockDb({
            showcasePin: { job_id: null, recipe_id: 'rec-1', headline: '', recipe_name: '' },
        }).db;
        await expect(hasPublishedShowcase()).resolves.toBe(false);
    });

    it('fails closed and logs when the pin read errors', async () => {
        const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
        mockAdminDb = createQuotaMockDb({
            showcasePinError: { message: 'PGRST205 recipe_showcase missing from schema cache' },
        }).db;

        await expect(hasPublishedShowcase()).resolves.toBe(false);

        expect(errorSpy).toHaveBeenCalled();
        errorSpy.mockRestore();
    });
});
