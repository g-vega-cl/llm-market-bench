import { afterEach, describe, expect, it, vi } from 'vitest';
import {
    attemptBudget,
    BUILDER_BUDGET_MS,
    BUILDER_MIN_RETRY_MS,
    compileStrategy,
    failureText,
    isTimeoutFailure,
} from './compiler-api';

vi.mock('~/lib/auth', () => ({
    getAuthServerClient: () => ({ auth: { getUser: vi.fn() } }),
}));

vi.mock('~/lib/db', () => ({
    getDbAdminClient: () => ({ rpc: vi.fn() }),
}));

afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
});

const conversation = [{ role: 'user' as const, content: 'buy chipmakers on ai capex news' }];

const timeoutError = () => new DOMException('The operation timed out.', 'TimeoutError');

describe('compile budget', () => {
    it('stays inside the measured origin ceiling that used to return a 502', () => {
        // Measured on production, same endpoint: replies at 19.9s/25.9s/27.8s,
        // Cloudflare 502 origin_bad_gateway at 30.1s. The budget has to leave
        // margin under that ceiling for the handler, seroval and the network.
        expect(BUILDER_BUDGET_MS).toBeLessThan(28_000);
        expect(BUILDER_BUDGET_MS).toBeGreaterThan(20_000);
        expect(BUILDER_MIN_RETRY_MS).toBeLessThan(BUILDER_BUDGET_MS);
    });

    it('spends no retry window when the budget is nearly gone', () => {
        expect(attemptBudget(BUILDER_BUDGET_MS)).toBe(BUILDER_BUDGET_MS);
        expect(attemptBudget(BUILDER_MIN_RETRY_MS)).toBe(BUILDER_MIN_RETRY_MS);
        expect(attemptBudget(BUILDER_MIN_RETRY_MS - 1)).toBe(0);
        expect(attemptBudget(0)).toBe(0);
    });

    it('degrades straight to a working template on a timeout, without a futile retry', async () => {
        const fetchMock = vi.fn().mockRejectedValue(timeoutError());
        vi.stubGlobal('fetch', fetchMock);

        const reply = await compileStrategy(conversation);

        expect(fetchMock).toHaveBeenCalledTimes(1);
        expect(reply.status).toBe('ok');
        if (reply.status === 'ok') {
            expect(reply.fallback).toBe(true);
            expect(reply.summary).toMatch(/too slow/i);
            expect(reply.strategy.stages).toHaveLength(1);
        }
    });

    it('still retries a cheap failure: a provider error is worth a second attempt', async () => {
        const fetchMock = vi.fn().mockRejectedValue(new Error('Builder model call failed (503)'));
        vi.stubGlobal('fetch', fetchMock);

        const reply = await compileStrategy(conversation);

        expect(fetchMock).toHaveBeenCalledTimes(2);
        expect(reply.status).toBe('ok');
        if (reply.status === 'ok') {
            expect(reply.fallback).toBe(true);
            expect(reply.summary).not.toMatch(/too slow/i);
        }
    });

    it('bounds every provider call with an abort signal instead of holding the request open', async () => {
        const fetchMock = vi.fn().mockRejectedValue(new Error('Builder model call failed (500)'));
        vi.stubGlobal('fetch', fetchMock);

        await compileStrategy(conversation);

        for (const call of fetchMock.mock.calls) {
            expect(call[1]?.signal).toBeInstanceOf(AbortSignal);
        }
    });

    it('returns the model reply when the first attempt succeeds', async () => {
        const fetchMock = vi.fn().mockResolvedValue({
            ok: true,
            json: async () => ({
                choices: [
                    {
                        message: {
                            content: JSON.stringify({
                                status: 'question',
                                question: 'Which chipmakers?',
                                options: ['All', 'Large-cap'],
                            }),
                        },
                    },
                ],
            }),
        });
        vi.stubGlobal('fetch', fetchMock);

        const reply = await compileStrategy(conversation);

        expect(fetchMock).toHaveBeenCalledTimes(1);
        expect(reply).toEqual({
            status: 'question',
            question: 'Which chipmakers?',
            options: ['All', 'Large-cap'],
        });
    });
});

describe('failure classification', () => {
    it('recognises an abort that is not an Error instance', () => {
        const abort = timeoutError();
        expect(abort).not.toBeInstanceOf(Error);
        expect(failureText(abort)).toBe('The operation timed out.');
        expect(isTimeoutFailure(failureText(abort))).toBe(true);
    });

    it('does not mistake a provider 5xx for a timeout', () => {
        expect(isTimeoutFailure('Builder model call failed (503)')).toBe(false);
        expect(failureText(new Error('boom'))).toBe('boom');
        expect(failureText('plain string')).toBe('plain string');
    });
});
