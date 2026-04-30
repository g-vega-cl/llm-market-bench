import { queryOptions } from '@tanstack/react-query'
import { causeAndEffectQueryKeys } from './keys'

export const causeAndEffectQueries = {
  list: <T,>(opts?: { fetchFn?: () => Promise<T> }) =>
    queryOptions({
      queryKey: causeAndEffectQueryKeys.list(),
      queryFn: opts?.fetchFn,
      staleTime: 1000 * 60 * 5,
    }),
}
