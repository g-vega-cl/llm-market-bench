import { beforeEach, describe, expect, it, vi } from 'vitest';
import { STARTER_RECIPES } from '../starter-templates';
import {
    clearPublicRecipeReadCaches,
    fetchLivePortfolioAndRuns,
    fetchRecipeAlerts,
    fetchRecipeOverview,
    markAlertRead,
    previewStrategyPrompt,
    submitWaitlistPledge,
} from './recipes-studio-api';

const mockGetUser = vi.fn();
vi.mock('~/lib/auth', () => ({
    getAuthServerClient: () => ({
        auth: { getUser: mockGetUser },
    }),
}));

let mockAdminDb: unknown;
let mockServerDb: unknown;
vi.mock('~/lib/db', () => ({
    getDbAdminClient: () => mockAdminDb,
    getDbServerClient: () => mockServerDb,
}));

function makeDbChain(dataByTable: Record<string, unknown[]>) {
    return {
        from(table: string) {
            const rows = dataByTable[table] ?? [];
            const chain = {
                select: () => chain,
                update: () => ({
                    eq: () => ({
                        eq: () => Promise.resolve({ error: null }),
                    }),
                }),
                insert: () => Promise.resolve({ error: null }),
                eq: () => chain,
                order: () => chain,
                limit: () => Promise.resolve({ data: rows, error: null }),
            };
            return chain;
        },
    };
}

