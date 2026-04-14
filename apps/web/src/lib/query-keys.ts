import type { QueryKey } from '@tanstack/react-query'

// ============================================================================
// Query Key Factories
// Following TanStack's recommended pattern for type-safe query keys
// https://tanstack.com/query/latest/docs/framework/react/guides/query-keys
// ============================================================================

export const queryKeys = {
  // All queries are scoped under 'benchify'
  all: ['benchify'] as const,

  // Today page
  today: {
    all: ['benchify', 'today'] as const,
    data: () => ['benchify', 'today', 'data'] as const,
  },

  // Memories
  memories: {
    all: ['benchify', 'memories'] as const,
    list: (filters?: { status?: string; memoryType?: string }) =>
      ['benchify', 'memories', 'list', filters] as const,
    detail: (id: string) => ['benchify', 'memories', 'detail', id] as const,
  },

  // Event Chain
  eventChain: {
    all: ['benchify', 'eventChain'] as const,
    detail: (id: string) => ['benchify', 'eventChain', 'detail', id] as const,
  },

  // Reasoning logs
  reasoning: {
    all: ['benchify', 'reasoning'] as const,
    list: (cursor?: string) => ['benchify', 'reasoning', 'list', cursor] as const,
    detail: (id: string) => ['benchify', 'reasoning', 'detail', id] as const,
  },

  // Portfolios
  portfolios: {
    all: ['benchify', 'portfolios'] as const,
    list: () => ['benchify', 'portfolios', 'list'] as const,
    detail: (id: string) => ['benchify', 'portfolios', 'detail', id] as const,
    positions: (portfolioId: string) =>
      ['benchify', 'portfolios', 'detail', portfolioId, 'positions'] as const,
    trades: (portfolioId: string) =>
      ['benchify', 'portfolios', 'detail', portfolioId, 'trades'] as const,
    performance: (portfolioId: string) =>
      ['benchify', 'portfolios', 'detail', portfolioId, 'performance'] as const,
  },

  // Concepts
  concepts: {
    all: ['benchify', 'concepts'] as const,
    list: () => ['benchify', 'concepts', 'list'] as const,
  },

  // Cause & Effect
  causeAndEffect: {
    all: ['benchify', 'causeAndEffect'] as const,
    list: () => ['benchify', 'causeAndEffect', 'list'] as const,
  },

  // Audits
  audits: {
    all: ['benchify', 'audits'] as const,
    list: (cursor?: string) => ['benchify', 'audits', 'list', cursor] as const,
  },

  // Auth
  auth: {
    all: ['benchify', 'auth'] as const,
    user: () => ['benchify', 'auth', 'user'] as const,
  },
} as const

// ============================================================================
// Type Utilities
// ============================================================================

/**
 * Extracts the data type from a query function
 * Usage: type MemoriesData = InferQueryData<typeof fetchMemories>
 */
export type InferQueryData<T extends (...args: any[]) => Promise<any>> = Awaited<ReturnType<T>>

/**
 * Type for paginated response
 */
export interface PaginatedResponse<T> {
  data: T[]
  hasMore: boolean
  nextCursor: string | null
}
