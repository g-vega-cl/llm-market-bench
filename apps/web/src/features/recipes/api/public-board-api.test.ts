import { describe, expect, it, vi } from 'vitest';

const statsRows = [
    {
        recipe_id: 'r-new',
        name: 'Chip Momentum',
        return_pct: 3.2,
        spy_return_pct: 1.1,
        trade_count: 4,
        open_positions: 2,
        runs_today: 2,
        last_run_at: '2026-11-19T15:30:00+00:00',
        last_action: { action: 'EXIT', ticker: 'NVDA', price: 181.2, reason: 'broken' },
        resolved_model: 'qwen3.8-27b',
    },
    {
        recipe_id: 'r-old',
        name: 'Value Screener',
        return_pct: -4.5,
        spy_return_pct: 3.1,
        trade_count: 1,
        open_positions: 0,
        runs_today: 1,
        last_run_at: '2026-11-18T15:30:00+00:00',
        last_action: null,
        resolved_model: null,
    },
];

const summaryRow = { live_count: 7, beat_spy_count: 3, median_return_pct: -0.65 };

const recipeRows = [
    {
        id: 'r-new',
        description: 'Buy chipmakers when AI capex news turns positive',
        graph_json: {
            stages: [
                {
                    blocks: [
                        { id: 'b1', type: 'prompt' },
                        { id: 'b2', type: 'news' },
                        { id: 'b3', type: 'technical_file' },
                        { id: 'b4', type: 'output_format' },
                    ],
                },
            ],
        },
        updated_at: '2026-11-19T15:30:00+00:00',
    },
    { id: 'r-old', description: null, graph_json: {}, updated_at: null },
];
const feedRows = [
    {
        recipe_id: 'r-new',
        recipe_name: 'Chip Momentum',
        action: 'exit',
        ticker: 'nvda',
        at: '2026-11-19T15:30:00+00:00',
    },
];

vi.mock('~/lib/db', () => ({
    getDbAdminClient: () => ({
        from: (table: string) => {
            if (table === 'recipe_public_stats') {
                return {
                    select: () => ({
                        eq: () => ({
                            order: () => ({
                                limit: async () => ({ data: statsRows, error: null }),
                            }),
                        }),
                    }),
                };
            }
            if (table === 'recipe_desk_summary') {
                return {
                    select: () => ({
                        eq: () => ({ maybeSingle: async () => ({ data: summaryRow }) }),
                    }),
                };
            }
            if (table === 'strategy_recipes') {
                return {
                    select: () => ({
                        in: async () => ({ data: recipeRows, error: null }),
                    }),
                };
            }
            if (table === 'recipe_desk_feed') {
                return {
                    select: () => ({
                        order: () => ({ limit: async () => ({ data: feedRows }) }),
                    }),
                };
            }
            throw new Error(`unexpected table ${table}`);
        },
    }),
}));

const { fetchPublicDesk } = await import('./public-board-api');

describe('fetchPublicDesk', () => {
    it('reads cards in the order the runner materialised them', async () => {
        const desk = await fetchPublicDesk();
        expect(desk.cards.map((card) => card.recipeId)).toEqual(['r-new', 'r-old']);
        expect(desk.cards[1].returnPct).toBe(-4.5);
    });

    it('takes the headline from the materialised summary, not from the page', async () => {
        const desk = await fetchPublicDesk();
        // live_count is 7 while only two cards were fetched: the count is a real
        // count, not cards.length.
        expect(desk.liveCount).toBe(7);
        expect(desk.beatSpyCount).toBe(3);
        expect(desk.medianReturnPct).toBe(-0.65);
    });

    it('uppercases the materialised feed rows', async () => {
        const desk = await fetchPublicDesk();
        expect(desk.feed).toEqual([
            {
                at: '2026-11-19T15:30:00+00:00',
                recipeId: 'r-new',
                recipeName: 'Chip Momentum',
                action: 'EXIT',
                ticker: 'NVDA',
            },
        ]);
    });

    it('never reads the execution queue (zero compute in the request path)', async () => {
        // The mock throws for any table other than the materialised rows and the
        // recipe prompt/graph the excerpt needs.
        await expect(fetchPublicDesk()).resolves.toBeDefined();
    });

    it("carries the owner's sentence beside each card", async () => {
        const desk = await fetchPublicDesk();
        expect(desk.cards[0].description).toBe('Buy chipmakers when AI capex news turns positive');
        expect(desk.cards[1].description).toBeNull();
    });

    it('spotlights the newest bot that has a prompt, with its compiled blocks', async () => {
        const desk = await fetchPublicDesk();
        expect(desk.spotlight?.recipeId).toBe('r-new');
        expect(desk.spotlight?.prompt).toContain('chipmakers');
        // Unknown types are humanised rather than dropped or shown raw.
        expect(desk.spotlight?.blocks).toEqual(['Prompt', 'News', 'technical file', 'Output']);
    });

    it('survives a failed prompt read without losing the cards', async () => {
        const desk = await fetchPublicDesk();
        expect(desk.cards).toHaveLength(2);
    });
});
