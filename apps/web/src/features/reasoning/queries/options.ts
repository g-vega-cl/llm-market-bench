import { infiniteQueryOptions, queryOptions } from '@tanstack/react-query'
import { reasoningQueryKeys } from './keys'
import type { PaginatedReasoningLogs } from '../api/fetch-reasoning-logs'

export const reasoningQueries = {
  list: <T extends PaginatedReasoningLogs>(opts?: {
    cursor?: string
    fetchFn?: (cursor: string | undefined) => Promise<T>
  }) =>
    infiniteQueryOptions({
      queryKey: reasoningQueryKeys.list(opts?.cursor),
      queryFn: ({ pageParam }) =>
        opts?.fetchFn ? opts.fetchFn(pageParam) : Promise.reject(new Error('fetchFn required')),
      initialPageParam: undefined as string | undefined,
      getNextPageParam: (lastPage: T) => lastPage?.nextCursor ?? undefined,
      staleTime: 1000 * 60 * 5,
    }),

  detail: <T,>(opts: { id: string; fetchFn?: () => Promise<T> }) =>
    queryOptions({
      queryKey: reasoningQueryKeys.detail(opts.id),
      queryFn: opts.fetchFn,
      staleTime: 1000 * 60 * 5,
    }),
}
