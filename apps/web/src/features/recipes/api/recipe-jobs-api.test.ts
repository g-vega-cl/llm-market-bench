import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
    fetchRecentBacktestJobs,
    fetchRecipeRunDetail,
    getRecipeJobStatus,
} from './recipe-jobs-api';

let mockAdminDb: unknown;
let mockServerDb: unknown;
const mockGetDbServerClient = vi.fn();
vi.mock('~/lib/db', () => ({
    getDbAdminClient: () => mockAdminDb,
    getDbServerClient: (options?: { useServiceRole?: boolean }) => {
        mockGetDbServerClient(options);
        return mockServerDb;
    },
}));

interface RecordedCall {
    op: 'select' | 'insert' | 'update';
    table: string;
    payload?: unknown;
    filters: Record<string, unknown>;
}

type DbResult = { data?: unknown; error?: { message: string } | null };

function createMockDb(results: Record<string, DbResult | ((call: RecordedCall) => DbResult)>) {
    const calls: RecordedCall[] = [];

    const resolve = (call: RecordedCall): DbResult => {
        const entry = results[`${call.op}:${call.table}`] ?? results[call.table];
        if (typeof entry === 'function') return entry(call);
        return entry ?? { data: null, error: null };
    };

    const db = {
        from(table: string) {
            const call: RecordedCall = { op: 'select', table, filters: {} };
            const chain = {
                select(_cols?: string) {
                    return chain;
                },
                insert(payload: unknown) {
                    call.op = 'insert';
                    call.payload = payload;
                    return chain;
                },
                update(payload: unknown) {
                    call.op = 'update';
                    call.payload = payload;
                    return chain;
                },
                eq(col: string, value: unknown) {
                    call.filters[col] = value;
                    return chain;
                },
                in(col: string, values: unknown[]) {
                    call.filters[col] = values;
                    return chain;
                },
                gte(_col: string, _value: unknown) {
                    return chain;
                },
                neq(_col: string, _value: unknown) {
                    return chain;
                },
                order(_col: string, _opts?: unknown) {
                    return chain;
                },
                limit(_n: number) {
                    return chain;
                },
                maybeSingle() {
                    calls.push(call);
                    return Promise.resolve(resolve(call));
                },
                single() {
                    calls.push(call);
                    return Promise.resolve(resolve(call));
                },
                // biome-ignore lint/suspicious/noThenProperty: the mock mimics the thenable supabase-js query builder
                then(
                    onFulfilled?: (value: unknown) => unknown,
                    onRejected?: (reason: unknown) => unknown,
                ) {
                    calls.push(call);
                    return Promise.resolve(resolve(call)).then(onFulfilled, onRejected);
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

describe('getRecipeJobStatus', () => {
    it('reads the queue with the service-role client, scoped to the caller', async () => {
        const { db, calls } = createMockDb({
            'select:recipe_execution_queue': { data: { id: 'job-1', status: 'completed' } },
        });
        mockServerDb = db;

        const result = await getRecipeJobStatus('job-1', 'user-1');

        expect(mockGetDbServerClient).toHaveBeenCalledWith({ useServiceRole: true });
        expect(calls[0]?.filters).toMatchObject({ id: 'job-1', user_id: 'user-1' });
        expect(result).toMatchObject({ status: 'completed' });
    });
});

describe('fetchRecipeRunDetail', () => {
    it('loads the user-scoped job and attaches recipe metadata', async () => {
        const { db, calls } = createMockDb({
            'select:recipe_execution_queue': {
                data: {
                    id: 'job-99',
                    recipe_id: 'rec-1',
                    mode: 'backtest',
                    status: 'processing',
                    progress_pct: 36,
                    result_json: { days_completed: 3, total_days: 10 },
                    error_message: null,
                },
            },
            'select:strategy_recipes': {
                data: { id: 'rec-1', name: 'Chip Tariff Momentum', cadence: '1d' },
            },
        });
        mockServerDb = db;

        const detail = await fetchRecipeRunDetail('job-99', 'user-1');

        expect(calls[0]?.filters).toMatchObject({ id: 'job-99', user_id: 'user-1' });
        expect(detail.job.status).toBe('processing');
        expect(detail.job.progress_pct).toBe(36);
        expect(detail.recipeName).toBe('Chip Tariff Momentum');
        expect(detail.recipeCadence).toBe('1d');
    });
});

describe('fetchRecentBacktestJobs', () => {
    it('queries backtest runs scoped to the requesting user', async () => {
        const { db, calls } = createMockDb({
            'select:recipe_execution_queue': {
                data: [
                    {
                        id: 'job-1',
                        recipe_id: 'rec-1',
                        mode: 'backtest',
                        status: 'completed',
                        progress_pct: 100,
                    },
                ],
            },
        });
        mockServerDb = db;

        const jobs = await fetchRecentBacktestJobs('user-1', 5);
        expect(calls[0]?.filters).toMatchObject({ user_id: 'user-1', mode: 'backtest' });
        expect(jobs).toHaveLength(1);
        expect(jobs[0]?.id).toBe('job-1');
    });

    it('computes queue position for pending backtest runs in fetchRecipeRunDetail', async () => {
        const { db } = createMockDb({
            'select:recipe_execution_queue': (call) => {
                if (call.filters.id === 'job-wait') {
                    return {
                        data: {
                            id: 'job-wait',
                            recipe_id: 'rec-1',
                            mode: 'backtest',
                            status: 'pending',
                            progress_pct: 0,
                            created_at: '2026-11-16T10:05:00+00:00',
                            result_json: null,
                            error_message: null,
                        },
                    };
                }
                return {
                    data: [
                        {
                            id: 'job-active',
                            status: 'processing',
                            created_at: '2026-11-16T10:00:00+00:00',
                        },
                        {
                            id: 'job-wait',
                            status: 'pending',
                            created_at: '2026-11-16T10:05:00+00:00',
                        },
                    ],
                };
            },
            'select:strategy_recipes': {
                data: { id: 'rec-1', name: 'Chip Momentum', cadence: '3h' },
            },
        });
        mockServerDb = db;

        const detail = await fetchRecipeRunDetail('job-wait', 'user-1');
        expect(detail.queuePosition).toBe(2);
        expect(detail.globalActiveBacktests).toBe(1);
    });
});
