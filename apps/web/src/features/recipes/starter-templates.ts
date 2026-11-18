import starterRecipesJson from '../../../../../packages/config/starter-recipes.json';
import type { PushStrategy } from './types';

const rawRecipes = starterRecipesJson as unknown as PushStrategy[];

/** `seed_starter_recipes` keys template identity on `name`, so duplicates collapse. */
function assertUniqueTemplateNames(recipes: PushStrategy[]): void {
    const seen = new Set<string>();
    for (const recipe of recipes) {
        if (seen.has(recipe.name)) {
            throw new Error(
                `Duplicate starter recipe name "${recipe.name}" in starter-recipes.json`,
            );
        }
        seen.add(recipe.name);
    }
}

assertUniqueTemplateNames(rawRecipes);

export const STARTER_RECIPES: PushStrategy[] = rawRecipes.map((recipe) => {
    if (recipe.stages.length !== 1) {
        throw new Error(`Starter recipe "${recipe.name}" must contain exactly one LLM stage`);
    }
    return recipe;
});
