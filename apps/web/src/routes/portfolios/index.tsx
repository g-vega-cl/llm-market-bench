import { createFileRoute, Link } from '@tanstack/react-router'
import { createServerFn, useServerFn } from '@tanstack/react-start'
import { fetchPortfolios } from './-queries'
import { useSuspenseQuery } from '@tanstack/react-query'
import { queries } from '~/lib/queries'

const getPortfolios = createServerFn({ method: 'GET' }).handler(async () => {
  return fetchPortfolios()
})

export const Route = createFileRoute('/portfolios/')({
  loader: async () => await getPortfolios(),
  component: PortfoliosPage,
})

type Portfolio = {
  id: string
  owner_id: string
  total_equity: number | null
  cash_balance: number
  buying_power: number | null
  is_active: boolean
}

function PortfolioCard({ portfolio, deprecated = false }: { portfolio: Portfolio; deprecated?: boolean }) {
  return (
    <Link
      key={portfolio.id}
      to="/portfolios/$portfolioId"
      params={{ portfolioId: portfolio.id }}
      className="block group"
    >
      <div
        className={`h-full p-6 border rounded-xl shadow-sm transition-shadow ${
          deprecated
            ? 'border-zinc-200 bg-zinc-50 opacity-60 hover:opacity-80 hover:shadow-md'
            : 'border-zinc-200 bg-white hover:shadow-md group-hover:border-zinc-300'
        }`}
      >
        <div className="flex justify-between items-start mb-4">
          <h3
            className={`text-xl font-bold capitalize ${
              deprecated ? 'text-zinc-500' : 'text-zinc-900'
            }`}
          >
            {portfolio.owner_id.replace(/-/g, ' ')}
          </h3>
          <span
            className={`px-2 py-1 text-xs font-medium rounded ${
              deprecated
                ? 'bg-zinc-200 text-zinc-500'
                : 'bg-emerald-50 text-emerald-700 border border-emerald-200'
            }`}
          >
            {deprecated ? 'Retired' : 'Active'}
          </span>
        </div>

        <div className="space-y-4">
          <div>
            <div className="text-sm text-zinc-500 mb-1">Total Equity</div>
            <div className={`text-2xl font-bold ${deprecated ? 'text-zinc-500' : 'text-zinc-900'}`}>
              ${Number(portfolio.total_equity || 0).toLocaleString(undefined, {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4 pt-4 border-t border-zinc-100">
            <div>
              <div className="text-xs text-zinc-500 mb-1">Cash</div>
              <div className="text-sm font-semibold text-zinc-600">
                ${Number(portfolio.cash_balance).toLocaleString(undefined, {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2,
                })}
              </div>
            </div>
            <div>
              <div className="text-xs text-zinc-500 mb-1">Buying Power</div>
              <div className="text-sm font-semibold text-zinc-600">
                ${Number(portfolio.buying_power || 0).toLocaleString(undefined, {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2,
                })}
              </div>
            </div>
          </div>
        </div>
      </div>
    </Link>
  )
}

function PortfoliosPage() {
  const initialData = Route.useLoaderData()
  const getPortfoliosFn = useServerFn(getPortfolios)

  const { data } = useSuspenseQuery({
    ...queries.portfolios.list({ fetchFn: () => getPortfoliosFn() }),
    initialData,
  })

  const active = data?.filter((p) => p.is_active !== false) ?? []
  const deprecated = data?.filter((p) => p.is_active === false) ?? []

  return (
    <div className="max-w-5xl mx-auto p-6 md:p-12">
      <header className="mb-12">
        <h1 className="text-4xl font-bold text-zinc-800 mb-4 tracking-tight">
          Agent Portfolios
        </h1>
        <p className="text-zinc-500 text-lg max-w-2xl">
          Live performance and current holdings of our AI trading agents.
        </p>
      </header>

      {/* Active agents */}
      <section className="mb-16">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {active.map((portfolio) => (
            <PortfolioCard key={portfolio.id} portfolio={portfolio} />
          ))}
        </div>
      </section>

      {/* Deprecated / retired agents */}
      {deprecated.length > 0 && (
        <section>
          <div className="flex items-center gap-3 mb-6">
            <h2 className="text-lg font-semibold text-zinc-400 tracking-wide uppercase text-sm">
              Retired Agents
            </h2>
            <div className="flex-1 border-t border-zinc-200" />
            <span className="text-xs text-zinc-400 bg-zinc-100 px-2 py-1 rounded-full">
              No longer trading
            </span>
          </div>
          <p className="text-sm text-zinc-400 mb-6">
            These portfolios are preserved for historical reference. They no longer receive new
            trade decisions but their full audit trail remains accessible.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {deprecated.map((portfolio) => (
              <PortfolioCard key={portfolio.id} portfolio={portfolio} deprecated />
            ))}
          </div>
        </section>
      )}
    </div>
  )
}
