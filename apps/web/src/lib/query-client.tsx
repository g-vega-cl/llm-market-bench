import { MutationCache, QueryCache, QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import type * as React from 'react';

export function makeQueryClient() {
    return new QueryClient({
        defaultOptions: {
            queries: {
                // With SSR, we usually want to set some default staleTime
                // above 0 to avoid refetching immediately on the client
                staleTime: 1000 * 60, // 1 minute
                // Retry on failures up to 3 times with exponential backoff and jitter
                retry: (failureCount, error) => {
                    // Don't retry on 4xx client errors (400, 401, 403, 404)
                    if (error instanceof Error) {
                        const msg = error.message;
                        if (
                            msg.includes('404') ||
                            msg.includes('401') ||
                            msg.includes('403') ||
                            msg.includes('400')
                        ) {
                            return false;
                        }
                    }
                    return failureCount < 3;
                },
                retryDelay: (attemptIndex) => {
                    // Exponential backoff with jitter: 1s, 2s, 4s (+ 0-500ms jitter, max 10s)
                    const baseDelay = Math.min(1000 * 2 ** attemptIndex, 10000);
                    const jitter = Math.random() * 500;
                    return baseDelay + jitter;
                },
                // Automatically refetch when network reconnects (TanStack default)
                refetchOnReconnect: true,
                // Show error in UI but don't throw
                throwOnError: false,
                // Add a timeout for queries
                gcTime: 1000 * 60 * 5, // 5 minutes (formerly cacheTime)
            },
            mutations: {
                retry: 1, // Only retry mutations once
                throwOnError: false,
            },
        },
        // Global query cache for error handling
        queryCache: new QueryCache({
            onError: (error, query) => {
                // Global error logging
                console.error('[QueryCache] Error:', error, 'Query:', query.queryKey);
            },
        }),
        // Global mutation cache for error handling
        mutationCache: new MutationCache({
            onError: (error, _variables, _context, _mutation) => {
                // Global error logging
                console.error('[MutationCache] Error:', error);
            },
        }),
    });
}

let browserQueryClient: QueryClient | undefined;

function getQueryClient() {
    if (typeof window === 'undefined') {
        // Server: always make a new query client
        return makeQueryClient();
    } else {
        // Browser: make a new query client if we don't already have one
        // This is important for React Query to work properly
        if (!browserQueryClient) browserQueryClient = makeQueryClient();
        return browserQueryClient;
    }
}

export function QueryClientProviderWrapper({ children }: { children: React.ReactNode }) {
    const queryClient = getQueryClient();

    return (
        <QueryClientProvider client={queryClient}>
            {children}
            {/* Only show DevTools in development */}
            {process.env.NODE_ENV === 'development' && <ReactQueryDevtools initialIsOpen={false} />}
        </QueryClientProvider>
    );
}

export interface QuerySettlementState {
    isFetched?: boolean;
    isFetching: boolean;
    isPending?: boolean;
    isSuccess?: boolean;
    isPlaceholderData?: boolean;
    data?: unknown;
}

/**
 * Returns true only when all provided queries have completed fetching,
 * are not currently refetching, are not serving placeholderData,
 * have valid data, and no concurrent React transition is pending.
 */
export function isQuerySettled(
    queries: (QuerySettlementState | undefined | null)[] | QuerySettlementState | undefined | null,
    isTransitionPending = false,
): boolean {
    if (isTransitionPending) return false;
    if (queries === null || queries === undefined) return false;
    const queryList = Array.isArray(queries) ? queries : [queries];
    if (queryList.length === 0) return true;
    return queryList.every((q) => {
        if (!q) return false;
        const hasValidData = q.data !== undefined && (q.isSuccess ?? true);
        return hasValidData && !q.isFetching && !q.isPending && !q.isPlaceholderData;
    });
}
