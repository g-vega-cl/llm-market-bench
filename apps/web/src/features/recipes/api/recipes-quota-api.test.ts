import { beforeEach, describe, expect, it, vi } from 'vitest';
import { STARTER_RECIPES } from '../starter-templates';
import {
    assertQuotaAllowsJob,
    cancelRecipeJob,
    fetchRecipeQuotaStatus,
    toggleLiveSchedule,
} from './recipes-quota-api';

let mockAdminDb: unknown;
vi.mock('~/lib/db', () => ({
    getDbAdminClient: () => mockAdminDb,
}));

interface QueueRow {
    id: string;
    user_id: string;
    mode: 'backtest' | 'live_turn';
    status: string;
    created_at: string;
}

function filterMockRows(rows: Array<Record<string, unknown>>, filters: Record<string, unknown>) {
    return rows.filter((row) => {
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
                    if (table === 'recipe_user_quotas') {
                        return Promise.resolve({ data: quotaRow, error: null });
                    }
                    return Promise.resolve({ data: null, error: null });
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
            dailyLiveTurnLimit: 3,
            activeLiveRecipes: 1,
            maxLiveRecipes: 1,
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

        mockAdminDb = createQuotaMockDb({
            queueRows: [
                {
                    id: 'l1',
                    user_id: 'user-1',
                    mode: 'live_turn',
                    status: 'completed',
                    created_at: nowIso,
                },
                {
                    id: 'l2',
                    user_id: 'user-1',
                    mode: 'live_turn',
                    status: 'completed',
                    created_at: nowIso,
                },
                {
                    id: 'l3',
                    user_id: 'user-1',
                    mode: 'live_turn',
                    status: 'completed',
                    created_at: nowIso,
                },
            ],
        }).db;
        await expect(assertQuotaAllowsJob('user-1', 'live_turn')).rejects.toThrow(
            'Daily live turn limit reached (3/3 in 24h)',
        );
    });

    it('enforces max 1 scheduled live recipe when toggling is_live on', async () => {
        mockAdminDb = createQuotaMockDb({
            singleRecipe: {
                id: 'rec-2',
                user_id: 'user-1',
                is_live: false,
                graph_json: STARTER_RECIPES[0],
            },
            recipeRows: [{ id: 'rec-1', user_id: 'user-1', is_live: true }],
        }).db;

        await expect(toggleLiveSchedule('rec-2', true, 'user-1')).rejects.toThrow(
            'Scheduled live limit reached (1/1)',
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
});
