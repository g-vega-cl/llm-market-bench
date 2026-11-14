import { beforeEach, describe, expect, it, vi } from 'vitest';
import { STARTER_RECIPES } from '../starter-templates';
import {
    fetchRecipeAlerts,
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
});
