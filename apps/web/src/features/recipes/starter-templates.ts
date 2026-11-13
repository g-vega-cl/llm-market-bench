import starterRecipesJson from '../../../../../packages/config/starter-recipes.json';
import type { PushStrategy } from './types';

export const STARTER_RECIPES: PushStrategy[] = starterRecipesJson as PushStrategy[];