describe('recipes-studio-api', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        clearPublicRecipeReadCaches();
        mockGetUser.mockResolvedValue({ data: { user: { id: 'user-1' } } });
    });

    it('fetches, marks alerts read, and records waitlist pledges', async () => {
        mockAdminDb = makeDbChain({
            recipe_alerts_inbox: [{ id: 'al-1', title: 'Alert', body: 'Filled', is_read: false }],
        });

        const alerts = await fetchRecipeAlerts('user-1');
        expect(alerts).toHaveLength(1);
        expect(await markAlertRead('al-1', 'user-1')).toEqual({ success: true });
        expect(await submitWaitlistPledge('user-1', 'a@b.com', 'pro', 'live')).toEqual({
            success: true,
        });
    });

    it('hydrates prompt preview blocks without querying embeddings', async () => {
        const nowIso = new Date().toISOString();
        mockServerDb = makeDbChain({
            recipe_news_corpus: [
                {
                    article_id: 'n1',
                    title: 'NVDA earnings beat',
                    full_text: 'NVDA posted record revenue.',
                    date_published: nowIso,
                    tickers: ['NVDA'],
                },
            ],
            memories: [
                {
                    id: 'm1',
                    content: 'AI capex cycle remains strong',
                    created_at: nowIso,
                    memory_type: 'MARKET_EVENT',
                    importance_score: 8,
                },
            ],
        });

        const hydrated = await previewStrategyPrompt(STARTER_RECIPES[0]);
        expect(Object.keys(hydrated).length).toBeGreaterThan(0);
    });

    it('fetches live paper portfolio enriched with mark prices and recent live_turn runs', async () => {
        mockServerDb = {
            from(table: string) {
                const chain = {
                    select: () => chain,
                    eq: () => chain,
                    in: () => chain,
                    order: () => chain,
                    limit: () =>
                        Promise.resolve({
                            data:
                                table === 'recipe_intraday_bars'
                                    ? [
                                          {
                                              ticker: 'NVDA',
                                              bar_time_utc: '2026-11-15T15:30:00+00:00',
                                              close: 220.0,
                                          },
                                      ]
                                    : table === 'recipe_execution_queue'
                                      ? [
                                            {
                                                id: 'live-1',
                                                recipe_id: 'rec-1',
                                                mode: 'live_turn',
                                                status: 'completed',
                                                progress_pct: 100,
                                                result_json: {
                                                    mode: 'live_turn',
                                                    as_of_utc: '2026-11-15T15:30:00+00:00',
                                                    stages: [],
                                                    final_output: '[]',
                                                    signals: [],
                                                },
                                                error_message: null,
                                                created_at: '2026-11-15T15:30:00+00:00',
                                            },
                                        ]
                                      : [],
                            error: null,
                        }),
                    single: () =>
                        Promise.resolve({
                            data: {
                                id: 'rec-1',
                                user_id: 'user-1',
                                is_public: false,
                                is_template: false,
                                is_live: true,
                                paper_cash: 7500,
                                paper_positions: [
                                    {
                                        ticker: 'NVDA',
                                        side: 'LONG',
                                        shares: 12.5,
                                        entry_price: 200.0,
                                        entry_time: '2026-11-14 09:30 ET',
                                        cost_basis: 2500.0,
                                    },
                                ],
                                paper_trades: [],
                                paper_equity_curve: [
                                    { time: '2026-11-14 09:30 ET', equity: 10000 },
                                    { time: '2026-11-15 15:30 ET', equity: 10250 },
                                ],
                            },
                            error: null,
                        }),
                };
                return chain;
            },
        };

        const liveState = await fetchLivePortfolioAndRuns('rec-1', 'user-1');
        expect(liveState.portfolio.cash).toBe(7500);
        expect(liveState.portfolio.equity_curve).toHaveLength(2);
        expect(liveState.portfolio.open_positions[0].current_price).toBe(220.0);
        expect(liveState.portfolio.open_positions[0].unrealized_pnl_net).toBeGreaterThan(240);
        expect(liveState.recentLiveRuns).toHaveLength(1);
        expect(liveState.liveMeta).toEqual({
            recipeName: '',
            description: '',
            cadence: '3h',
            isLive: true,
            isOwner: true,
            isPublic: false,
            isTemplate: false,
            turboExpiresAt: null,
            turboUsedToday: false,
        });
    });

    it('prefers newer live signal_prices over older intraday bars and bounds bar query with order and limit', async () => {
        let barOrderCalled = false;
        let barLimitCalled = false;
        let queueUserFilter: unknown = null;

        mockServerDb = {
            from(table: string) {
                const chain = {
                    select: () => chain,
                    eq: (col: string, val: unknown) => {
                        if (table === 'recipe_execution_queue' && col === 'user_id') {
                            queueUserFilter = val;
                        }
                        return chain;
                    },
                    in: () => chain,
                    order: () => {
                        if (table === 'recipe_intraday_bars') barOrderCalled = true;
                        return chain;
                    },
                    limit: () => {
                        if (table === 'recipe_intraday_bars') {
                            barLimitCalled = true;
                            return Promise.resolve({
                                data: [
                                    {
                                        ticker: 'NVDA',
                                        bar_time_utc: '2026-11-10T15:30:00+00:00',
                                        close: 190.0,
                                    },
                                ],
                                error: null,
                            });
                        }
                        return Promise.resolve({
                            data: [
                                {
                                    id: 'live-fresh',
                                    recipe_id: 'rec-pub',
                                    mode: 'live_turn',
                                    status: 'completed',
                                    progress_pct: 100,
                                    result_json: {
                                        mode: 'live_turn',
                                        as_of_utc: '2026-11-15T15:30:00+00:00',
                                        signal_prices: { NVDA: 230.0 },
                                        stages: [],
                                        final_output: '[]',
                                        signals: [],
                                    },
                                    error_message: null,
                                    created_at: '2026-11-15T15:30:00+00:00',
                                },
                            ],
                            error: null,
                        });
                    },
                    single: () =>
                        Promise.resolve({
                            data: {
                                id: 'rec-pub',
                                user_id: 'author-99',
                                is_public: true,
                                is_template: false,
                                paper_cash: 7500,
                                paper_positions: [
                                    {
                                        ticker: 'NVDA',
                                        shares: 10,
                                        entry_price: 200.0,
                                        entry_time: '2026-11-14 09:30 ET',
                                        cost_basis: 2000.0,
                                    },
                                ],
                                paper_trades: [],
                            },
                            error: null,
                        }),
                };
                return chain;
            },
        };

        const res = await fetchLivePortfolioAndRuns('rec-pub', 'viewer-1');
        expect(barOrderCalled).toBe(true);
        expect(barLimitCalled).toBe(true);
        expect(queueUserFilter).toBe('author-99');
        expect(res.portfolio.open_positions[0]?.current_price).toBe(230.0);
        expect(res.portfolio.total_equity).toBe(9800.0);
        expect(res.portfolio.cash + (res.portfolio.open_positions[0]?.market_value ?? 0)).toBe(
            res.portfolio.total_equity,
        );
    });

    it('loads public overview for logged-out visitors without leaking owner id, and rejects private recipes', async () => {
        const makeOverviewDb = (isPublic: boolean) => ({
            from(_table: string) {
                const chain = {
                    select: () => chain,
                    eq: () => chain,
                    in: () => chain,
                    order: () => chain,
                    limit: () => Promise.resolve({ data: [], error: null }),
                    single: () =>
                        Promise.resolve({
                            data: {
                                id: 'rec-overview',
                                user_id: 'author-1',
                                name: 'Shared Catalyst Bot',
                                description: 'Public showcase bot',
                                cadence: '3h',
                                is_public: isPublic,
                                is_template: false,
                                is_live: true,
                                turbo_expires_at: null,
                                archived_at: null,
                                graph_json: STARTER_RECIPES[0],
                                paper_cash: 10000,
                                paper_positions: [],
                                paper_trades: [],
                                paper_equity_curve: [],
                            },
                            error: null,
                        }),
                };
                return chain;
            },
        });

        mockServerDb = makeOverviewDb(true);
        const pub = await fetchRecipeOverview('rec-overview', null);
        expect(pub.isOwner).toBe(false);
        expect(pub.isPublic).toBe(true);
        expect(pub.strategy.id).toBeUndefined();
        expect(pub.strategy.name).toBe('Shared Catalyst Bot');

        clearPublicRecipeReadCaches();
        mockServerDb = makeOverviewDb(false);
        await expect(fetchRecipeOverview('rec-overview', null)).rejects.toThrow('Unauthorized');
    });
});
