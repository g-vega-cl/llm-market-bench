import { describe, expect, it, vi } from 'vitest';
import { Route } from './recipes-demo';

vi.mock('~/features/recipes/pages/RecipeBacktestPage', () => ({
    RecipeBacktestPage: () => null,
}));

type HeadTag = { name?: string; content?: string; title?: string };

describe('Recipe Showcase Demo route', () => {
    it('configures public preview SEO metadata', () => {
        const head = Route.options.head as unknown as () => { meta: HeadTag[] };
        const description = head().meta.find((tag) => tag.name === 'description')?.content;
        expect(description).toMatch(/^Read-only walkthrough of a 30-slot point-in-time/);
    });
});
