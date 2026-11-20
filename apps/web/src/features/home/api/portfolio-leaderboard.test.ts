import { beforeEach, describe, expect, it, vi } from 'vitest';

interface StubResult {
    data?: unknown[] | null;
    count?: number | null;
    error?: { code?: string; message: string } | null;
}

const tableResults: Record<string, StubResult> = {};

function builder(result: StubResult) {
    const query: Record<string, unknown> = {};
    for (const method of ['select', 'eq', 'gte', 'in', 'order', 'limit']) {
        query[method] = () => query;
    }
    // supabase-js awaits its query builder directly, so the stub has to be thenable.
    // biome-ignore lint/suspicious/noThenProperty: test double for the PostgREST builder
    query.then = (resolve: (value: unknown) => unknown, reject: (reason: unknown) => unknown) =>
        Promise.resolve(result).then(resolve, reject);
    return query;
}

vi.mock('~/lib/db', () => ({
    getDbAdminClient: () => ({
        from: (table: string) => builder(tableResults[table] ?? { data: [] }),
    }),
}));

const { fetchPortfolioLeaderboard, normalizePoints, normalizeRows } = await import(
    './portfolio-leaderboard'
);

describe('normalizePoints', () => {
    it('keeps well-formed points', () => {
        expect(normalizePoints([{ date: '2026-11-10', value: 1.5 }])).toEqual([
            { date: '2026-11-10', value: 1.5 },
        ]);
    });

    it('drops a point with a non-numeric value instead of plotting NaN', () => {
        expect(normalizePoints([{ date: '2026-11-10', value: 'oops' }])).toEqual([]);
    });

    it('returns an empty series for a non-array payload', () => {
        expect(normalizePoints(undefined)).toEqual([]);
    });
});

describe('normalizeRows', () => {
    it('keeps a row whose series is missing from crashing the chart', () => {
        const rows = normalizeRows([
            { portfolioId: 'p1', label: 'Max Pain', returnPct: 2.3, observations: 19 },
        ]);

        expect(rows[0].series).toEqual([]);
    });

    it('coerces non-numeric returns', () => {
        const rows = normalizeRows([{ portfolioId: 'p1', label: 'x', returnPct: 'NaN' }]);

        expect(rows[0].returnPct).toBe(0);
    });

    it('returns an empty list for a non-array payload', () => {
        expect(normalizeRows(undefined)).toEqual([]);
    });
});

describe('fetchPortfolioLeaderboard', () => {
    beforeEach(() => {
        for (const key of Object.keys(tableResults)) delete tableResults[key];
        tableResults.portfolio_leaderboard = {
            data: [
                {
                    portfolio_id: 'p1',
                    owner_id: 'sys-max-pain',
                    return_pct: 2.3,
                    observations: 19,
                    window_days: 30,
                    median_return_pct: -1.5,
                },
            ],
            count: 30,
        };
        // The series view already returns percent return from the ranking anchor.
        tableResults.portfolio_leaderboard_series = {
            data: [
                { portfolio_id: 'p1', date: '2026-11-10', return_pct: 0 },
                { portfolio_id: 'p1', date: '2026-11-19', return_pct: 2.3 },
            ],
        };
        tableResults.spy_benchmark_series = {
            data: [
                { date: '2026-11-10', return_pct: 0 },
                { date: '2026-11-19', return_pct: 1 },
            ],
        };
    });

    it('maps the pre-computed percent series onto each row', async () => {
        const board = await fetchPortfolioLeaderboard();

        expect(board.rows).toHaveLength(1);
        expect(board.rows[0].label).toBe('Max Pain');
        expect(board.rows[0].returnPct).toBe(2.3);
        expect(board.rows[0].series[0].value).toBeCloseTo(0);
        expect(board.rows[0].series[1].value).toBeCloseTo(2.3);
    });

    it('carries the median, window and board size from the view', async () => {
        const board = await fetchPortfolioLeaderboard();

        expect(board.medianReturnPct).toBe(-1.5);
        expect(board.windowDays).toBe(30);
        expect(board.trackedCount).toBe(30);
        expect(board.degraded).toBe(false);
    });

    it('reads the SPY benchmark from its own view', async () => {
        const board = await fetchPortfolioLeaderboard();

        expect(board.spy).toHaveLength(2);
        expect(board.spy[0].value).toBeCloseTo(0);
        expect(board.spy[1].value).toBeCloseTo(1);
        expect(board.spyUnavailable).toBe(false);
    });

    it('rejects when the series read fails instead of painting an empty chart', async () => {
        tableResults.portfolio_leaderboard_series = {
            data: null,
            error: { code: '42P01', message: 'boom' },
        };

        await expect(fetchPortfolioLeaderboard()).rejects.toThrow(/42P01: boom/);
    });

    it('keeps the rows and flags the benchmark when only SPY fails', async () => {
        tableResults.spy_benchmark_series = { data: null, error: { message: 'spy down' } };

        const board = await fetchPortfolioLeaderboard();

        expect(board.rows).toHaveLength(1);
        expect(board.spy).toEqual([]);
        expect(board.spyUnavailable).toBe(true);
        expect(board.degraded).toBe(false);
    });

    it('reports an unknown board size when the count read fails', async () => {
        tableResults.portfolio_leaderboard = {
            data: tableResults.portfolio_leaderboard.data,
            count: null,
            error: null,
        };

        const board = await fetchPortfolioLeaderboard();
        expect(board.trackedCount).toBeNull();
    });

    it('returns a fresh empty board when the view has no rows', async () => {
        tableResults.portfolio_leaderboard = { data: [], count: 0 };

        const first = await fetchPortfolioLeaderboard();
        first.rows.push({
            portfolioId: 'x',
            label: 'x',
            returnPct: 0,
            observations: 0,
            series: [],
        });

        const second = await fetchPortfolioLeaderboard();
        expect(second.rows).toEqual([]);
    });
});
