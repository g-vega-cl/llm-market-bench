import { act, renderHook } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { STARTER_RECIPES } from '../starter-templates';
import type { PushStrategy, StrategyRecipeRecord, StrategyStage } from '../types';
import { RecipeSaveError, useRecipeDraft } from './use-recipe-draft';

function draftStrategy(overrides: Partial<PushStrategy> = {}): PushStrategy {
    return { ...STARTER_RECIPES[0], ...overrides };
}

function savedRow(name: string, id = 'rec-1'): StrategyRecipeRecord {
    return {
        id,
        name,
        cadence: '3h',
        is_live: false,
        trial_count: 0,
        updated_at: '2026-11-16T19:00:00Z',
    } as unknown as StrategyRecipeRecord;
}

function deferred<T>() {
    let resolve!: (value: T) => void;
    let reject!: (reason?: unknown) => void;
    const promise = new Promise<T>((res, rej) => {
        resolve = res;
        reject = rej;
    });
    return { promise, resolve, reject };
}

function withExtraBlock(stage: StrategyStage): StrategyStage {
    return {
        ...stage,
        blocks: [...stage.blocks, { id: 'blk-added', type: 'prompt', text: 'Added mid-save' }],
    };
}

describe('useRecipeDraft', () => {
    it('keeps an edit made while the save was in flight', async () => {
        const first = deferred<StrategyRecipeRecord>();
        const persist = vi.fn(() => first.promise);
        const { result } = renderHook(() => useRecipeDraft(draftStrategy(), null));

        act(() => result.current.setName('Saved Name'));
        const stage = result.current.strategy.stages[0];
        let savePromise: Promise<StrategyRecipeRecord> = Promise.resolve(savedRow('x'));
        act(() => {
            savePromise = result.current.save(persist);
        });

        act(() => result.current.setStage(withExtraBlock(stage)));
        expect(result.current.isSaving).toBe(true);

        await act(async () => {
            first.resolve(savedRow('Saved Name'));
            await savePromise;
        });

        expect(persist).toHaveBeenCalledTimes(1);
        expect(result.current.strategy.stages[0].blocks).toHaveLength(stage.blocks.length + 1);
        expect(result.current.isDirty).toBe(true);
        expect(result.current.saveState).toBe('idle');
        expect(result.current.strategy.id).toBe('rec-1');
        expect(result.current.isSaving).toBe(false);
    });

    it('persists the current draft when a save is requested mid-flight', async () => {
        const first = deferred<StrategyRecipeRecord>();
        const second = deferred<StrategyRecipeRecord>();
        const persist = vi
            .fn()
            .mockImplementationOnce(() => first.promise)
            .mockImplementationOnce(() => second.promise);
        const { result } = renderHook(() => useRecipeDraft(draftStrategy(), null));

        act(() => result.current.setName('First Draft'));
        const stage = result.current.strategy.stages[0];
        act(() => {
            void result.current.save(persist);
        });

        act(() => result.current.setStage(withExtraBlock(stage)));
        let chained: Promise<StrategyRecipeRecord> = Promise.resolve(savedRow('x'));
        act(() => {
            chained = result.current.save(persist);
        });

        await act(async () => {
            first.resolve(savedRow('First Draft'));
        });
        await act(async () => {
            second.resolve(savedRow('First Draft'));
            await chained;
        });

        expect(persist).toHaveBeenCalledTimes(2);
        const secondSnapshot = persist.mock.calls[1][0] as PushStrategy;
        expect(secondSnapshot.stages[0].blocks).toHaveLength(stage.blocks.length + 1);
    });

    it('ignores a response that lands after the draft was replaced by a template', async () => {
        const first = deferred<StrategyRecipeRecord>();
        const persist = vi.fn(() => first.promise);
        const { result } = renderHook(() =>
            useRecipeDraft(draftStrategy({ id: 'rec-old', name: 'Old Name' }), 'Old Name'),
        );

        act(() => result.current.setName('Renamed'));
        let savePromise: Promise<StrategyRecipeRecord> = Promise.resolve(savedRow('x'));
        act(() => {
            savePromise = result.current.save(persist);
        });

        act(() => result.current.resetTo(STARTER_RECIPES[0]));

        await act(async () => {
            first.resolve(savedRow('Renamed', 'rec-old'));
            await savePromise.catch(() => undefined);
        });

        expect(result.current.strategy.id).toBeUndefined();
        expect(result.current.strategy.name).toBe(STARTER_RECIPES[0].name);
    });

    it('rejects with RecipeSaveError and allows a retry', async () => {
        const persist = vi
            .fn()
            .mockRejectedValueOnce(new Error('Unauthorized: please sign in to save recipes'))
            .mockResolvedValueOnce(savedRow('Retried'));
        const { result } = renderHook(() => useRecipeDraft(draftStrategy(), null));

        act(() => result.current.setName('Retried'));

        let rejection: unknown;
        await act(async () => {
            rejection = await result.current.save(persist).catch((err: unknown) => err);
        });

        expect(rejection).toBeInstanceOf(RecipeSaveError);
        expect((rejection as Error).message).toBe('Unauthorized: please sign in to save recipes');
        expect(result.current.saveState).toBe('error');
        expect(result.current.isSaving).toBe(false);

        await act(async () => {
            await result.current.save(persist);
        });

        expect(persist).toHaveBeenCalledTimes(2);
        expect(result.current.strategy.id).toBe('rec-1');
        expect(result.current.saveState).toBe('saved');
    });
});
