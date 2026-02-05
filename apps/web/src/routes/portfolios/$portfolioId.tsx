import { createFileRoute } from '@tanstack/react-router'
import { createServerFn } from '@tanstack/react-start'
import { fetchPortfolioById, fetchPositions, fetchPerformanceHistory } from './-queries'
import { PerformanceChart } from './components/-PerformanceChart'

const getPortfolioData = createServerFn({ method: 'GET' })
  .inputValidator((d: string) => d)
  .handler(async ({ data: portfolioId }) => {
    const [portfolio, positions, history] = await Promise.all([
      fetchPortfolioById(portfolioId),
      fetchPositions(portfolioId),
      fetchPerformanceHistory(portfolioId),
    ])

    return { portfolio, positions, history }
  })

export const Route = createFileRoute('/portfolios/$portfolioId')({
  loader: ({ params }) => getPortfolioData({ data: params.portfolioId }),
  component: PortfolioDetailPage,
})

function PortfolioDetailPage() {
  const { portfolio, positions, history } = Route.useLoaderData()

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
          <div className="overflow-x-auto border border-zinc-200 rounded-xl bg-white shadow-sm">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-zinc-50 border-bottom border-zinc-200">
                  <th className="px-6 py-4 text-xs font-bold uppercase tracking-wider text-zinc-500">Ticker</th>
                  <th className="px-6 py-4 text-xs font-bold uppercase tracking-wider text-zinc-500 text-right">Quantity</th>
                  <th className="px-6 py-4 text-xs font-bold uppercase tracking-wider text-zinc-500 text-right">Avg Cost</th>
                  <th className="px-6 py-4 text-xs font-bold uppercase tracking-wider text-zinc-500 text-right">Price</th>
                  <th className="px-6 py-4 text-xs font-bold uppercase tracking-wider text-zinc-500 text-right">P/L (USD)</th>
                  <th className="px-6 py-4 text-xs font-bold uppercase tracking-wider text-zinc-500 text-right">P/L (%)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-100">
                {positions?.map((pos) => (
                  <tr key={pos.ticker} className="hover:bg-zinc-50/50 transition-colors">
                    <td className="px-6 py-4 font-bold text-zinc-900">{pos.ticker}</td>
                    <td className="px-6 py-4 text-right text-zinc-700">{pos.quantity}</td>
                    <td className="px-6 py-4 text-right text-zinc-700">
                      ${Number(pos.average_cost_basis).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </td>
                    <td className="px-6 py-4 text-right text-zinc-700">
                      ${Number(pos.current_price || pos.average_cost_basis).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </td>
                    <td className={`px-6 py-4 text-right font-medium ${Number(pos.unrealized_pnl_usd) >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                      {Number(pos.unrealized_pnl_usd) >= 0 ? '+' : ''}
                      ${Number(pos.unrealized_pnl_usd).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </td>
                    <td className={`px-6 py-4 text-right font-medium ${Number(pos.unrealized_pnl_pct) >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                      {Number(pos.unrealized_pnl_pct) >= 0 ? '+' : ''}
                      {Number(pos.unrealized_pnl_pct).toFixed(2)}%
                    </td>
                  </tr>
                ))}
                {(!positions || positions.length === 0) && (
                  <tr>
                    <td colSpan={6} className="px-6 py-12 text-center text-zinc-500">
                      No active positions in this portfolio.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </div>
  )
}
