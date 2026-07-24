import { queryOptions } from '@tanstack/react-query';
import { autoresearchQueryKeys } from './keys';

/**
 * Autoresearch feature query options factory.
 */
export const autoresearchQueries = {
    experiments: <T>(opts?: { fetchFn?: () => Promise<T> }) =>
        queryOptions({
            queryKey: autoresearchQueryKeys.experiments(),
            queryFn: opts?.fetchFn,
            staleTime: 1000 * 60 * 10, // 10 minutes - experiments change once a week
        }),
    backtest: <T>(opts?: { fetchFn?: () => Promise<T> }) =>
        queryOptions({
            queryKey: autoresearchQueryKeys.backtest(),
            queryFn: opts?.fetchFn,
            staleTime: 1000 * 60 * 10,
        }),
};
