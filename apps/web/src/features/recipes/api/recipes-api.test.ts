import { beforeEach, describe, expect, it, vi } from 'vitest';
import { STARTER_RECIPES } from '../starter-templates';
import type { PushStrategy, StrategyStage } from '../types';
import {
    assertNoPrevOutputPlaceholder,
    assertSingleLlmStage,
    enqueueRecipeJob,
    fetchRecentBacktestJobs,
    fetchRecipeById,
    fetchRecipeRunDetail,
    getRecipeJobStatus,
    saveRecipe,
} from './recipes-api';

const mockGetUser = vi.fn();
vi.mock('~/lib/auth', () => ({
    getAuthServerClient: () => ({
        auth: {
            getUser: mockGetUser,
        },
    }),
}));

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

const [stage] = STARTER_RECIPES[0].stages;

function twoStageStrategy(): PushStrategy {
    return {
        ...STARTER_RECIPES[0],
        stages: [stage, { ...stage, id: 'stage-2' }] as unknown as [StrategyStage],
    };
}

function recipeRow(overrides: Record<string, unknown> = {}) {
    return {
        id: 'rec-1',
        user_id: 'user-1',
        is_public: false,
        is_template: false,
        graph_json: STARTER_RECIPES[0],
        ...overrides,
    };
}

beforeEach(() => {
    vi.clearAllMocks();
    mockGetUser.mockResolvedValue({ data: { user: { id: 'user-1' } } });
    mockAdminDb = createMockDb({}).db;
    mockServerDb = createMockDb({}).db;
});

describe('assertSingleLlmStage', () => {
    it('accepts a strategy with exactly one LLM stage', () => {
        expect(() => assertSingleLlmStage(STARTER_RECIPES[0])).not.toThrow();
    });

    it('rejects a strategy that chains a second LLM stage', () => {
        expect(() => assertSingleLlmStage(twoStageStrategy())).toThrow('exactly one LLM stage');
    });

    it('rejects a strategy with no LLM stage', () => {
        expect(() =>
            assertSingleLlmStage({
                ...STARTER_RECIPES[0],
                stages: [] as unknown as [StrategyStage],
            }),
        ).toThrow('exactly one LLM stage');
    });
});

describe('assertNoPrevOutputPlaceholder', () => {
    it('rejects a prompt that references a previous stage output', () => {
        const strategy: PushStrategy = {
            ...STARTER_RECIPES[0],
            stages: [
                {
                    ...stage,
                    blocks: [
                        { id: 'blk-p', type: 'prompt', text: 'Given {{prev_output}}, decide.' },
                    ],
                },
            ],
        };

        expect(() => assertNoPrevOutputPlaceholder(strategy)).toThrow(
            'prev_output is not available',
        );
    });
});

