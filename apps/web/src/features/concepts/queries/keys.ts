export const conceptsQueryKeys = {
    all: ['benchify', 'concepts'] as const,
    list: () => ['benchify', 'concepts', 'list'] as const,
} as const;
