import { createFileRoute } from '@tanstack/react-router'
import { createServerFn, useServerFn } from '@tanstack/react-start'
import { fetchPortfolioById, fetchPositions, fetchPerformanceHistory, fetchTrades } from './-queries'
import { PerformanceChart } from './components/-PerformanceChart'
import { PositionsTable } from './components/-PositionsTable'
import { TradesTable } from './components/-TradesTable'
import { useSuspenseQuery } from '@tanstack/react-query'
import { queries } from '~/lib/queries'
import * as React from 'react'
import { usePostHog } from '@posthog/react'

const getPortfolioData = createServerFn({ method: 'GET' })
  .inputValidator((d: string) => d)
  .handler(async ({ data: portfolioId }: { data: string }) => {
    const [portfolio, positions, history, trades] = await Promise.all([
      fetchPortfolioById(portfolioId),
      fetchPositions(portfolioId),
      fetchPerformanceHistory(portfolioId),
      fetchTrades(portfolioId),
    ])

    return { portfolio, positions, history, trades }
  })

export const Route = createFileRoute('/portfolios/$portfolioId')({
  loader: ({ params }) => getPortfolioData({ data: params.portfolioId }),
  component: PortfolioDetailPage,
})

function PortfolioDetailPage() {
  const posthog = usePostHog()
  const initialData = Route.useLoaderData()
  const getPortfolioDataFn = useServerFn(getPortfolioData)

  const { data } = useSuspenseQuery({
    ...queries.portfolios.detail({ id: initialData.portfolio.id, fetchFn: () => getPortfolioDataFn(initialData.portfolio.id) }),
    initialData,
  })

  const { portfolio, positions, history, trades } = data

  React.useEffect(() => {
    posthog.capture('portfolio_viewed', { portfolio_id: portfolio.id, owner_id: portfolio.owner_id })
  }, [portfolio.id])

  if (!portfolio) {
    return <div>Portfolio not found</div>
  }

  return (
    <div className="max-w-7xl mx-auto p-6 md:p-12">
      <header className="mb-12 flex flex-col md:flex-row md:items-end justify-between gap-6">
        <div>
          <h1 className="text-4xl font-bold text-zinc-900 mb-2 tracking-tight capitalize">
            {portfolio.owner_id.replace(/-/g, ' ')}
          </h1>
          <p className="text-zinc-500 text-lg">
            Portfolio analysis and performance timeline.
          </p>
        </div>
        <div className="bg-zinc-50 border border-zinc-200 rounded-lg p-4 flex gap-8">
          <div>
            <div className="text-xs text-zinc-500 uppercase tracking-wider mb-1">Total Equity</div>
            <div className="text-2xl font-bold text-zinc-900">
              ${Number(portfolio.total_equity || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </div>
          </div>
          <div>
            <div className="text-xs text-zinc-500 uppercase tracking-wider mb-1">Cash</div>
            <div className="text-2xl font-bold text-zinc-900">
              ${Number(portfolio.cash_balance).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </div>
          </div>
        </div>
      </header>

      <div className="grid grid-cols-1 gap-12">
        {/* Performance Chart */}
        <section>
          <PerformanceChart data={history || []} />
          {(!history || history.length === 0) && (
            <div className="mt-4 p-8 border border-dashed border-zinc-300 rounded-xl text-center text-zinc-500">
              No performance history available yet. Performance is recorded daily.
            </div>
          )}
        </section>

        {/* Positions Table */}
        <section>
          <h3 className="text-xl font-bold text-zinc-900 mb-6">Current Positions</h3>
          <PositionsTable positions={positions as any} />
        </section>

        {/* Recent Trades Table */}
        <section>
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-xl font-bold text-zinc-900">Recent Trades</h3>
            <span className="text-sm text-zinc-500 bg-zinc-100 px-3 py-1 rounded-full font-medium">
              Audit Trail
            </span>
          </div>
          <TradesTable trades={trades as any} />
        </section>
      </div>
    </div>
  )
}
