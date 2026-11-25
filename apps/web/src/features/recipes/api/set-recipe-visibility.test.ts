import { beforeEach, describe, expect, it, vi } from 'vitest';
import { readVisibilityPayload, setRecipeVisibility } from './set-recipe-visibility';

interface RecordedCall {
    op: 'select' | 'insert' | 'update';
    table: string;
    payload?: Record<string, unknown>;
    filters: Record<string, unknown>;
}

type DbResult = { data?: unknown; error?: { message: string } | null };

function createMockDb(results: Record<string, DbResult>) {
    const calls: RecordedCall[] = [];

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
                single() {
                    calls.push(call);
                    return Promise.resolve(resolve());
                },
            };
            return chain;
        },
    };

    return { db, calls };
}

let mockAdminDb: unknown;
const invalidatePublicRecipeCache = vi.hoisted(() => vi.fn());

vi.mock('~/lib/db', () => ({
    getDbAdminClient: () => mockAdminDb,
}));

vi.mock('./recipes-studio-api', () => ({
    invalidatePublicRecipeCache,
}));

beforeEach(() => {
    vi.clearAllMocks();
});

describe('setRecipeVisibility', () => {
    it('flips a bot to private and drops its cached public read', async () => {
        const { db, calls } = createMockDb({
            'select:strategy_recipes': { data: { user_id: 'user-1', is_template: false } },
            'update:strategy_recipes': { data: { id: 'rec-1', is_public: false } },
        });
        mockAdminDb = db;

        const result = await setRecipeVisibility('rec-1', 'user-1', false);

        expect(result).toEqual({ id: 'rec-1', isPublic: false });
        const update = calls.find(
            (call) => call.op === 'update' && call.table === 'strategy_recipes',
        );
        expect(update?.payload).toMatchObject({ is_public: false });
        // Visibility is not a content edit: bumping updated_at would trip the
        // showcase publisher's graph-drift guard.
        expect(update?.payload).not.toHaveProperty('updated_at');
        expect(update?.filters).toMatchObject({ id: 'rec-1', user_id: 'user-1' });
        expect(invalidatePublicRecipeCache).toHaveBeenCalledWith('rec-1');
    });

    it('flips a bot back to public and refreshes the public path', async () => {
        const { db } = createMockDb({
            'select:strategy_recipes': { data: { user_id: 'user-1', is_template: false } },
            'update:strategy_recipes': { data: { id: 'rec-1', is_public: true } },
        });
        mockAdminDb = db;

        await expect(setRecipeVisibility('rec-1', 'user-1', true)).resolves.toEqual({
            id: 'rec-1',
            isPublic: true,
        });
        expect(invalidatePublicRecipeCache).toHaveBeenCalledWith('rec-1');
    });

    it('refuses a bot owned by another user and writes nothing', async () => {
        const { db, calls } = createMockDb({
            'select:strategy_recipes': { data: { user_id: 'user-2', is_template: false } },
        });
        mockAdminDb = db;

        await expect(setRecipeVisibility('rec-1', 'user-1', false)).rejects.toThrow(
            'Unauthorized: cannot change visibility of a recipe owned by another user',
        );
        expect(calls.some((call) => call.op === 'update')).toBe(false);
        expect(invalidatePublicRecipeCache).not.toHaveBeenCalled();
    });

    it('refuses starter templates, which are public by definition', async () => {
        const { db, calls } = createMockDb({
            'select:strategy_recipes': { data: { user_id: 'user-1', is_template: true } },
        });
        mockAdminDb = db;

        await expect(setRecipeVisibility('rec-1', 'user-1', false)).rejects.toThrow(
            'Cannot change the visibility of a starter template',
        );
        expect(calls.some((call) => call.op === 'update')).toBe(false);
    });

    it('fails closed when the bot does not exist', async () => {
        const { db } = createMockDb({
            'select:strategy_recipes': { data: null, error: { message: 'no rows' } },
        });
        mockAdminDb = db;

        await expect(setRecipeVisibility('missing', 'user-1', false)).rejects.toThrow(
            'Recipe not found',
        );
    });

    it('refuses to republish a removed bot, which has its own restore path', async () => {
        const { db, calls } = createMockDb({
            'select:strategy_recipes': {
                data: {
                    user_id: 'user-1',
                    is_template: false,
                    archived_at: '2026-11-18T00:00:00Z',
                },
            },
        });
        mockAdminDb = db;

        await expect(setRecipeVisibility('rec-1', 'user-1', true)).rejects.toThrow(
            'A removed bot cannot change visibility; restore it first',
        );
        expect(calls.some((call) => call.op === 'update')).toBe(false);
    });

    it('reports a failed flip without leaking the database message', async () => {
        const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
        const { db } = createMockDb({
            'select:strategy_recipes': { data: { user_id: 'user-1', is_template: false } },
            'update:strategy_recipes': { data: null, error: { message: 'PGRST204' } },
        });
        mockAdminDb = db;

        await expect(setRecipeVisibility('rec-1', 'user-1', false)).rejects.toThrow(
            'Failed to change bot visibility',
        );
        expect(errorSpy).toHaveBeenCalled();
        expect(invalidatePublicRecipeCache).not.toHaveBeenCalled();
        errorSpy.mockRestore();
    });
});

describe('readVisibilityPayload', () => {
    it('accepts a strict boolean payload', () => {
        expect(readVisibilityPayload({ recipeId: 'rec-1', isPublic: false })).toEqual({
            recipeId: 'rec-1',
            isPublic: false,
        });
    });

    it('rejects a stringified boolean, which would otherwise publish the bot', () => {
        expect(() => readVisibilityPayload({ recipeId: 'rec-1', isPublic: 'false' })).toThrow(
            'isPublic must be a boolean',
        );
    });

    it('rejects a missing recipe id or a null body', () => {
        expect(() => readVisibilityPayload({ isPublic: true })).toThrow('recipeId must be');
        expect(() => readVisibilityPayload(null)).toThrow('recipeId must be');
    });
});
