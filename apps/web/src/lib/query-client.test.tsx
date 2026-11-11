import { describe, expect, it } from 'vitest';
import { isQuerySettled, makeQueryClient } from './query-client';

describe('isQuerySettled helper', () => {
    it('returns true when all queries are fetched, not fetching, not pending, and not placeholder', () => {
        const query1 = {
            data: [{ id: 1 }],
            isFetched: true,
            isFetching: false,
            isPending: false,
            isPlaceholderData: false,
        };
        const query2 = { data: 'ok', isFetched: true, isFetching: false };
        expect(isQuerySettled([query1, query2])).toBe(true);
        expect(isQuerySettled(query1)).toBe(true);
    });

    it('returns false for errored queries without valid data', () => {
        const erroredQuery = {
            data: undefined,
            isFetched: true,
            isFetching: false,
            isPending: false,
            isSuccess: false,
            isError: true,
        };
        expect(isQuerySettled(erroredQuery)).toBe(false);
    });

    it('returns true for hydrated query with initialData (isSuccess: true, data present, not fetching)', () => {
        const hydratedQuery = {
            data: [{ id: 'p1' }],
            isSuccess: true,
            isFetched: false,
            isFetching: false,
            isPending: false,
        };
        expect(isQuerySettled(hydratedQuery)).toBe(true);
    });

    it('returns false if any query is not yet fetched', () => {
        const q1 = { isFetched: false, isFetching: true, isPending: true };
        expect(isQuerySettled(q1)).toBe(false);
    });

    it('returns false if any query is actively fetching/refetching', () => {
        const q1 = { isFetched: true, isFetching: true, isPending: false };
        expect(isQuerySettled(q1)).toBe(false);
    });

    it('returns false if any query is pending or placeholderData', () => {
        const q1 = { isFetched: true, isFetching: false, isPlaceholderData: true };
        const q2 = { isFetched: true, isFetching: false, isPending: true };
        expect(isQuerySettled(q1)).toBe(false);
        expect(isQuerySettled(q2)).toBe(false);
    });

    it('returns false if isTransitionPending is true even if queries are fetched', () => {
        const q1 = { isFetched: true, isFetching: false, isPending: false };
        expect(isQuerySettled([q1], true)).toBe(false);
    });

    it('returns false if a query in the list is null or undefined', () => {
        expect(isQuerySettled([null])).toBe(false);
        expect(isQuerySettled([undefined])).toBe(false);
    });

    it('returns true for an empty query list when transition is not pending', () => {
        expect(isQuerySettled([])).toBe(true);
    });
});

describe('makeQueryClient configuration', () => {
    it('initializes query client with exponential backoff and jitter', () => {
        const client = makeQueryClient();
        const queries = client.getDefaultOptions().queries;

        expect(queries?.staleTime).toBe(60000);
        expect(queries?.refetchOnReconnect).toBe(true);

        // Test retry logic
        const retryFn = queries?.retry as (count: number, error: unknown) => boolean;
        expect(retryFn(1, new Error('Network timeout'))).toBe(true);
        expect(retryFn(2, new Error('Network timeout'))).toBe(true);
        expect(retryFn(3, new Error('Network timeout'))).toBe(false);

        // Skips 4xx errors
        expect(retryFn(0, new Error('Request failed with 404 Not Found'))).toBe(false);
        expect(retryFn(0, new Error('Unauthorized 401'))).toBe(false);
        expect(retryFn(0, new Error('Forbidden 403'))).toBe(false);
        expect(retryFn(0, new Error('Bad Request 400'))).toBe(false);

        // Test retryDelay function with backoff and jitter bounds
        const retryDelayFn = queries?.retryDelay as (attemptIndex: number) => number;
        const delay0 = retryDelayFn(0);
        expect(delay0).toBeGreaterThanOrEqual(1000);
        expect(delay0).toBeLessThanOrEqual(1500);

        const delay1 = retryDelayFn(1);
        expect(delay1).toBeGreaterThanOrEqual(2000);
        expect(delay1).toBeLessThanOrEqual(2500);

        const delay2 = retryDelayFn(2);
        expect(delay2).toBeGreaterThanOrEqual(4000);
        expect(delay2).toBeLessThanOrEqual(4500);
    });
});
