import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { STARTER_RECIPES } from '../starter-templates';
import { useBuilderChat } from './use-builder-chat';

vi.mock('@posthog/react', () => ({
    usePostHog: () => undefined,
}));

vi.mock('./compile-queue', async (importOriginal) => ({
    // Keep the pure helpers real (the abandon threshold is behaviour under test);
    // only the server functions are faked.
    ...(await importOriginal<typeof import('./compile-queue')>()),
    enqueueCompileFn: vi.fn(),
    fetchCompileJobFn: vi.fn(),
    cancelCompileFn: vi.fn().mockResolvedValue({ cancelled: true }),
}));

import { cancelCompileFn, enqueueCompileFn, fetchCompileJobFn } from './compile-queue';

const onNeedSignIn = vi.fn();

function wrapper({ children }: { children: React.ReactNode }) {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

function job(overrides: Record<string, unknown>) {
    return {
        id: 'job-1',
        status: 'completed',
        progress_pct: 100,
        result_json: null,
        error_message: null,
        ...overrides,
    };
}

beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(enqueueCompileFn).mockResolvedValue({ jobId: 'job-1' } as never);
});

describe('useBuilderChat (queued compiles)', () => {
    it('cancels a job no worker claims instead of counting up forever', async () => {
        vi.useFakeTimers();
        try {
            vi.mocked(fetchCompileJobFn).mockResolvedValue(
                job({ status: 'pending', progress_pct: 0 }) as never,
            );
            const { result } = renderHook(
                () => useBuilderChat({ userId: 'user-1', onNeedSignIn }),
                { wrapper },
            );

            await act(async () => {
                await result.current.send('buy chipmakers on AI capex');
            });
            await act(async () => {
                await vi.advanceTimersByTimeAsync(2_500);
            });
            expect(result.current.phase).toBe('queued');
            expect(result.current.statusDetail).toBeNull();

            await act(async () => {
                await vi.advanceTimersByTimeAsync(301_000);
            });

            expect(result.current.phase).toBe('error');
            expect(result.current.error).toMatch(/never picked this request up/i);
            expect(cancelCompileFn).toHaveBeenCalledWith({ data: { jobId: 'job-1' } });
        } finally {
            vi.useRealTimers();
        }
    });

    it('enqueues, polls, and lands a question reply in the transcript', async () => {
        vi.mocked(fetchCompileJobFn).mockResolvedValue(
            job({
                result_json: {
                    content: JSON.stringify({
                        status: 'question',
                        question: 'Which chipmakers?',
                        options: ['All', 'Large-cap'],
                    }),
                },
            }) as never,
        );

        const { result } = renderHook(() => useBuilderChat({ userId: 'user-1', onNeedSignIn }), {
            wrapper,
        });

        await act(async () => {
            await result.current.send('buy chipmakers');
        });

        await waitFor(() => expect(result.current.phase).toBe('question'));
        expect(enqueueCompileFn).toHaveBeenCalledWith({
            data: { messages: [{ role: 'user', content: 'buy chipmakers' }] },
        });
        expect(result.current.messages).toHaveLength(2);
        expect(result.current.messages[1]).toEqual({
            role: 'assistant',
            content: 'Which chipmakers?',
        });
        expect(result.current.isCompiling).toBe(false);
    });

    it('shows QUEUED while the job waits for a worker', async () => {
        vi.mocked(fetchCompileJobFn).mockResolvedValue(
            job({ status: 'pending', progress_pct: 5 }) as never,
        );

        const { result } = renderHook(() => useBuilderChat({ userId: 'user-1', onNeedSignIn }), {
            wrapper,
        });

        await act(async () => {
            await result.current.send('buy chipmakers');
        });

        await waitFor(() => expect(result.current.phase).toBe('queued'));
        expect(result.current.isCompiling).toBe(true);
    });

    it('degrades an unusable model reply to the closest template instead of dead-ending', async () => {
        vi.mocked(fetchCompileJobFn).mockResolvedValue(
            job({ result_json: { content: 'I would rather chat about it.' } }) as never,
        );

        const { result } = renderHook(() => useBuilderChat({ userId: 'user-1', onNeedSignIn }), {
            wrapper,
        });

        await act(async () => {
            await result.current.send('buy chipmakers');
        });

        await waitFor(() => expect(result.current.phase).toBe('ready'));
        const reply = result.current.reply;
        expect(reply?.status).toBe('ok');
        if (reply?.status === 'ok') {
            expect(reply.fallback).toBe(true);
            expect(reply.strategy.stages).toHaveLength(1);
        }
    });

    it('surfaces a failed job as a retryable error with no stale reply', async () => {
        vi.mocked(fetchCompileJobFn).mockResolvedValue(
            job({ status: 'failed', result_json: null, error_message: 'provider 503' }) as never,
        );

        const { result } = renderHook(() => useBuilderChat({ userId: 'user-1', onNeedSignIn }), {
            wrapper,
        });

        await act(async () => {
            await result.current.send('buy chipmakers');
        });

        await waitFor(() => expect(result.current.phase).toBe('error'));
        expect(result.current.error).toBe('provider 503');
        expect(result.current.reply).toBeNull();
    });

    it('turns an envelope-less poll into a legible failure, not a TypeError', async () => {
        vi.mocked(fetchCompileJobFn).mockResolvedValue(undefined as never);

        const { result } = renderHook(() => useBuilderChat({ userId: 'user-1', onNeedSignIn }), {
            wrapper,
        });

        await act(async () => {
            await result.current.send('buy chipmakers');
        });

        await waitFor(() => expect(result.current.phase).toBe('error'));
        expect(result.current.error).toMatch(/did not come back/i);
        expect(result.current.error).not.toMatch(/reading 'status'/);
    });

    it('rejects an enqueue refused by the daily meter', async () => {
        vi.mocked(enqueueCompileFn).mockRejectedValue(
            new Error('Daily builder limit reached (25 compiles).') as never,
        );

        const { result } = renderHook(() => useBuilderChat({ userId: 'user-1', onNeedSignIn }), {
            wrapper,
        });

        await act(async () => {
            await result.current.send('buy chipmakers');
        });

        expect(result.current.phase).toBe('error');
        expect(result.current.error).toMatch(/Daily builder limit/);
        expect(fetchCompileJobFn).not.toHaveBeenCalled();
    });

    it('latches an in-flight enqueue so a double click spends one compile', async () => {
        vi.mocked(fetchCompileJobFn).mockResolvedValue(job({ status: 'pending' }) as never);

        const { result } = renderHook(() => useBuilderChat({ userId: 'user-1', onNeedSignIn }), {
            wrapper,
        });

        await act(async () => {
            const first = result.current.send('buy chipmakers');
            const second = result.current.send('buy chipmakers');
            await Promise.all([first, second]);
        });

        expect(enqueueCompileFn).toHaveBeenCalledTimes(1);
        expect(result.current.messages).toHaveLength(1);
    });

    it('retries the last turn without appending a duplicate message', async () => {
        // Each enqueue gets its own job id (as in production), so the poll is a new query.
        vi.mocked(enqueueCompileFn)
            .mockResolvedValueOnce({ jobId: 'job-1' } as never)
            .mockResolvedValueOnce({ jobId: 'job-2' } as never);
        vi.mocked(fetchCompileJobFn).mockImplementation((async ({
            data,
        }: {
            data: { jobId: string };
        }) =>
            data.jobId === 'job-1'
                ? job({ status: 'failed', result_json: null, error_message: 'provider 503' })
                : job({
                      result_json: {
                          content: JSON.stringify({
                              status: 'ok',
                              summary: 'Chip momentum',
                              strategy: STARTER_RECIPES[0],
                          }),
                      },
                  })) as never);

        const { result } = renderHook(() => useBuilderChat({ userId: 'user-1', onNeedSignIn }), {
            wrapper,
        });

        await act(async () => {
            await result.current.send('buy chipmakers');
        });
        await waitFor(() => expect(result.current.phase).toBe('error'));

        await act(async () => {
            result.current.retry();
        });

        await waitFor(() => expect(result.current.phase).toBe('ready'));
        expect(result.current.messages).toHaveLength(1);
        expect(result.current.messages[0].content).toBe('buy chipmakers');
    });

    it('offers the closest template explicitly after a failure', async () => {
        vi.mocked(fetchCompileJobFn).mockResolvedValue(
            job({ status: 'failed', result_json: null, error_message: 'provider 503' }) as never,
        );

        const { result } = renderHook(() => useBuilderChat({ userId: 'user-1', onNeedSignIn }), {
            wrapper,
        });

        await act(async () => {
            await result.current.send('buy chipmakers');
        });
        await waitFor(() => expect(result.current.phase).toBe('error'));

        act(() => result.current.useTemplate());

        expect(result.current.error).toBeNull();
        expect(result.current.phase).toBe('ready');
        const reply = result.current.reply;
        if (reply?.status === 'ok') {
            expect(reply.strategy.name).toBe(STARTER_RECIPES[0].name);
        }
    });

    it('parks an anonymous idea and asks for sign-in instead of enqueuing', async () => {
        const { result } = renderHook(() => useBuilderChat({ userId: null, onNeedSignIn }), {
            wrapper,
        });

        await act(async () => {
            await result.current.send('buy chipmakers');
        });

        expect(enqueueCompileFn).not.toHaveBeenCalled();
        expect(onNeedSignIn).toHaveBeenCalledWith('buy chipmakers');
        expect(result.current.phase).toBe('signed-out');
    });
});
