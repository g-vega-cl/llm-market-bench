import { queryOptions } from '@tanstack/react-query';
import type { Concept } from '../components/ConceptMap';
import { conceptsQueryKeys } from './keys';

export const conceptsQueries = {
    list: <T extends Concept[]>(opts?: { fetchFn?: () => Promise<T> }) =>
        queryOptions({
            queryKey: conceptsQueryKeys.list(),
            queryFn: opts?.fetchFn,
            staleTime: 1000 * 60 * 10, // 10 minutes - concepts change slowly
        }),
};
