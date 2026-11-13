import { describe, expect, it, vi } from 'vitest';
import { Route } from './index';

vi.mock('~/features/recipes/pages/RecipeStudioPage', () => ({
    RecipeStudioPage: () => null,
}));

type HeadTag = { name?: string; content?: string; title?: string };

describe('Recipe Studio route', () => {
    it('describes the single-call strategy builder in its SEO metadata', () => {
        const head = Route.options.head as unknown as () => { meta: HeadTag[] };

        const description = head().meta.find((tag) => tag.name === 'description')?.content;

        expect(description).toMatch(/^Single-call 5-block push strategy builder/);
    });
});
