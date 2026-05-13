import { infiniteQueryOptions, queryOptions } from '@tanstack/react-query';
import type { PaginatedMemories } from '../api/fetch-memories';
import { eventChainQueryKeys, memoriesQueryKeys } from './keys';

/**
 * Memories feature query options factory.
 */
export const memoriesQueries = {
    list: <T extends PaginatedMemories>(opts?: {
        filters?: { status?: string; memoryType?: string };
        cursor?: string;
        fetchFn?: (cursor: string | undefined) => Promise<T>;
    }) =>
        infiniteQueryOptions({
            queryKey: memoriesQueryKeys.list(opts?.filters),
            queryFn: ({ pageParam }) =>
                opts?.fetchFn
                    ? opts.fetchFn(pageParam)
                    : Promise.reject(new Error('fetchFn required')),
            initialPageParam: undefined as string | undefined,
            getNextPageParam: (lastPage: T) => lastPage?.nextCursor ?? undefined,
            staleTime: 1000 * 60 * 5, // 5 minutes
        }),

    detail: <T>(opts: { id: string; fetchFn?: () => Promise<T> }) =>
        queryOptions({
            queryKey: memoriesQueryKeys.detail(opts.id),
            queryFn: opts.fetchFn,
            staleTime: 1000 * 60 * 5,
        }),
};

export const eventChainQueries = {
    detail: <T>(opts: { id: string; fetchFn?: () => Promise<T> }) =>
        queryOptions({
            queryKey: eventChainQueryKeys.detail(opts.id),
            queryFn: opts.fetchFn,
            staleTime: 1000 * 60 * 5,
        }),
};
