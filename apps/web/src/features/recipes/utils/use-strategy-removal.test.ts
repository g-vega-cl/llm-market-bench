import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { archiveRecipeFn } from '../api/archive-recipe';
import type { RecipeSummaryItem } from '../types';
import { useStrategyRemoval } from './use-strategy-removal';

vi.mock('../api/archive-recipe', () => ({
    archiveRecipeFn: vi.fn(),
}));

const strategy: RecipeSummaryItem = {
    id: 'rec-1',
    name: 'Quality Value Screener',
    cadence: '3h',
    is_live: false,
    is_public: true,
    trial_count: 0,
    updated_at: '2026-11-17T12:00:00.000Z',
};

beforeEach(() => {
    vi.clearAllMocks();
});

describe('useStrategyRemoval', () => {
    it('calls onRemoved only after the server confirms the hide', async () => {
        let confirm: (value: unknown) => void = () => {};
        vi.mocked(archiveRecipeFn).mockReturnValue(
            new Promise((resolve) => {
                confirm = resolve;
            }) as never,
        );
        const onRemoved = vi.fn();

        const { result } = renderHook(() => useStrategyRemoval(onRemoved));

        act(() => {
            void result.current.remove(strategy);
        });

        expect(result.current.removingId).toBe('rec-1');
        expect(onRemoved).not.toHaveBeenCalled();

        await act(async () => {
            confirm({ id: 'rec-1', archived_at: '2026-11-17T14:00:00.000Z', cancelled_jobs: 0 });
        });

        await waitFor(() => {
            expect(result.current.removingId).toBeNull();
        });
        expect(onRemoved).toHaveBeenCalledWith(strategy);
        expect(result.current.errorMessage).toBeNull();
    });

    it('keeps the list untouched and reports the failure', async () => {
        vi.mocked(archiveRecipeFn).mockRejectedValue(new Error('Unauthorized'));
        const onRemoved = vi.fn();

        const { result } = renderHook(() => useStrategyRemoval(onRemoved));

        await act(async () => {
            await result.current.remove(strategy);
        });

        expect(onRemoved).not.toHaveBeenCalled();
        expect(result.current.errorMessage).toBe('Unauthorized');
        expect(result.current.removingId).toBeNull();
    });

    it('ignores a second removal while one is in flight', async () => {
        let confirm: (value: unknown) => void = () => {};
        vi.mocked(archiveRecipeFn).mockReturnValue(
            new Promise((resolve) => {
                confirm = resolve;
            }) as never,
        );
        const onRemoved = vi.fn();

        const { result } = renderHook(() => useStrategyRemoval(onRemoved));

        act(() => {
            void result.current.remove(strategy);
        });
        await act(async () => {
            await result.current.remove({ ...strategy, id: 'rec-2' });
        });

        expect(archiveRecipeFn).toHaveBeenCalledTimes(1);
        await act(async () => {
            confirm({ id: 'rec-1', archived_at: '2026-11-17T14:00:00.000Z', cancelled_jobs: 0 });
        });
    });
});
