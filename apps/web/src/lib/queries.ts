import { queryOptions, infiniteQueryOptions } from '@tanstack/react-query'
import { queryKeys } from './query-keys'

/**
 * Centralized query options factory.
 * These factories take an optional fetch function so they can easily integrate
 * with TanStack Start's useServerFn hooks inside components.
 */
export const queries = {
  // --------------------------------------------------------------------------
  // Today Page
  // --------------------------------------------------------------------------
  today: <T,>(fetchFn?: () => Promise<T>) =>
    queryOptions({
      queryKey: queryKeys.today.data(),
      queryFn: fetchFn,
      staleTime: 1000 * 60 * 2, // 2 minutes - today's data changes frequently
    }),

  // --------------------------------------------------------------------------
  // Portfolios
  // --------------------------------------------------------------------------
  portfolios: {
    list: <T,>(fetchFn?: () => Promise<T>) =>
      queryOptions({
        queryKey: queryKeys.portfolios.list(),
        queryFn: fetchFn,
        staleTime: 1000 * 60 * 5, // 5 minutes
      }),
    detail: <T,>(id: string, fetchFn?: () => Promise<T>) =>
      queryOptions({
        queryKey: queryKeys.portfolios.detail(id),
        queryFn: fetchFn,
        staleTime: 1000 * 60 * 5, // 5 minutes
      }),
    positions: <T,>(id: string, fetchFn?: () => Promise<T>) =>
      queryOptions({
        queryKey: queryKeys.portfolios.positions(id),
        queryFn: fetchFn,
        staleTime: 1000 * 60 * 5, // 5 minutes
      }),
    trades: <T,>(id: string, fetchFn?: () => Promise<T>) =>
      queryOptions({
        queryKey: queryKeys.portfolios.trades(id),
        queryFn: fetchFn,
        staleTime: 1000 * 60 * 5, // 5 minutes
      }),
    performance: <T,>(id: string, fetchFn?: () => Promise<T>) =>
      queryOptions({
        queryKey: queryKeys.portfolios.performance(id),
        queryFn: fetchFn,
        staleTime: 1000 * 60 * 5, // 5 minutes
      }),
  },

  // --------------------------------------------------------------------------
  // Concepts
  // --------------------------------------------------------------------------
  concepts: {
    list: <T,>(fetchFn?: () => Promise<T>) =>
      queryOptions({
        queryKey: queryKeys.concepts.list(),
        queryFn: fetchFn,
        staleTime: 1000 * 60 * 10, // 10 minutes - concepts don't change often
      }),
  },

  // --------------------------------------------------------------------------
  // Cause & Effect
  // --------------------------------------------------------------------------
  causeAndEffect: {
    list: <T,>(fetchFn?: () => Promise<T>) =>
      queryOptions({
        queryKey: queryKeys.causeAndEffect.list(),
        queryFn: fetchFn,
        staleTime: 1000 * 60 * 5, // 5 minutes
      }),
  },

  // --------------------------------------------------------------------------
  // Memories
  // --------------------------------------------------------------------------
  memories: {
    list: <T,>(filters?: { status?: string; memoryType?: string }, fetchFn?: (cursor: string | undefined) => Promise<T>) =>
      infiniteQueryOptions({
        queryKey: queryKeys.memories.list(filters),
        queryFn: ({ pageParam }) => fetchFn ? fetchFn(pageParam) : Promise.reject(new Error('fetchFn required')),
        initialPageParam: undefined as string | undefined,
        getNextPageParam: (lastPage: any) => lastPage?.nextCursor ?? undefined,
        staleTime: 1000 * 60 * 5, // 5 minutes
      }),
    detail: <T,>(id: string, fetchFn?: () => Promise<T>) =>
      queryOptions({
        queryKey: queryKeys.memories.detail(id),
        queryFn: fetchFn,
        staleTime: 1000 * 60 * 5,
      }),
  },

  // --------------------------------------------------------------------------
  // Reasoning
  // --------------------------------------------------------------------------
  reasoning: {
    list: <T,>(cursor?: string, fetchFn?: (cursor: string | undefined) => Promise<T>) =>
      infiniteQueryOptions({
        queryKey: queryKeys.reasoning.list(cursor),
        queryFn: ({ pageParam }) => fetchFn ? fetchFn(pageParam) : Promise.reject(new Error('fetchFn required')),
        initialPageParam: undefined as string | undefined,
        getNextPageParam: (lastPage: any) => lastPage?.nextCursor ?? undefined,
        staleTime: 1000 * 60 * 5, // 5 minutes
      }),
    detail: <T,>(id: string, fetchFn?: () => Promise<T>) =>
      queryOptions({
        queryKey: queryKeys.reasoning.detail(id),
        queryFn: fetchFn,
        staleTime: 1000 * 60 * 5, // 5 minutes
      }),
  },
}
