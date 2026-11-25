import { describe, expect, it, vi } from 'vitest';

const inserted: Array<Record<string, unknown>> = [];
let sourceRow: Record<string, unknown> | null = null;

vi.mock('~/lib/db', () => ({
    getDbAdminClient: () => ({
        from: () => ({
            select: () => ({
                eq: () => ({
                    single: async () => ({
                        data: sourceRow,
                        error: sourceRow ? null : { message: 'not found' },
                    }),
                }),
            }),
            insert: (payload: Record<string, unknown>) => ({
                select: () => ({
                    single: async () => {
                        inserted.push(payload);
                        return { data: { id: 'new-recipe', name: payload.name }, error: null };
                    },
                }),
            }),
        }),
    }),
}));

const { forkRecipe } = await import('./fork-recipe');

const templateGraph = {
    version: '2.0-push',
    name: 'Chip Momentum',
    cadence: '3h',
    stages: [{ id: 's1', blocks: [{ id: 'b1', type: 'output_format' }], selected_tools: [] }],
};

function setSource(row: Record<string, unknown>) {
    sourceRow = row;
    inserted.length = 0;
}

describe('forkRecipe', () => {
    it('copies a public template into a new row owned by the caller', async () => {
        setSource({
            user_id: 'someone-else',
            name: 'Chip Momentum',
            description: 'x',
            cadence: '3h',
            graph_json: templateGraph,
            is_public: true,
            is_template: true,
            archived_at: null,
        });

        const created = await forkRecipe('src-1', 'user-1');

        expect(created.id).toBe('new-recipe');
        expect(inserted).toHaveLength(1);
        expect(inserted[0].user_id).toBe('user-1');
        expect(inserted[0].name).toBe('Copy of Chip Momentum');
        // A fork never inherits live scheduling and inherits the source's
        // visibility; a template is public, so its copy is too.
        expect(inserted[0].is_live).toBe(false);
        expect(inserted[0].is_public).toBe(true);
        expect(inserted[0].paper_cash).toBe(10000);
    });

    it('keeps the fork of a private bot private', async () => {
        setSource({
            user_id: 'user-1',
            name: 'My private edge',
            description: 'x',
            cadence: '3h',
            graph_json: templateGraph,
            is_public: false,
            is_template: false,
            archived_at: null,
        });

        await forkRecipe('src-private', 'user-1');

        expect(inserted).toHaveLength(1);
        // Publishing a copy of a strategy the owner hid would leak it.
        expect(inserted[0].is_public).toBe(false);
    });

    it('refuses a private recipe owned by somebody else', async () => {
        setSource({
            user_id: 'someone-else',
            name: 'Private',
            cadence: '3h',
            graph_json: templateGraph,
            is_public: false,
            is_template: false,
            archived_at: null,
        });

        await expect(forkRecipe('src-2', 'user-1')).rejects.toThrow(
            /cannot fork a private recipe/i,
        );
        expect(inserted).toHaveLength(0);
    });

    it('refuses to fork a strategy the owner archived', async () => {
        setSource({
            user_id: 'user-1',
            name: 'Mine',
            cadence: '3h',
            graph_json: templateGraph,
            is_public: true,
            is_template: false,
            archived_at: '2026-11-17T00:00:00.000Z',
        });

        await expect(forkRecipe('src-3', 'user-1')).rejects.toThrow(/removed from My Strategies/i);
        expect(inserted).toHaveLength(0);
    });

    it('rejects a malformed graph instead of copying it into a queue row', async () => {
        setSource({
            user_id: 'someone-else',
            name: 'Broken',
            cadence: '3h',
            graph_json: { stages: [{ id: 's1' }, { id: 's2' }] },
            is_public: true,
            is_template: false,
            archived_at: null,
        });

        await expect(forkRecipe('src-4', 'user-1')).rejects.toThrow();
        expect(inserted).toHaveLength(0);
    });
});
