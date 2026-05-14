import { MutationCache, QueryCache, QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import type * as React from 'react';

function makeQueryClient() {
    return new QueryClient({
        defaultOptions: {
            queries: {
                // With SSR, we usually want to set some default staleTime
                // above 0 to avoid refetching immediately on the client
                staleTime: 1000 * 60, // 1 minute
                // Retry on failures up to 3 times with exponential backoff
                retry: (failureCount, error) => {
                    // Don't retry on 404s or authentication errors
                    if (error instanceof Error && error.message.includes('404')) {
                        return false;
                    }
                    return failureCount < 3;
                },
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
