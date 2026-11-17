import { Button, Input, Label } from '@llm-market-bench/ui-design-system';
import { useId } from 'react';
import { RECIPE_NAME_MAX_LENGTH } from '../api/recipes-validators';

export type RecipeSaveState = 'idle' | 'saving' | 'saved' | 'error';

interface RecipeNameFieldProps {
    value: string;
    onChange: (value: string) => void;
    onSave: () => void;
    isDirty: boolean;
    saveState: RecipeSaveState;
    errorMessage?: string | null;
    disabled?: boolean;
}

function resolveSaveLabel(isDirty: boolean, saveState: RecipeSaveState): string {
    if (saveState === 'saving') return 'Saving...';
    if (saveState === 'saved' && !isDirty) return 'Saved';
    return 'Save Recipe';
}

/**
 * Explicit rename + save surface for the studio header.
 *
 * The button is the only explicit way to persist a name or graph edit; running
 * a recipe still persists the current draft as a side effect of queueing a job.
 */
export function RecipeNameField({
    value,
    onChange,
    onSave,
    isDirty,
    saveState,
    errorMessage = null,
    disabled = false,
}: RecipeNameFieldProps) {
    const inputId = useId();
    const errorId = `${inputId}-error`;
    const isError = saveState === 'error' && Boolean(errorMessage);

    return (
        <div className="flex flex-wrap items-end gap-2 min-w-0">
            <div className="flex flex-col gap-1 min-w-0">
                <Label htmlFor={inputId}>Recipe Name</Label>
                <Input
                    id={inputId}
                    type="text"
                    value={value}
                    onChange={(e) => onChange(e.target.value)}
                    placeholder="Name this strategy"
                    maxLength={RECIPE_NAME_MAX_LENGTH}
                    isError={isError}
                    aria-invalid={isError}
                    aria-describedby={isError ? errorId : undefined}
                    disabled={disabled}
                />
            </div>
            <Button
                size="sm"
                variant="outline"
                onClick={onSave}
                disabled={!isDirty || disabled || saveState === 'saving'}
                isLoading={saveState === 'saving'}
            >
                {resolveSaveLabel(isDirty, saveState)}
            </Button>
            <span role="status" aria-live="polite" className="sr-only">
                {saveState === 'saving' ? 'Saving recipe' : null}
                {saveState === 'saved' && !isDirty ? 'Recipe saved' : null}
            </span>
            {isError && (
                <span id={errorId} role="alert" className="text-xs font-normal text-danger">
                    {errorMessage}
                </span>
            )}
        </div>
    );
}
