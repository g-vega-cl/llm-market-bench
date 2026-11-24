import { describe, expect, it } from 'vitest';

import { pendingRecipeTarget } from './pending-recipe-nav';

describe('pendingRecipeTarget', () => {
    it('reports nothing while the router is idle', () => {
        expect(
            pendingRecipeTarget('idle', { pathname: '/recipes', search: { recipeId: 'bot-1' } }),
        ).toBeNull();
    });

    it('reports a workspace navigation from the pending /build search object', () => {
        expect(
            pendingRecipeTarget('pending', { pathname: '/build', search: { recipeId: 'bot-2' } }),
        ).toEqual({ recipeId: 'bot-2', destination: 'workspace' });
    });

    it('reports a workspace navigation from a raw query string', () => {
        expect(
            pendingRecipeTarget('pending', { pathname: '/build', search: '?recipeId=bot-3' }),
        ).toEqual({ recipeId: 'bot-3', destination: 'workspace' });
    });

    it('reports a live-view navigation from the pending live path', () => {
        expect(
            pendingRecipeTarget('pending', { pathname: '/recipes/live/bot-1', search: {} }),
        ).toEqual({ recipeId: 'bot-1', destination: 'live' });
        // A stray query string must not reclassify a live-page navigation.
        expect(
            pendingRecipeTarget('pending', {
                pathname: '/recipes/live/bot-1',
                search: { recipeId: 'bot-9' },
            }),
        ).toEqual({ recipeId: 'bot-1', destination: 'live' });
    });

    it('ignores destinations that carry no recipe id', () => {
        expect(pendingRecipeTarget('pending', { pathname: '/lab', search: {} })).toBeNull();
        expect(
            pendingRecipeTarget('pending', { pathname: '/build', search: { idea: 'spy' } }),
        ).toBeNull();
    });

    it('ignores blank ids', () => {
        expect(
            pendingRecipeTarget('pending', { pathname: '/build', search: { recipeId: '  ' } }),
        ).toBeNull();
        expect(
            pendingRecipeTarget('pending', { pathname: '/build', search: '?recipeId=' }),
        ).toBeNull();
    });
});
