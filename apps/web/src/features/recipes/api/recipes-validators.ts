import recipeNamingJson from '../../../../../../packages/config/recipe-naming.json';
import type { StrategyStage } from '../types';

const PREV_OUTPUT_PLACEHOLDER = '{{prev_output}}';

interface RecipeNaming {
    defaultName: string;
    nameMaxLength: number;
}

// Shared with apps/engine/recipes/push_schema.py so the two sides cannot drift.
export const { defaultName: DEFAULT_RECIPE_NAME, nameMaxLength: RECIPE_NAME_MAX_LENGTH } =
    recipeNamingJson as RecipeNaming;

/**
 * Single source of truth for the persisted recipe name. The DB column is
 * `TEXT NOT NULL`, so a blank or missing name must never reach the insert.
 */
export function normalizeRecipeName(name: string | null | undefined): string {
    return name?.trim().slice(0, RECIPE_NAME_MAX_LENGTH) || DEFAULT_RECIPE_NAME;
}

export function assertSingleLlmStage(recipe: { stages: readonly StrategyStage[] }): void {
    if (!Array.isArray(recipe.stages) || recipe.stages.length !== 1) {
        throw new Error('Invalid strategy: must contain exactly one LLM stage');
    }
}

export function assertNoPrevOutputPlaceholder(recipe: { stages: readonly StrategyStage[] }): void {
    for (const stage of recipe.stages ?? []) {
        for (const block of stage.blocks ?? []) {
            if (block.type === 'prompt' && block.text.includes(PREV_OUTPUT_PLACEHOLDER)) {
                throw new Error(
                    'Invalid strategy: prev_output is not available in a single-stage strategy',
                );
            }
        }
    }
}
