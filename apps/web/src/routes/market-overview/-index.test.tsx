import { beforeEach, describe, expect, it, vi } from 'vitest';

const fetchMarketOverviewData = vi.fn().mockResolvedValue({ correlationData: [] });

vi.mock('~/features/market-overview/api/fetch-market-overview', () => ({
    fetchMarketOverviewData: (limit?: number) => fetchMarketOverviewData(limit),
}));
vi.mock('~/features/market-overview/pages/MarketOverviewPage', () => ({
    MarketOverviewPage: () => null,
}));
vi.mock('@tanstack/react-router', () => ({
    createFileRoute: () => (config: Record<string, unknown>) => ({
        ...config,
        useLoaderData: vi.fn(),
    }),
}));
vi.mock('@tanstack/react-start', () => {
    const builder = {
        validator: () => builder,
        handler: (fn: (ctx: { data: unknown }) => unknown) => (args?: { data?: unknown }) =>
            fn({ data: args?.data }),
    };
    return { createServerFn: () => builder, useServerFn: (fn: unknown) => fn };
});

describe('/market-overview route loader', () => {
    beforeEach(() => fetchMarketOverviewData.mockClear());

    it('loads the full correlation matrix in SSR (no partial slice that flashes empty filters)', async () => {
        const { Route } = await import('./index');
        await (Route as unknown as { loader: () => Promise<unknown> }).loader();
        expect(fetchMarketOverviewData).toHaveBeenCalledWith(undefined);
    });
});
