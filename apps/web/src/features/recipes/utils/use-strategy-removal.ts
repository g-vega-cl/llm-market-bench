import { useState } from 'react';
import { archiveRecipeFn } from '../api/archive-recipe';
import type { RecipeSummaryItem } from '../types';

export interface StrategyRemoval {
    /** Strategy whose removal request is in flight, if any. */
    removingId: string | null;
    errorMessage: string | null;
    remove: (item: RecipeSummaryItem) => Promise<void>;
}

/**
 * Confirmed (non-optimistic) removal of a strategy from My Strategies.
 *
 * The list is only touched through `onRemoved`, which the caller runs after the
 * server confirms the hide; a failure leaves the list untouched and surfaces the
 * message in-flow. One removal is in flight at a time so a double click cannot
 * issue two archive calls for the same row.
 */
export function useStrategyRemoval(onRemoved: (item: RecipeSummaryItem) => void): StrategyRemoval {
    const [removingId, setRemovingId] = useState<string | null>(null);
    const [errorMessage, setErrorMessage] = useState<string | null>(null);

    const remove = async (item: RecipeSummaryItem) => {
        if (removingId) return;
        setErrorMessage(null);
        setRemovingId(item.id);
        try {
            await archiveRecipeFn({ data: { recipeId: item.id } });
            onRemoved(item);
        } catch (err) {
            setErrorMessage(err instanceof Error ? err.message : `Failed to remove "${item.name}"`);
        } finally {
            setRemovingId(null);
        }
    };

    return { removingId, errorMessage, remove };
}
