/**
 * Query keys for the Memories feature.
 */
export const memoriesQueryKeys = {
    all: ['benchify', 'memories'] as const,
    list: (filters?: { status?: string; memoryType?: string }) =>
        ['benchify', 'memories', 'list', filters] as const,
    detail: (id: string) => ['benchify', 'memories', 'detail', id] as const,
    sources: (id: string, sourceIds: string[]) =>
        ['benchify', 'memories', 'sources', id, sourceIds] as const,
    resolutionChild: (parentId: string) =>
        ['benchify', 'memories', 'resolutionChild', parentId] as const,
    causeAndEffect: (eventId: string) =>
        ['benchify', 'memories', 'causeAndEffect', eventId] as const,
} as const;

export const eventChainQueryKeys = {
    all: ['benchify', 'eventChain'] as const,
    detail: (id: string) => ['benchify', 'eventChain', 'detail', id] as const,
} as const;
