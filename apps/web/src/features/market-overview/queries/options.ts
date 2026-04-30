import { queryOptions } from '@tanstack/react-query'
import { marketOverviewQueryKeys } from './keys'
import type { MarketOverviewData } from '../api/fetch-market-overview'

export const marketOverviewQueries = {
  data: (opts?: { fetchFn?: () => Promise<MarketOverviewData> }) =>
    queryOptions({
      queryKey: marketOverviewQueryKeys.data(),
      queryFn: opts?.fetchFn,
      staleTime: 1000 * 60 * 60, // 1 hour - correlation data changes weekly
    }),
}
