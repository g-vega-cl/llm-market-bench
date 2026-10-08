import { describe, expect, it } from 'vitest';
import { makeQueryClient } from './query-client';

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
