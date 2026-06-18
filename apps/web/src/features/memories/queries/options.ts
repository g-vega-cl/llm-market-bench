import { infiniteQueryOptions, queryOptions } from '@tanstack/react-query';
import type { NewsletterSnapshot, PaginatedMemories } from '../api/fetch-memories';
import { eventChainQueryKeys, memoriesQueryKeys } from './keys';

/**
 * Memories feature query options factory.
 */
export const memoriesQueries = {
    list: <T extends PaginatedMemories>(opts?: {
        filters?: { status?: string; memoryType?: string; category?: string };
        cursor?: string;
        fetchFn?: (cursor: string | undefined, category?: string) => Promise<T>;
    }) =>
        infiniteQueryOptions({
            queryKey: memoriesQueryKeys.list(opts?.filters),
            queryFn: ({ pageParam }) =>
                opts?.fetchFn
                    ? opts.fetchFn(pageParam, opts?.filters?.category)
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

    sources: <T extends NewsletterSnapshot[]>(opts: {
        id: string;
        sourceIds: string[];
        fetchFn?: (sourceIds: string[]) => Promise<T>;
    }) =>
        queryOptions({
            queryKey: memoriesQueryKeys.sources(opts.id, opts.sourceIds),
            queryFn: () =>
                opts.fetchFn
                    ? opts.fetchFn(opts.sourceIds)
                    : Promise.reject(new Error('fetchFn required')),
            staleTime: 1000 * 60 * 5, // 5 minutes
        }),
};

export const eventChainQueries = {
    detail: <T>(opts: { id: string; fetchFn?: () => Promise<T> }) =>
        queryOptions({
            queryKey: eventChainQueryKeys.detail(opts.id),
            queryFn: opts.fetchFn,
            staleTime: 0, // Force background refetch on client-mount for Hybrid SSR
        }),
};
