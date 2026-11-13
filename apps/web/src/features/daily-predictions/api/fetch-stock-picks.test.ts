import { beforeEach, describe, expect, it, vi } from 'vitest';

type Row = Record<string, unknown>;

let basketsData: Row[] = [];
let picksData: Row[] = [];
let basketsError: { message: string } | null = null;
let picksError: { message: string } | null = null;
const picksInSpy = vi.fn();
const fromSpy = vi.fn();

interface Chain {
    select: ReturnType<typeof vi.fn>;
    order: ReturnType<typeof vi.fn>;
    in: ReturnType<typeof vi.fn>;
}

function createChain(table: 'daily_stock_baskets' | 'daily_stock_picks'): Chain {
    let scopedBasketIds: string[] | null = null;
    const chain = {} as Chain;
    chain.select = vi.fn(() => chain);
    chain.in = vi.fn((column: string, ids: string[]) => {
        picksInSpy(column, ids);
        scopedBasketIds = ids;
        return chain;
    });
    chain.order = vi.fn(() => {
        if (table === 'daily_stock_baskets') {
            return Promise.resolve({ data: basketsData, error: basketsError });
        }
        // Emulate the server-side `basket_id in (...)` filter.
        const rows =
            scopedBasketIds === null
                ? picksData
                : picksData.filter((p) => scopedBasketIds?.includes(p.basket_id as string));
        return Promise.resolve({ data: rows, error: picksError });
    });
    return chain;
}

let basketsChain = createChain('daily_stock_baskets');
let picksChain = createChain('daily_stock_picks');

vi.mock('~/lib/db', () => ({
    getDbServerClient: () => ({
        from: (table: string) => {
            fromSpy(table);
            return table === 'daily_stock_baskets' ? basketsChain : picksChain;
        },
    }),
}));

import { fetchDailyStockBaskets, latestBasketIdsByModel } from './fetch-stock-picks';

function basket(id: string, targetDate: string, modelName: string): Row {
    return { id, target_date: targetDate, model_name: modelName, status: 'evaluated' };
}

describe('fetchDailyStockBaskets', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        basketsChain = createChain('daily_stock_baskets');
        picksChain = createChain('daily_stock_picks');
        basketsData = [];
        picksData = [];
        basketsError = null;
        picksError = null;
    });

    it('returns an empty list without querying picks when no baskets exist', async () => {
        const result = await fetchDailyStockBaskets();

        expect(result).toEqual([]);
        expect(fromSpy).not.toHaveBeenCalledWith('daily_stock_picks');
    });

    it('fetches picks only for the newest basket of each model track', async () => {
        basketsData = [
            basket('b-consensus-new', '2026-11-13', 'consensus'),
            basket('b-consensus-old', '2026-11-12', 'consensus'),
            basket('b-minimax', '2026-11-13', 'MiniMax-M3'),
        ];
        picksData = [
            { id: 'p1', basket_id: 'b-consensus-new', rank: 1, ticker: 'AMD' },
            { id: 'p2', basket_id: 'b-minimax', rank: 1, ticker: 'NVDA' },
            { id: 'p3', basket_id: 'b-consensus-old', rank: 1, ticker: 'STALE' },
        ];

        const result = await fetchDailyStockBaskets();

        expect(picksInSpy).toHaveBeenCalledTimes(1);
        const [column, ids] = picksInSpy.mock.calls[0];
        expect(column).toBe('basket_id');
        expect(ids).toEqual(['b-consensus-new', 'b-minimax']);
        expect(ids).not.toContain('b-consensus-old');

        expect(result.find((b) => b.id === 'b-consensus-new')?.picks).toHaveLength(1);
        expect(result.find((b) => b.id === 'b-consensus-old')?.picks).toEqual([]);
    });

    it('surfaces basket query errors', async () => {
        basketsError = { message: 'boom' };

        await expect(fetchDailyStockBaskets()).rejects.toThrow('boom');
    });

    it('surfaces pick query errors', async () => {
        basketsData = [basket('b-consensus', '2026-11-13', 'consensus')];
        picksError = { message: 'picks boom' };

        await expect(fetchDailyStockBaskets()).rejects.toThrow('picks boom');
    });
});

describe('latestBasketIdsByModel', () => {
    it('keeps only the first (newest) basket per model in input order', () => {
        const ids = latestBasketIdsByModel([
            basket('b1', '2026-11-13', 'consensus'),
            basket('b2', '2026-11-13', 'gpt-5.6-luna'),
            basket('b3', '2026-11-12', 'consensus'),
            basket('b4', '2026-11-11', 'gpt-5.6-luna'),
        ] as never);

        expect(ids).toEqual(['b1', 'b2']);
    });
});
