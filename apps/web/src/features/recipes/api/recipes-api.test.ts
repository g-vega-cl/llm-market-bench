import { beforeEach, describe, expect, it, vi } from 'vitest';
import { STARTER_RECIPES } from '../starter-templates';
import type { PushStrategy, StrategyStage } from '../types';
import {
    assertNoPrevOutputPlaceholder,
    assertSingleLlmStage,
    enqueueRecipeJob,
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
                limit(_n: number) {
                    return chain;
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

    it('queues a job for a recipe the caller owns', async () => {
        const { db, calls } = createMockDb({
            'select:strategy_recipes': { data: recipeRow() },
            'select:recipe_execution_queue': { data: [] },
            'insert:recipe_execution_queue': { data: { id: 'job-1' } },
        });
        mockAdminDb = db;

        await enqueueRecipeJob('rec-1', 'backtest', 'user-1');

        const insert = calls.find((call) => call.op === 'insert');
        expect(insert?.payload).toMatchObject({
            recipe_id: 'rec-1',
            user_id: 'user-1',
            mode: 'backtest',
            priority: 10,
        });
    });
});
