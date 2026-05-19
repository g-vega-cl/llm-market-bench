export const autoresearchQueryKeys = {
    all: ['autoresearch'] as const,
    experiments: () => ['autoresearch', 'experiments'] as const,
} as const;
