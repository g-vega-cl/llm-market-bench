import type { QueryKey } from '@tanstack/react-query';

/**
 * Query keys for the Memories feature.
 */
export const memoriesQueryKeys = {
    all: ['benchify', 'memories'] as const,
    list: (filters?: { status?: string; memoryType?: string }) =>
        ['benchify', 'memories', 'list', filters] as const,
    detail: (id: string) => ['benchify', 'memories', 'detail', id] as const,
} as const;

export const eventChainQueryKeys = {
    all: ['benchify', 'eventChain'] as const,
    detail: (id: string) => ['benchify', 'eventChain', 'detail', id] as const,
} as const;
