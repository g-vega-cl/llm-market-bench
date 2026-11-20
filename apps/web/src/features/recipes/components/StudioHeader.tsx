import { Badge } from '@llm-market-bench/ui-design-system';
import { RecipeNameField, type RecipeSaveState } from './RecipeNameField';

/**
 * Studio title block: the page heading, the strategy name field (with its
 * explicit Save button), and the one-line explanation of the push model.
 */
export function StudioHeader({
    name,
    onNameChange,
    onSave,
    isDirty,
    saveState,
    saveError,
    disabled,
}: {
    name: string;
    onNameChange: (name: string) => void;
    onSave: () => void;
    isDirty: boolean;
    saveState: RecipeSaveState;
    saveError: string | null;
    disabled?: boolean;
}) {
    return (
        <div className="flex flex-col gap-1">
            <div className="flex items-center gap-2">
                <h1 className="font-display text-sm font-bold text-voxel-ink">
                    Strategy Builder MVP
                </h1>
                <Badge variant="soft" size="sm">
                    5-Block Push v2
                </Badge>
            </div>
            <RecipeNameField
                value={name}
                onChange={onNameChange}
                onSave={onSave}
                isDirty={isDirty}
                saveState={saveState}
                errorMessage={saveError}
                disabled={disabled}
            />
            <p className="text-xs font-normal text-voxel-muted">
                Compose Prompt, News, Memories, Technicals, and Output Format blocks into a single
                Long-Only LLM call (runs every 30m during market hours 09:30–16:00 ET).
            </p>
        </div>
    );
}
