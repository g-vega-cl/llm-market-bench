import { beforeEach, describe, expect, it, vi } from 'vitest';
import { archiveRecipe } from './archive-recipe';

interface RecordedCall {
    op: 'select' | 'insert' | 'update';
    table: string;
    payload?: Record<string, unknown>;
    filters: Record<string, unknown>;
}

type DbResult = { data?: unknown; error?: { message: string } | null };

function createMockDb(
    results: Record<string, DbResult>,
    options: { cancelError?: { message: string } | null; cancelledRows?: unknown[] } = {},
) {
    const calls: RecordedCall[] = [];
    const { cancelError = null, cancelledRows = [{ id: 'job-1' }, { id: 'job-2' }] } = options;

    const db = {
        from(table: string) {
            const call: RecordedCall = { op: 'select', table, filters: {} };
            const resolve = (): DbResult =>
                results[`${call.op}:${table}`] ?? { data: null, error: null };

            const chain = {
                select(_cols?: string) {
                    return chain;
                },
                update(payload: Record<string, unknown>) {
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
                single() {
                    calls.push(call);
                    return Promise.resolve(resolve());
                },
                // biome-ignore lint/suspicious/noThenProperty: the mock mimics the thenable supabase-js query builder
                then(
                    onFulfilled?: (value: unknown) => unknown,
                    onRejected?: (reason: unknown) => unknown,
                ) {
                    calls.push(call);
                    const settled: DbResult =
                        table === 'recipe_execution_queue'
                            ? { data: cancelError ? null : cancelledRows, error: cancelError }
                            : resolve();
                    return Promise.resolve(settled).then(onFulfilled, onRejected);
                },
            };
            return chain;
        },
    };

    return { db, calls };
}

let mockAdminDb: unknown;
vi.mock('~/lib/db', () => ({
    getDbAdminClient: () => mockAdminDb,
}));

beforeEach(() => {
    vi.clearAllMocks();
});

describe('archiveRecipe', () => {
    it('hides the strategy, clears is_live, and cancels its open jobs', async () => {
        const { db, calls } = createMockDb({
            'select:strategy_recipes': { data: { user_id: 'user-1' } },
            'update:strategy_recipes': {
                data: { id: 'rec-1', archived_at: '2026-11-17T14:00:00.000Z' },
            },
        });
        mockAdminDb = db;

        const result = await archiveRecipe('rec-1', 'user-1');

        expect(result).toMatchObject({ id: 'rec-1', cancelled_jobs: 2 });
        const recipeUpdate = calls.find(
            (call) => call.op === 'update' && call.table === 'strategy_recipes',
        );
        // Hiding is not a content edit: bumping updated_at would trip the
        // showcase publisher's graph-drift guard.
        expect(recipeUpdate?.payload).not.toHaveProperty('updated_at');
        expect(recipeUpdate?.payload).toMatchObject({ is_live: false, turbo_expires_at: null });
        expect(typeof recipeUpdate?.payload?.archived_at).toBe('string');
        expect(recipeUpdate?.filters).toMatchObject({ id: 'rec-1', user_id: 'user-1' });

        const jobCancel = calls.find(
            (call) => call.op === 'update' && call.table === 'recipe_execution_queue',
        );
        expect(jobCancel?.payload).toMatchObject({ status: 'cancelled' });
        expect(jobCancel?.filters).toMatchObject({
            recipe_id: 'rec-1',
            user_id: 'user-1',
            status: ['pending', 'processing'],
        });
    });

    it('refuses a recipe owned by another user and writes nothing', async () => {
        const { db, calls } = createMockDb({
            'select:strategy_recipes': { data: { user_id: 'user-2' } },
        });
        mockAdminDb = db;

        await expect(archiveRecipe('rec-1', 'user-1')).rejects.toThrow(
            'Unauthorized: cannot remove a recipe owned by another user',
        );
        expect(calls.some((call) => call.op === 'update')).toBe(false);
    });

    it('fails closed when the recipe does not exist', async () => {
        const { db } = createMockDb({
            'select:strategy_recipes': { data: null, error: { message: 'no rows' } },
        });
        mockAdminDb = db;

        await expect(archiveRecipe('missing', 'user-1')).rejects.toThrow('Recipe not found');
    });

    it('reports a failed hide instead of pretending it worked', async () => {
        const { db } = createMockDb({
            'select:strategy_recipes': { data: { user_id: 'user-1' } },
            'update:strategy_recipes': { data: null, error: { message: 'PGRST204' } },
        });
        mockAdminDb = db;

        await expect(archiveRecipe('rec-1', 'user-1')).rejects.toThrow('PGRST204');
    });

    it('keeps the removal when cancelling queued jobs fails', async () => {
        const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
        const { db } = createMockDb(
            {
                'select:strategy_recipes': { data: { user_id: 'user-1' } },
                'update:strategy_recipes': {
                    data: { id: 'rec-1', archived_at: '2026-11-17T14:00:00.000Z' },
                },
            },
            { cancelError: { message: 'PGRST204 recipe_execution_queue' } },
        );
        mockAdminDb = db;

        const result = await archiveRecipe('rec-1', 'user-1');

        expect(result.cancelled_jobs).toBe(0);
        expect(errorSpy).toHaveBeenCalled();
        errorSpy.mockRestore();
    });
});
