export const portfolioQueryKeys = {
    all: ['benchify', 'portfolios'] as const,
    list: () => ['benchify', 'portfolios', 'list'] as const,
    detail: (id: string) => ['benchify', 'portfolios', 'detail', id] as const,
    positions: (portfolioId: string) =>
        ['benchify', 'portfolios', 'detail', portfolioId, 'positions'] as const,
    trades: (portfolioId: string) =>
        ['benchify', 'portfolios', 'detail', portfolioId, 'trades'] as const,
    performance: (portfolioId: string) =>
        ['benchify', 'portfolios', 'detail', portfolioId, 'performance'] as const,
    comparison: (benchmark: string) => ['benchify', 'portfolios', 'comparison', benchmark] as const,
    benchmarks: {
        all: ['benchify', 'benchmarks'] as const,
        history: (tickers: string[], startDate: string, endDate: string) =>
            ['benchify', 'benchmarks', 'history', tickers.join(','), startDate, endDate] as const,
    },
};
