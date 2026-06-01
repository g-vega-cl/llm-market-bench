import { queryOptions } from '@tanstack/react-query';
import { todayQueryKeys } from './keys';

/**
 * Today feature query options factory.
 *
 * Takes an optional fetch function so it can easily integrate
 * with TanStack Start's useServerFn hooks inside components.
 */
export const todayQueries = {
    data: <T>(opts?: { fetchFn?: () => Promise<T> }) =>
        queryOptions({
            queryKey: todayQueryKeys.data(),
            queryFn: opts?.fetchFn,
            staleTime: 1000 * 60 * 2, // 2 minutes - today's data changes frequently
        }),
    hero: <T>(opts?: { fetchFn?: () => Promise<T> }) =>
        queryOptions({
            queryKey: todayQueryKeys.hero(),
            queryFn: opts?.fetchFn,
            // Hero is the LCP element — keep it fresh for streaming
            // revalidation but allow instant refetches on tab focus.
            staleTime: 1000 * 30, // 30 seconds
        }),
};
