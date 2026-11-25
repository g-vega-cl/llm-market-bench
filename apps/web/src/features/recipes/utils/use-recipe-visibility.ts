import { useRef, useState } from 'react';
import { setRecipeVisibilityFn } from '../api/set-recipe-visibility';
import type { RecipeSummaryItem } from '../types';

export interface RecipeVisibilityToggle {
    /** Bot whose visibility request is in flight, if any. */
    togglingId: string | null;
    errorMessage: string | null;
    /** Flips the bot to the opposite of its current visibility. */
    toggle: (item: RecipeSummaryItem) => Promise<void>;
}

/**
 * Confirmed (non-optimistic) public/private flip for a bot.
 *
 * The list is only touched through `onChanged`, which the caller runs with the
 * state the server returned — never with the state the click intended, so two
 * tabs racing cannot paint a lie. A failure leaves the row untouched and
 * surfaces the message in-flow.
 */
export function useRecipeVisibility(
    onChanged: (item: RecipeSummaryItem, isPublic: boolean) => void,
): RecipeVisibilityToggle {
    const [togglingId, setTogglingId] = useState<string | null>(null);
    const [errorMessage, setErrorMessage] = useState<string | null>(null);
    // A ref, not the state value: two clicks in the same tick both read the
    // stale `togglingId` and would otherwise fire two writes.
    const inFlight = useRef<string | null>(null);

    const toggle = async (item: RecipeSummaryItem) => {
        if (inFlight.current) return;
        inFlight.current = item.id;
        setErrorMessage(null);
        setTogglingId(item.id);
        try {
            const result = await setRecipeVisibilityFn({
                data: { recipeId: item.id, isPublic: !item.is_public },
            });
            onChanged(item, result.isPublic);
        } catch (err) {
            setErrorMessage(
                err instanceof Error
                    ? err.message
                    : `Failed to change visibility of "${item.name}"`,
            );
        } finally {
            inFlight.current = null;
            setTogglingId(null);
        }
    };

    return { togglingId, errorMessage, toggle };
}
