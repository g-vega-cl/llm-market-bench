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
  today: <T,>(opts?: { fetchFn?: () => Promise<T> }) =>
    queryOptions({
      queryKey: queryKeys.today.data(),
      queryFn: opts?.fetchFn,
      staleTime: 1000 * 60 * 2, // 2 minutes - today's data changes frequently
    }),

  // --------------------------------------------------------------------------
  // Portfolios
  // --------------------------------------------------------------------------
  portfolios: {
    list: <T,>(opts?: { fetchFn?: () => Promise<T> }) =>
      queryOptions({
        queryKey: queryKeys.portfolios.list(),
        queryFn: opts?.fetchFn,
        staleTime: 1000 * 60 * 5, // 5 minutes
      }),
    detail: <T,>(opts: { id: string; fetchFn?: () => Promise<T> }) =>
      queryOptions({
        queryKey: queryKeys.portfolios.detail(opts.id),
        queryFn: opts.fetchFn,
        staleTime: 1000 * 60 * 5, // 5 minutes
      }),
    positions: <T,>(opts: { id: string; fetchFn?: () => Promise<T> }) =>
      queryOptions({
        queryKey: queryKeys.portfolios.positions(opts.id),
        queryFn: opts.fetchFn,
        staleTime: 1000 * 60 * 5, // 5 minutes
      }),
    trades: <T,>(opts: { id: string; fetchFn?: () => Promise<T> }) =>
      queryOptions({
        queryKey: queryKeys.portfolios.trades(opts.id),
        queryFn: opts.fetchFn,
        staleTime: 1000 * 60 * 5, // 5 minutes
      }),
    performance: <T,>(opts: { id: string; fetchFn?: () => Promise<T> }) =>
      queryOptions({
        queryKey: queryKeys.portfolios.performance(opts.id),
        queryFn: opts.fetchFn,
        staleTime: 1000 * 60 * 5, // 5 minutes
      }),
  },

  // --------------------------------------------------------------------------
  // Concepts
  // --------------------------------------------------------------------------
  concepts: {
    list: <T,>(opts?: { fetchFn?: () => Promise<T> }) =>
      queryOptions({
        queryKey: queryKeys.concepts.list(),
        queryFn: opts?.fetchFn,
        staleTime: 1000 * 60 * 10, // 10 minutes - concepts don't change often
      }),
  },

  // --------------------------------------------------------------------------
  // Cause & Effect
  // --------------------------------------------------------------------------
  causeAndEffect: {
    list: <T,>(opts?: { fetchFn?: () => Promise<T> }) =>
      queryOptions({
        queryKey: queryKeys.causeAndEffect.list(),
        queryFn: opts?.fetchFn,
        staleTime: 1000 * 60 * 5, // 5 minutes
      }),
  },

  // --------------------------------------------------------------------------
  // Audits
  // --------------------------------------------------------------------------
  audits: {
    list: <T,>(opts?: { cursor?: string; fetchFn?: (cursor: string | undefined) => Promise<T> }) =>
      infiniteQueryOptions({
        queryKey: queryKeys.audits.list(opts?.cursor),
        queryFn: ({ pageParam }) => opts?.fetchFn ? opts.fetchFn(pageParam) : Promise.reject(new Error('fetchFn required')),
        initialPageParam: undefined as string | undefined,
        getNextPageParam: (lastPage: any) => lastPage?.nextCursor ?? undefined,
        staleTime: 1000 * 60 * 5, // 5 minutes
      }),
  },

  // --------------------------------------------------------------------------
  // Memories
  // --------------------------------------------------------------------------
  memories: {
    list: <T,>(opts?: { filters?: { status?: string; memoryType?: string }; cursor?: string; fetchFn?: (cursor: string | undefined) => Promise<T> }) =>
      infiniteQueryOptions({
        queryKey: queryKeys.memories.list(opts?.filters),
        queryFn: ({ pageParam }) => opts?.fetchFn ? opts.fetchFn(pageParam) : Promise.reject(new Error('fetchFn required')),
        initialPageParam: undefined as string | undefined,
        getNextPageParam: (lastPage: any) => lastPage?.nextCursor ?? undefined,
        staleTime: 1000 * 60 * 5, // 5 minutes
      }),
    detail: <T,>(opts: { id: string; fetchFn?: () => Promise<T> }) =>
      queryOptions({
        queryKey: queryKeys.memories.detail(opts.id),
        queryFn: opts.fetchFn,
        staleTime: 1000 * 60 * 5,
      }),
  },

  // --------------------------------------------------------------------------
  // Event Chain
  // --------------------------------------------------------------------------
  eventChain: {
    detail: <T,>(opts: { id: string; fetchFn?: () => Promise<T> }) =>
      queryOptions({
        queryKey: queryKeys.eventChain.detail(opts.id),
        queryFn: opts.fetchFn,
        staleTime: 1000 * 60 * 5, // 5 minutes
      }),
  },

  // --------------------------------------------------------------------------
  // Benchmarks
  // --------------------------------------------------------------------------
  benchmarks: {
    history: <T,>(opts: { tickers: string[]; startDate: string; endDate: string; fetchFn?: () => Promise<T> }) =>
      queryOptions({
        queryKey: queryKeys.benchmarks.history(opts.tickers, opts.startDate, opts.endDate),
        queryFn: opts.fetchFn,
        staleTime: 1000 * 60 * 5,
        enabled: opts.tickers.length > 0 && !!opts.startDate && !!opts.endDate,
      }),
  },

  // --------------------------------------------------------------------------
  // Reasoning
  // --------------------------------------------------------------------------
  reasoning: {
    list: <T,>(opts?: { cursor?: string; fetchFn?: (cursor: string | undefined) => Promise<T> }) =>
      infiniteQueryOptions({
        queryKey: queryKeys.reasoning.list(opts?.cursor),
        queryFn: ({ pageParam }) => opts?.fetchFn ? opts.fetchFn(pageParam) : Promise.reject(new Error('fetchFn required')),
        initialPageParam: undefined as string | undefined,
        getNextPageParam: (lastPage: any) => lastPage?.nextCursor ?? undefined,
        staleTime: 1000 * 60 * 5, // 5 minutes
      }),
    detail: <T,>(opts: { id: string; fetchFn?: () => Promise<T> }) =>
      queryOptions({
        queryKey: queryKeys.reasoning.detail(opts.id),
        queryFn: opts.fetchFn,
        staleTime: 1000 * 60 * 5, // 5 minutes
      }),
  },
}