describe('saveRecipe', () => {
    it('rejects a two-stage strategy and writes nothing', async () => {
        const { db, calls } = createMockDb({});
        mockAdminDb = db;

        await expect(saveRecipe(twoStageStrategy(), 'user-1')).rejects.toThrow(
            'exactly one LLM stage',
        );
        expect(calls).toHaveLength(0);
    });

    it('strips disallowed web_search tool from stage selected_tools before saving', async () => {
        const { db, calls } = createMockDb({
            'insert:strategy_recipes': { data: recipeRow() },
        });
        mockAdminDb = db;
        const dirtyStrategy: PushStrategy = {
            ...STARTER_RECIPES[0],
            stages: [
                {
                    ...stage,
                    selected_tools: ['get_stock_quote', 'web_search', 'run_stock_screener'],
                },
            ],
        };

        await saveRecipe(dirtyStrategy, 'user-1');

        const insert = calls.find((call) => call.op === 'insert');
        const graph = (insert?.payload as { graph_json: PushStrategy }).graph_json;
        expect(graph.stages[0].selected_tools).toEqual(['get_stock_quote', 'run_stock_screener']);
    });

    it('rejects a strategy that references prev_output and writes nothing', async () => {
        const { db, calls } = createMockDb({});
        mockAdminDb = db;
        const strategy: PushStrategy = {
            ...STARTER_RECIPES[0],
            stages: [
                {
                    ...stage,
                    blocks: [
                        { id: 'blk-p', type: 'prompt', text: 'Given {{prev_output}}, decide.' },
                    ],
                },
            ],
        };

        await expect(saveRecipe(strategy, 'user-1')).rejects.toThrow(
            'prev_output is not available',
        );
        expect(calls).toHaveLength(0);
    });

    it('inserts a new recipe owned by the caller', async () => {
        const { db, calls } = createMockDb({
            'insert:strategy_recipes': { data: recipeRow() },
        });
        mockAdminDb = db;

        await saveRecipe(STARTER_RECIPES[0], 'user-1');

        const insert = calls.find((call) => call.op === 'insert');
        expect(insert).toBeDefined();
        expect((insert?.payload as { user_id: string }).user_id).toBe('user-1');
        expect(
            (insert?.payload as { concurrency_config: Record<string, number> }).concurrency_config,
        ).toEqual({
            max_open_trades: 4,
            max_equity_pct_per_trade: 25.0,
        });
        expect((insert?.payload as { cadence: string }).cadence).toBe('3h');
    });

    it('refuses to update a recipe owned by another user', async () => {
        const { db, calls } = createMockDb({
            'select:strategy_recipes': { data: { user_id: 'someone-else' } },
        });
        mockAdminDb = db;

        await expect(saveRecipe({ ...STARTER_RECIPES[0], id: 'rec-1' }, 'user-1')).rejects.toThrow(
            'Unauthorized',
        );
        expect(calls.some((call) => call.op === 'update')).toBe(false);
    });

    it('fails closed when the existing row cannot be read', async () => {
        const { db, calls } = createMockDb({
            'select:strategy_recipes': { error: { message: 'not found' } },
        });
        mockAdminDb = db;

        await expect(saveRecipe({ ...STARTER_RECIPES[0], id: 'rec-1' }, 'user-1')).rejects.toThrow(
            'Recipe not found',
        );
        expect(calls.some((call) => call.op === 'update')).toBe(false);
    });

    it('updates the owner-scoped row without transferring ownership', async () => {
        const { db, calls } = createMockDb({
            'select:strategy_recipes': { data: { user_id: 'user-1' } },
            'update:strategy_recipes': { data: recipeRow() },
        });
        mockAdminDb = db;

        await saveRecipe({ ...STARTER_RECIPES[0], id: 'rec-1' }, 'user-1');

        const update = calls.find((call) => call.op === 'update');
        expect(update).toBeDefined();
        expect(update?.payload).not.toHaveProperty('user_id');
        expect(update?.payload).not.toHaveProperty('concurrency_config');
        expect(update?.filters).toMatchObject({ id: 'rec-1', user_id: 'user-1' });
    });
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

describe('enqueueRecipeJob', () => {
    it('rejects a recipe the caller neither owns nor may see', async () => {
        const { db, calls } = createMockDb({
            'select:strategy_recipes': { data: recipeRow({ user_id: 'someone-else' }) },
        });
        mockAdminDb = db;

        await expect(enqueueRecipeJob('rec-1', 'backtest', 'user-1')).rejects.toThrow(
            'Unauthorized',
        );
        expect(calls.some((call) => call.op === 'insert')).toBe(false);
    });

    it('rejects a legacy multi-stage recipe instead of queueing it', async () => {
        const { db, calls } = createMockDb({
            'select:strategy_recipes': { data: recipeRow({ graph_json: twoStageStrategy() }) },
        });
        mockAdminDb = db;

        await expect(enqueueRecipeJob('rec-1', 'backtest', 'user-1')).rejects.toThrow(
            'exactly one LLM stage',
        );
        expect(calls.some((call) => call.op === 'insert')).toBe(false);
    });

    it('queues backtests on strata-auto-go and live turns on auto-go via free-llm-proxy', async () => {
        const { db, calls } = createMockDb({
            'select:strategy_recipes': (call) =>
                call.filters.is_live === true ? { data: [] } : { data: recipeRow() },
            'select:recipe_execution_queue': { data: [] },
            'insert:recipe_execution_queue': { data: { id: 'job-1' } },
        });
        mockAdminDb = db;

        await enqueueRecipeJob('rec-1', 'backtest', 'user-1');
        await enqueueRecipeJob('rec-1', 'live_turn', 'user-1');

        const inserts = calls.filter((call) => call.op === 'insert');
        expect(inserts[0]?.payload).toMatchObject({
            recipe_id: 'rec-1',
            user_id: 'user-1',
            mode: 'backtest',
            priority: 10,
            provider: 'free-llm-proxy',
            model: 'strata-auto-go',
        });
        expect(inserts[1]?.payload).toMatchObject({
            mode: 'live_turn',
            priority: 1,
            provider: 'free-llm-proxy',
            model: 'auto-go',
        });
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

describe('fetchRecipeById', () => {
    it('preserves recipe id when owned by the caller', async () => {
        const { db } = createMockDb({
            'select:strategy_recipes': {
                data: {
                    ...recipeRow({ id: 'rec-own', user_id: 'user-1' }),
                    name: 'My Strategy',
                    description: 'Test',
                    cadence: '1d',
                },
            },
        });
        mockServerDb = db;

        const loaded = await fetchRecipeById('rec-own', 'user-1');
        expect(loaded?.id).toBe('rec-own');
        expect(loaded?.name).toBe('My Strategy');
    });

    it('drops recipe id when loading a public template owned by another user', async () => {
        const { db } = createMockDb({
            'select:strategy_recipes': {
                data: {
                    ...recipeRow({ id: 'rec-pub', user_id: 'other-user', is_public: true }),
                    name: 'Public Template',
                    description: 'Shared',
                    cadence: '1d',
                },
            },
        });
        mockServerDb = db;

        const loaded = await fetchRecipeById('rec-pub', 'user-1');
        expect(loaded?.id).toBeUndefined();
        expect(loaded?.name).toBe('Public Template');
    });

    it('rejects private recipes owned by another user', async () => {
        const { db } = createMockDb({
            'select:strategy_recipes': {
                data: recipeRow({ id: 'rec-priv', user_id: 'other-user', is_public: false }),
            },
        });
        mockServerDb = db;

        await expect(fetchRecipeById('rec-priv', 'user-1')).rejects.toThrow('Unauthorized');
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
