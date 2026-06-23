import { queryOptions } from '@tanstack/react-query';
import type { Concept, ConceptMemory } from '../api/fetch-concepts';
import { conceptsQueryKeys } from './keys';

export const conceptsQueries = {
    list: <T extends Concept[]>(opts?: { fetchFn?: () => Promise<T> }) =>
        queryOptions({
            queryKey: conceptsQueryKeys.list(),
            queryFn: opts?.fetchFn,
            staleTime: Number.POSITIVE_INFINITY,
        }),
    memories: (conceptId: string, fetchFn: () => Promise<ConceptMemory[]>) =>
        queryOptions({
            queryKey: [...conceptsQueryKeys.all, 'memories', conceptId] as const,
            queryFn: fetchFn,
            staleTime: Number.POSITIVE_INFINITY,
        }),
};
