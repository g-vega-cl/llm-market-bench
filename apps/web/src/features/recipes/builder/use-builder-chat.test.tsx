import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { STARTER_RECIPES } from '../starter-templates';
import { useBuilderChat } from './use-builder-chat';

vi.mock('@posthog/react', () => ({
    usePostHog: () => undefined,
}));

vi.mock('./compiler-api', () => ({
    compileStrategyFn: vi.fn(),
}));

import { compileStrategyFn } from './compiler-api';

const onNeedSignIn = vi.fn();

beforeEach(() => {
    vi.clearAllMocks();
});

describe('useBuilderChat', () => {
    it('turns an envelope-less reply into a retryable failure, not a TypeError', async () => {
        // The transport resolves to undefined when the response is not a reply
        // envelope (an edge 502, a cut-off request) — the old code then threw
        // "Cannot read properties of undefined (reading 'status')".
        vi.mocked(compileStrategyFn).mockResolvedValue(undefined as never);

        const { result } = renderHook(() => useBuilderChat({ userId: 'user-1', onNeedSignIn }));

        await act(async () => {
            await result.current.send('buy chipmakers on ai capex news');
        });

        expect(result.current.phase).toBe('error');
        expect(result.current.error).toMatch(/request was cut off/i);
        expect(result.current.error).not.toMatch(/reading 'status'/);
        expect(result.current.reply).toBeNull();
        expect(result.current.isCompiling).toBe(false);
        expect(result.current.messages).toHaveLength(1);
    });

    it('retries the last turn without appending a duplicate message', async () => {
        vi.mocked(compileStrategyFn)
            .mockResolvedValueOnce(undefined as never)
            .mockResolvedValueOnce({
                status: 'ok',
                strategy: STARTER_RECIPES[0],
                summary: 'Chip momentum',
            } as never);

        const { result } = renderHook(() => useBuilderChat({ userId: 'user-1', onNeedSignIn }));

        await act(async () => {
            await result.current.send('buy chipmakers');
        });
        expect(result.current.phase).toBe('error');

        await act(async () => {
            result.current.retry();
        });

        await waitFor(() => expect(result.current.phase).toBe('ready'));
        expect(result.current.messages).toHaveLength(1);
        expect(result.current.messages[0].content).toBe('buy chipmakers');
    });

    it('treats a question reply without an options array as malformed, not as a crash', async () => {
        vi.mocked(compileStrategyFn).mockResolvedValue({
            status: 'question',
            question: 'Which chipmakers?',
            options: undefined,
        } as never);

        const { result } = renderHook(() => useBuilderChat({ userId: 'user-1', onNeedSignIn }));

        await act(async () => {
            await result.current.send('buy chipmakers');
        });

        expect(result.current.phase).toBe('error');
        expect(result.current.error).toMatch(/cut off/i);
        expect(result.current.messages).toHaveLength(1);
    });

    it('latches an in-flight compile so a double click cannot spend two compiles', async () => {
        let release: (value: unknown) => void = () => undefined;
        vi.mocked(compileStrategyFn).mockImplementation(
            () =>
                new Promise((resolve) => {
                    release = resolve;
                }) as never,
        );

        const { result } = renderHook(() => useBuilderChat({ userId: 'user-1', onNeedSignIn }));

        await act(async () => {
            const first = result.current.send('buy chipmakers');
            const second = result.current.send('buy chipmakers');
            release({
                status: 'ok',
                strategy: STARTER_RECIPES[0],
                summary: 'Chip momentum',
            });
            await Promise.all([first, second]);
        });

        expect(compileStrategyFn).toHaveBeenCalledTimes(1);
        expect(result.current.messages).toHaveLength(1);
    });

    it('parks an anonymous idea and asks for sign-in instead of compiling', async () => {
        const { result } = renderHook(() => useBuilderChat({ userId: null, onNeedSignIn }));

        await act(async () => {
            await result.current.send('buy chipmakers');
        });

        expect(compileStrategyFn).not.toHaveBeenCalled();
        expect(onNeedSignIn).toHaveBeenCalledWith('buy chipmakers');
        expect(result.current.phase).toBe('signed-out');
    });
});
