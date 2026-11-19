import { describe, expect, it, vi } from 'vitest';
import { track } from './analytics';

describe('track', () => {
    it('forwards the event and props to the client', () => {
        const capture = vi.fn();
        track({ capture }, 'recipe_forked', { recipeId: 'r-1' });
        expect(capture).toHaveBeenCalledWith('recipe_forked', { recipeId: 'r-1' });
    });

    it('is a no-op without a client', () => {
        expect(() => track(null, 'builder_opened')).not.toThrow();
        expect(() => track(undefined, 'builder_compiled')).not.toThrow();
    });

    it('is a no-op without props', () => {
        const capture = vi.fn();
        track({ capture }, 'builder_declined');
        expect(capture).toHaveBeenCalledWith('builder_declined', undefined);
    });
});
