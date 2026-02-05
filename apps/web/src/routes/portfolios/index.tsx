import { createFileRoute, Link } from '@tanstack/react-router'
import { createServerFn } from '@tanstack/react-start'
import { fetchPortfolios } from './-queries'

const getPortfolios = createServerFn({ method: 'GET' }).handler(async () => {
  return fetchPortfolios()
})

export const Route = createFileRoute('/portfolios/')({
  loader: async () => await getPortfolios(),
  component: PortfoliosPage,
})

function PortfoliosPage() {
  const portfolios = Route.useLoaderData()

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

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {portfolios?.map((portfolio) => (
          <Link
            key={portfolio.id}
            to="/portfolios/$portfolioId"
            params={{ portfolioId: portfolio.id }}
            className="block group"
          >
            <div className="h-full p-6 border border-zinc-200 rounded-xl bg-white shadow-sm hover:shadow-md transition-shadow group-hover:border-zinc-300">
              <div className="flex justify-between items-start mb-4">
                <h3 className="text-xl font-bold text-zinc-900 capitalize">
                  {portfolio.owner_id.replace(/-/g, ' ')}
                </h3>
                <span className="px-2 py-1 text-xs font-medium bg-zinc-100 text-zinc-600 rounded">
                  Active
                </span>
              </div>

              <div className="space-y-4">
                <div>
                  <div className="text-sm text-zinc-500 mb-1">Total Equity</div>
                  <div className="text-2xl font-bold text-zinc-900">
                    ${Number(portfolio.total_equity || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4 pt-4 border-t border-zinc-100">
                  <div>
                    <div className="text-xs text-zinc-500 mb-1">Cash</div>
                    <div className="text-sm font-semibold text-zinc-800">
                      ${Number(portfolio.cash_balance).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-zinc-500 mb-1">Buying Power</div>
                    <div className="text-sm font-semibold text-zinc-800">
                      ${Number(portfolio.buying_power || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  )
}
