import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { setRecipeVisibilityFn } from '../api/set-recipe-visibility';
import type { RecipeSummaryItem } from '../types';
import { useRecipeVisibility } from './use-recipe-visibility';

vi.mock('../api/set-recipe-visibility', () => ({
    setRecipeVisibilityFn: vi.fn(),
}));

const publicBot: RecipeSummaryItem = {
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

describe('useRecipeVisibility', () => {
    it('flips a public bot to private and only reports it after the server confirms', async () => {
        let confirm: (value: unknown) => void = () => {};
        vi.mocked(setRecipeVisibilityFn).mockReturnValue(
            new Promise((resolve) => {
                confirm = resolve;
            }) as never,
        );
        const onChanged = vi.fn();

        const { result } = renderHook(() => useRecipeVisibility(onChanged));

        act(() => {
            void result.current.toggle(publicBot);
        });

        expect(setRecipeVisibilityFn).toHaveBeenCalledWith({
            data: { recipeId: 'rec-1', isPublic: false },
        });
        expect(result.current.togglingId).toBe('rec-1');
        expect(onChanged).not.toHaveBeenCalled();

        await act(async () => {
            confirm({ id: 'rec-1', isPublic: false });
        });

        await waitFor(() => {
            expect(result.current.togglingId).toBeNull();
        });
        expect(onChanged).toHaveBeenCalledWith(publicBot, false);
        expect(result.current.errorMessage).toBeNull();
    });

    it('flips a private bot back to public', async () => {
        vi.mocked(setRecipeVisibilityFn).mockResolvedValue({
            id: 'rec-1',
            isPublic: true,
        } as never);
        const onChanged = vi.fn();

        const { result } = renderHook(() => useRecipeVisibility(onChanged));

        await act(async () => {
            await result.current.toggle({ ...publicBot, is_public: false });
        });

        expect(setRecipeVisibilityFn).toHaveBeenCalledWith({
            data: { recipeId: 'rec-1', isPublic: true },
        });
        expect(onChanged).toHaveBeenCalledWith({ ...publicBot, is_public: false }, true);
    });

    it('keeps the row untouched and reports the failure', async () => {
        vi.mocked(setRecipeVisibilityFn).mockRejectedValue(new Error('Unauthorized'));
        const onChanged = vi.fn();

        const { result } = renderHook(() => useRecipeVisibility(onChanged));

        await act(async () => {
            await result.current.toggle(publicBot);
        });

        expect(onChanged).not.toHaveBeenCalled();
        expect(result.current.errorMessage).toBe('Unauthorized');
        expect(result.current.togglingId).toBeNull();
    });

    it('ignores a second flip while one is in flight', async () => {
        let confirm: (value: unknown) => void = () => {};
        vi.mocked(setRecipeVisibilityFn).mockReturnValue(
            new Promise((resolve) => {
                confirm = resolve;
            }) as never,
        );
        const onChanged = vi.fn();

        const { result } = renderHook(() => useRecipeVisibility(onChanged));

        act(() => {
            void result.current.toggle(publicBot);
        });
        await act(async () => {
            await result.current.toggle({ ...publicBot, id: 'rec-2' });
        });

        expect(setRecipeVisibilityFn).toHaveBeenCalledTimes(1);
        await act(async () => {
            confirm({ id: 'rec-1', isPublic: false });
        });
    });

    it('does not fire twice when both clicks land in the same tick', async () => {
        vi.mocked(setRecipeVisibilityFn).mockResolvedValue({
            id: 'rec-1',
            isPublic: false,
        } as never);
        const onChanged = vi.fn();

        const { result } = renderHook(() => useRecipeVisibility(onChanged));

        await act(async () => {
            // React has not re-rendered between these two calls, so the state
            // guard alone would let both through.
            await Promise.all([result.current.toggle(publicBot), result.current.toggle(publicBot)]);
        });

        expect(setRecipeVisibilityFn).toHaveBeenCalledTimes(1);
        expect(onChanged).toHaveBeenCalledTimes(1);
    });
});
