import { describe, expect, it, vi } from 'vitest';

const mockFetchShowcase = vi.fn();
vi.mock('~/features/recipes/api/recipes-quota-api', () => ({
    fetchPublicShowcaseBacktestFn: () => mockFetchShowcase(),
}));

vi.mock('~/features/recipes/pages/RecipeBacktestPage', () => ({
    RecipeBacktestPage: () => null,
}));

import { Route } from './recipes-demo';

type HeadTag = { name?: string; content?: string; title?: string };
type Loader = () => Promise<{ job: { id: string } } | null>;

describe('Recipe Showcase Demo route', () => {
    it('configures public preview SEO metadata', () => {
        const head = Route.options.head as unknown as () => { meta: HeadTag[] };
        const description = head().meta.find((tag) => tag.name === 'description')?.content;
        expect(description).toMatch(/^Read-only walkthrough of a 30-slot point-in-time/);
    });

    it('loads the pinned showcase backtest for the read-only page', async () => {
        mockFetchShowcase.mockResolvedValueOnce({
            job: { id: 'job-pinned' },
            recipeName: 'News momentum, long-only',
            recipeCadence: '3h',
        });
        const loader = Route.options.loader as unknown as Loader;

        const data = await loader();

        expect(data?.job.id).toBe('job-pinned');
    });

    it('degrades to the sign-in card when no showcase is published', async () => {
        mockFetchShowcase.mockRejectedValueOnce(new Error('showcase unavailable'));
        const loader = Route.options.loader as unknown as Loader;

        await expect(loader()).resolves.toBeNull();
    });
});
