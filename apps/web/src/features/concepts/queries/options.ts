import { queryOptions } from '@tanstack/react-query'
import { conceptsQueryKeys } from './keys'
import type { Concept } from '../components/ConceptMap'

export const conceptsQueries = {
  list: <T extends Concept[]>(opts?: { fetchFn?: () => Promise<T> }) =>
    queryOptions({
      queryKey: conceptsQueryKeys.list(),
      queryFn: opts?.fetchFn,
      staleTime: 1000 * 60 * 10, // 10 minutes - concepts change slowly
    }),
}
