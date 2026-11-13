import starterRecipesJson from '../../../../../packages/config/starter-recipes.json';
import type { PushStrategy } from './types';

const rawRecipes = starterRecipesJson as unknown as PushStrategy[];

export const STARTER_RECIPES: PushStrategy[] = rawRecipes.map((recipe) => {
    if (recipe.stages.length !== 1) {
        throw new Error(`Starter recipe "${recipe.name}" must contain exactly one LLM stage`);
    }
    return recipe;
});
