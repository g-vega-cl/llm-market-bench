import { renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useActualReturns } from './useActualReturns';

const mockGetDbBrowserClient = vi.hoisted(() => vi.fn());

vi.mock('~/lib/db', () => ({
    getDbBrowserClient: mockGetDbBrowserClient,
}));

function makePendingChain() {
    const pending = new Promise(() => {});
    const chain: Record<string, unknown> = {};
    for (const m of ['from', 'select', 'gte', 'lte', 'in', 'eq']) {
        chain[m] = () => chain;
    }
    chain.order = () => pending;
    return chain;
}

function makeResolvedClient(opts: {
    portfolioRows?: unknown[] | null;
    portfolioError?: Error | null;
    spyRows?: unknown[] | null;
    spyError?: Error | null;
}) {
    return {
        from: (table: string) => {
            const chain: Record<string, unknown> = {};
            for (const m of ['select', 'gte', 'lte', 'in', 'eq']) {
                chain[m] = () => chain;
            }
            chain.order = () =>
                Promise.resolve(
                    table === 'price_history'
                        ? { data: opts.spyRows ?? null, error: opts.spyError ?? null }
                        : { data: opts.portfolioRows ?? null, error: opts.portfolioError ?? null },
                );
            return chain;
        },
    };
}

describe('useActualReturns', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockGetDbBrowserClient.mockImplementation(() => makePendingChain());
    });

    it('reports loading on the very first render when a week range is provided', () => {
        const { result } = renderHook(() =>
            useActualReturns('2026-06-22', '2026-06-26', { p1: {} as never }, false, null),
        );
        expect(result.current.isLoadingActuals).toBe(true);
        expect(result.current.actualReturns).toBeNull();
        expect(result.current.actualsError).toBeNull();
    });

    it('is not loading when there is no week range to fetch', () => {
        const { result } = renderHook(() => useActualReturns(null, null, null, false, null));
        expect(result.current.isLoadingActuals).toBe(false);
        expect(result.current.actualsError).toBeNull();
    });

    it('clears prior experiment returns and spyReturn when switching to an experiment whose fetch fails', async () => {
        const errSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
        mockGetDbBrowserClient.mockImplementation(() =>
            makeResolvedClient({
                portfolioRows: [
                    {
                        portfolio_id: 'p1',
                        total_equity: 10000,
                        date: '2026-06-22',
                        portfolios: { owner_id: 'gemini-3.5-flash-lite' },
                    },
                    {
                        portfolio_id: 'p1',
                        total_equity: 10200,
                        date: '2026-06-26',
                        portfolios: { owner_id: 'gemini-3.5-flash-lite' },
                    },
                ],
                spyRows: [
                    { fetched_at: '2026-06-22T00:00:00Z', price: 100 },
                    { fetched_at: '2026-06-26T00:00:00Z', price: 103 },
                ],
            }),
        );

        const { result, rerender } = renderHook(
            ({ weekStart, weekEnd }: { weekStart: string | null; weekEnd: string | null }) =>
                useActualReturns(weekStart, weekEnd, { p1: {} as never }, true, null),
            { initialProps: { weekStart: '2026-06-22', weekEnd: '2026-06-26' } },
        );

        await waitFor(() => expect(result.current.isLoadingActuals).toBe(false));
        expect(result.current.actualReturns?.['gemini-3.5-flash-lite']?.actualReturn).toBeCloseTo(
            2.0,
            4,
        );
        expect(result.current.actualSpyReturn).toBeCloseTo(3.0, 4);

        mockGetDbBrowserClient.mockImplementation(() =>
            makeResolvedClient({
                portfolioError: new Error('Archive DB offline'),
            }),
        );

        rerender({ weekStart: '2026-06-29', weekEnd: '2026-07-03' });

        await waitFor(() => expect(result.current.isLoadingActuals).toBe(false));
        expect(result.current.actualsError).toBe('Archive DB offline');
        expect(result.current.actualReturns).toBeNull();
        expect(result.current.actualSpyReturn).toBeNull();
        errSpy.mockRestore();
    });

    it('surfaces spyRes.error when SPY benchmark query fails', async () => {
        const errSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
        mockGetDbBrowserClient.mockImplementation(() =>
            makeResolvedClient({
                portfolioRows: [],
                spyError: new Error('SPY query timeout'),
            }),
        );

        const { result } = renderHook(() =>
            useActualReturns('2026-06-22', '2026-06-26', { p1: {} as never }, true, null),
        );

        await waitFor(() => expect(result.current.isLoadingActuals).toBe(false));
        expect(result.current.actualsError).toBe('SPY query timeout');
        expect(result.current.actualReturns).toBeNull();
        expect(result.current.actualSpyReturn).toBeNull();
        errSpy.mockRestore();
    });
});
