import { describe, expect, it } from 'vitest';
import recipeNamingJson from '../../../../../../packages/config/recipe-naming.json';
import {
    DEFAULT_RECIPE_NAME,
    normalizeRecipeName,
    RECIPE_NAME_MAX_LENGTH,
} from './recipes-validators';

describe('normalizeRecipeName', () => {
    it('keeps the shared naming contract in sync with packages/config', () => {
        expect(DEFAULT_RECIPE_NAME).toBe(recipeNamingJson.defaultName);
        expect(RECIPE_NAME_MAX_LENGTH).toBe(recipeNamingJson.nameMaxLength);
    });

    it('trims surrounding whitespace', () => {
        expect(normalizeRecipeName('  Momentum Rotation  ')).toBe('Momentum Rotation');
    });

    it('falls back to the default for blank, null, and undefined names', () => {
        expect(normalizeRecipeName('')).toBe(DEFAULT_RECIPE_NAME);
        expect(normalizeRecipeName('   ')).toBe(DEFAULT_RECIPE_NAME);
        expect(normalizeRecipeName(null)).toBe(DEFAULT_RECIPE_NAME);
        expect(normalizeRecipeName(undefined)).toBe(DEFAULT_RECIPE_NAME);
    });

    it('caps the name at the shared maximum length', () => {
        expect(normalizeRecipeName('x'.repeat(RECIPE_NAME_MAX_LENGTH + 20))).toHaveLength(
            RECIPE_NAME_MAX_LENGTH,
        );
    });
});
