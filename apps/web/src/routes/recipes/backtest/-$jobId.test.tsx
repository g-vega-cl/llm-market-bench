import { describe, expect, it, vi } from 'vitest';
import { Route } from './$jobId';

vi.mock('~/features/recipes/pages/RecipeBacktestPage', () => ({
    RecipeBacktestPage: () => null,
}));

type HeadTag = { name?: string; content?: string; title?: string };

describe('Recipe Backtest route', () => {
    it('configures SEO metadata for the live backtest run page', () => {
        const head = Route.options.head as unknown as () => { meta: HeadTag[] };
        const description = head().meta.find((tag) => tag.name === 'description')?.content;
        expect(description).toMatch(/^Live day-by-day point-in-time backtest telemetry/);
    });
});
