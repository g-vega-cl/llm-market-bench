export const reasoningQueryKeys = {
    all: ['benchify', 'reasoning'] as const,
    list: (cursor?: string) => ['benchify', 'reasoning', 'list', cursor] as const,
    detail: (id: string) => ['benchify', 'reasoning', 'detail', id] as const,
} as const;
