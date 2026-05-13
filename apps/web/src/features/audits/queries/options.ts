import { infiniteQueryOptions } from '@tanstack/react-query';
import type { PaginatedAudits } from '../api/fetch-audits';
import { auditsQueryKeys } from './keys';

export const auditsQueries = {
    list: <T extends PaginatedAudits>(opts?: {
        cursor?: string;
        fetchFn?: (cursor: string | undefined) => Promise<T>;
    }) =>
        infiniteQueryOptions({
            queryKey: auditsQueryKeys.list(opts?.cursor),
            queryFn: ({ pageParam }) =>
                opts?.fetchFn
                    ? opts.fetchFn(pageParam)
                    : Promise.reject(new Error('fetchFn required')),
            initialPageParam: undefined as string | undefined,
            getNextPageParam: (lastPage: T) => lastPage?.nextCursor ?? undefined,
            staleTime: 1000 * 60 * 5,
        }),
};
