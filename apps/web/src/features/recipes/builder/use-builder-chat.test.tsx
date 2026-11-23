import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { STARTER_RECIPES } from '../starter-templates';
import { useBuilderChat } from './use-builder-chat';

const posthogCapture = vi.fn();

vi.mock('@posthog/react', () => ({
    usePostHog: () => ({ capture: posthogCapture }),
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
            expect(
                posthogCapture.mock.calls
                    .filter(([event]) => event === 'builder_failed')
                    .at(-1)?.[1],
            ).toMatchObject({ reason_code: 'abandoned' });
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

    it('reports a failed job under a short reason code, keeping the message', async () => {
        vi.mocked(fetchCompileJobFn).mockResolvedValue(
            job({
                status: 'failed',
                result_json: null,
                error_message: 'The model took too long to answer. Try again.',
            }) as never,
        );
        const { result } = renderHook(() => useBuilderChat({ userId: 'user-1', onNeedSignIn }), {
            wrapper,
        });

        await act(async () => {
            await result.current.send('buy chipmakers');
        });

        await waitFor(() => expect(result.current.phase).toBe('error'));
        const [, props] = posthogCapture.mock.calls
            .filter(([event]) => event === 'builder_failed')
            .at(-1) as [string, Record<string, unknown>];
        expect(props.reason_code).toBe('job_failed');
        expect(props.reason).toMatch(/too long/);
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

    it('starts a clean user-led conversation when refining after a declined reply', async () => {
        vi.mocked(fetchCompileJobFn)
            .mockResolvedValueOnce(
                job({
                    result_json: {
                        content: JSON.stringify({
                            status: 'declined',
                            reason: 'Shorting is not supported.',
                            closest: 'Long-only chipmaker rotation.',
                        }),
                    },
                }) as never,
            )
            .mockResolvedValueOnce(
                job({
                    result_json: {
                        content: JSON.stringify({
                            status: 'question',
                            question: 'Which tickers?',
                            options: ['NVDA', 'AMD'],
                        }),
                    },
                }) as never,
            );

        const { result } = renderHook(() => useBuilderChat({ userId: 'user-1', onNeedSignIn }), {
            wrapper,
        });

        await act(async () => {
            await result.current.send('short chipmakers');
        });
        await waitFor(() => expect(result.current.phase).toBe('declined'));

        await act(async () => {
            await result.current.send('long chipmakers only');
        });

        expect(enqueueCompileFn).toHaveBeenLastCalledWith({
            data: { messages: [{ role: 'user', content: 'long chipmakers only' }] },
        });
    });

    it('lands an alignment round and submits formatted answers to compile the final bot', async () => {
        vi.mocked(enqueueCompileFn)
            .mockResolvedValueOnce({ jobId: 'job-align-1' } as never)
            .mockResolvedValueOnce({ jobId: 'job-align-2' } as never);
        vi.mocked(fetchCompileJobFn)
            .mockResolvedValueOnce(
                job({
                    result_json: {
                        content: JSON.stringify({
                            status: 'align',
                            intro: 'Let us align on 3 quick choices.',
                            questions: [
                                { id: 'q1', question: 'Sector?', options: ['Semis', 'Software'] },
                                { id: 'q2', question: 'Entry?', options: ['News', 'RSI < 35'] },
                                { id: 'q3', question: 'Exit?', options: ['Target', 'Trail'] },
                            ],
                        }),
                    },
                }) as never,
            )
            .mockResolvedValueOnce(
                job({
                    result_json: {
                        content: JSON.stringify({
                            status: 'ok',
                            summary: 'Compiled aligned chip bot.',
                            strategy: STARTER_RECIPES[0],
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
        await waitFor(() => expect(result.current.phase).toBe('align'));
        expect(result.current.messages).toHaveLength(2);
        expect(result.current.messages[1].content).toContain('1. Sector?');

        await act(async () => {
            await result.current.submitAlignment([
                { question: 'Sector?', answer: 'Semis' },
                { question: 'Entry?', answer: 'News' },
                { question: 'Exit?', answer: 'Target' },
            ]);
        });

        await waitFor(() => expect(result.current.phase).toBe('ready'));
        expect(enqueueCompileFn).toHaveBeenLastCalledWith({
            data: {
                messages: [
                    { role: 'user', content: 'buy chipmakers' },
                    {
                        role: 'assistant',
                        content: expect.stringContaining('1. Sector?'),
                    },
                    {
                        role: 'user',
                        content: expect.stringContaining('- Sector?: Semis'),
                    },
                ],
            },
        });
    });

    it('preserves activeAlignment on compile failure and replaces failed trailing user turn on resubmit', async () => {
        vi.mocked(enqueueCompileFn)
            .mockResolvedValueOnce({ jobId: 'job-a1' } as never)
            .mockRejectedValueOnce(new Error('provider busy') as never)
            .mockResolvedValueOnce({ jobId: 'job-a2' } as never);
        vi.mocked(fetchCompileJobFn)
            .mockResolvedValueOnce(
                job({
                    result_json: {
                        content: JSON.stringify({
                            status: 'align',
                            questions: [
                                { id: 'q1', question: 'Sector?', options: ['Semis', 'Cloud'] },
                                { id: 'q2', question: 'Entry?', options: ['News', 'RSI < 35'] },
                                { id: 'q3', question: 'Exit?', options: ['Target', 'Trail'] },
                            ],
                        }),
                    },
                }) as never,
            )
            .mockResolvedValueOnce(
                job({
                    result_json: {
                        content: JSON.stringify({
                            status: 'ok',
                            summary: 'Compiled aligned bot.',
                            strategy: STARTER_RECIPES[0],
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
        await waitFor(() => expect(result.current.phase).toBe('align'));

        await act(async () => {
            await result.current.submitAlignment([
                { question: 'Sector?', answer: 'Semis' },
                { question: 'Entry?', answer: 'News' },
                { question: 'Exit?', answer: 'Target' },
            ]);
        });

        await waitFor(() => expect(result.current.phase).toBe('error'));
        expect(result.current.activeAlignment?.questions).toHaveLength(3);

        await act(async () => {
            await result.current.submitAlignment([
                { question: 'Sector?', answer: 'Cloud' },
                { question: 'Entry?', answer: 'RSI < 35' },
                { question: 'Exit?', answer: 'Trail' },
            ]);
        });

        await waitFor(() => expect(result.current.phase).toBe('ready'));
        expect(result.current.activeAlignment).toBeNull();
        expect(enqueueCompileFn).toHaveBeenLastCalledWith({
            data: {
                messages: [
                    { role: 'user', content: 'buy chipmakers' },
                    { role: 'assistant', content: expect.stringContaining('1. Sector?') },
                    { role: 'user', content: expect.stringContaining('- Sector?: Cloud') },
                ],
            },
        });
    });

    it('guards against a second alignment round by degrading to a runnable template', async () => {
        const alignContent = JSON.stringify({
            status: 'align',
            questions: [
                { id: 'q1', question: 'Sector?', options: ['Semis', 'Cloud'] },
                { id: 'q2', question: 'Entry?', options: ['News', 'RSI < 35'] },
                { id: 'q3', question: 'Exit?', options: ['Target', 'Trail'] },
            ],
        });
        vi.mocked(enqueueCompileFn)
            .mockResolvedValueOnce({ jobId: 'job-loop-1' } as never)
            .mockResolvedValueOnce({ jobId: 'job-loop-2' } as never);
        vi.mocked(fetchCompileJobFn).mockResolvedValue(
            job({ result_json: { content: alignContent } }) as never,
        );

        const { result } = renderHook(() => useBuilderChat({ userId: 'user-1', onNeedSignIn }), {
            wrapper,
        });

        await act(async () => {
            await result.current.send('buy chipmakers');
        });
        await waitFor(() => expect(result.current.phase).toBe('align'));

        await act(async () => {
            await result.current.submitAlignment([
                { question: 'Sector?', answer: 'Semis' },
                { question: 'Entry?', answer: 'News' },
                { question: 'Exit?', answer: 'Target' },
            ]);
        });

        await waitFor(() => expect(result.current.phase).toBe('ready'));
        expect(result.current.reply?.status).toBe('ok');
    });
});
