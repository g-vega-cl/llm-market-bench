import { Button } from '@llm-market-bench/ui-design-system';
import type { RecipeSummaryItem } from '../types';

interface LiveSwitchConfirmationProps {
    /** The recipe that is currently live (the one being switched away from). */
    conflictingRecipe: RecipeSummaryItem;
    /** The name of the recipe the user is trying to enable live. */
    targetRecipeName: string;
    /** Whether the switch operation is in flight. */
    isSwitching: boolean;
    onConfirm: () => void;
    onCancel: () => void;
}

/**
 * Inline confirmation trough shown when the user tries to enable live on a
 * recipe while another recipe is already live. Enforces the max_live_recipes=1
 * quota by making the switch explicit.
 *
 * Design-spec §10: no modals — this renders in-flow as a recessed voxel trough.
 */
export function LiveSwitchConfirmation({
    conflictingRecipe,
    targetRecipeName,
    isSwitching,
    onConfirm,
    onCancel,
}: LiveSwitchConfirmationProps) {
    return (
        <div
            role="alert"
            className="voxel-trough bg-voxel-trough p-3 flex flex-wrap items-center justify-between gap-3 text-xs font-normal text-voxel-ink rounded-none min-w-0"
        >
            <span className="min-w-0 break-words">
                <span className="font-bold text-warning">⚠</span>{' '}
                <span className="font-bold">{conflictingRecipe.name}</span> is currently live (30m).
                Enable live for <span className="font-bold">{targetRecipeName}</span> instead?
            </span>
            <div className="flex flex-wrap items-center gap-2 shrink-0">
                <Button
                    size="sm"
                    variant="solid"
                    onClick={onConfirm}
                    disabled={isSwitching}
                    isLoading={isSwitching}
                >
                    Switch to This
                </Button>
                <Button
                    size="sm"
                    variant="outline"
                    colorScheme="neutral"
                    onClick={onCancel}
                    disabled={isSwitching}
                >
                    Keep {conflictingRecipe.name}
                </Button>
            </div>
        </div>
    );
}
