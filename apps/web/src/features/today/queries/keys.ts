import type { QueryKey } from '@tanstack/react-query';

/**
 * Query keys for the Today feature.
 *
 * Following TanStack's recommended pattern for type-safe query keys.
 *
 * @see https://tanstack.com/query/latest/docs/framework/react/guides/query-keys
 */
export const todayQueryKeys = {
    all: ['benchify', 'today'] as const,
    data: () => ['benchify', 'today', 'data'] as const,
} as const;
