import { renderHook } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { useActualReturns } from './useActualReturns';

vi.mock('~/lib/db', () => {
    const pending = new Promise(() => {});
    const chain: Record<string, unknown> = {};
    for (const m of ['from', 'select', 'gte', 'lte', 'in', 'eq']) {
        chain[m] = () => chain;
    }
    chain.order = () => pending;
    return { getDbBrowserClient: () => chain };
});

describe('useActualReturns', () => {
    it('reports loading on the very first render when a week range is provided', () => {
        const { result } = renderHook(() =>
            useActualReturns('2026-06-22', '2026-06-26', { p1: {} as never }, false, null),
        );
        expect(result.current.isLoadingActuals).toBe(true);
        expect(result.current.actualReturns).toBeNull();
    });

    it('is not loading when there is no week range to fetch', () => {
        const { result } = renderHook(() => useActualReturns(null, null, null, false, null));
        expect(result.current.isLoadingActuals).toBe(false);
    });
});
