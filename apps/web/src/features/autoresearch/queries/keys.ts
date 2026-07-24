export const autoresearchQueryKeys = {
    all: ['autoresearch'] as const,
    experiments: () => ['autoresearch', 'experiments'] as const,
    backtest: () => ['autoresearch', 'backtest'] as const,
} as const;
