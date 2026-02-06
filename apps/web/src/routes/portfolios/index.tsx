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
    <div className="stack gap-fluid-2xl">
      <header className="stack gap-fluid-xs">
        <h1 className="text-fluid-4xl font-black text-zinc-900 dark:text-white tracking-tighter">
          Agent Portfolios
        </h1>
        <p className="text-zinc-500 text-fluid-lg max-w-2xl">
          Live performance and current holdings of our AI trading agents.
        </p>
      </header>

      <div className="grid-auto-fit">
        {portfolios?.map((portfolio) => (
          <Link
            key={portfolio.id}
            to="/portfolios/$portfolioId"
            params={{ portfolioId: portfolio.id }}
            className="card-vibrant group no-underline"
          >
            <div className="flex justify-between items-start mb-fluid-m">
              <h3 className="text-fluid-xl font-black text-zinc-900 dark:text-zinc-100 capitalize tracking-tight group-hover:text-brand transition-colors">
                {portfolio.owner_id.replace(/-/g, ' ')}
              </h3>
              <span className="px-fluid-s py-1 text-xs font-bold bg-brand/10 text-brand rounded-full uppercase tracking-widest">
                Active
              </span>
            </div>

            <div className="stack gap-fluid-m">
              <div>
                <div className="text-xs font-bold text-zinc-400 uppercase tracking-widest mb-1">
                  Total Equity
                </div>
                <div className="text-fluid-3xl font-black text-zinc-900 dark:text-zinc-100">
                  $
                  {Number(portfolio.total_equity || 0).toLocaleString(undefined, {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2,
                  })}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-fluid-m pt-fluid-m border-t-2 border-zinc-100 dark:border-zinc-800">
                <div>
                  <div className="text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-1">
                    Cash
                  </div>
                  <div className="text-fluid-base font-bold text-zinc-700 dark:text-zinc-300">
                    $
                    {Number(portfolio.cash_balance).toLocaleString(undefined, {
                      minimumFractionDigits: 2,
                      maximumFractionDigits: 2,
                    })}
                  </div>
                </div>
                <div>
                  <div className="text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-1">
                    Buying Power
                  </div>
                  <div className="text-fluid-base font-bold text-zinc-700 dark:text-zinc-300">
                    $
                    {Number(portfolio.buying_power || 0).toLocaleString(undefined, {
                      minimumFractionDigits: 2,
                      maximumFractionDigits: 2,
                    })}
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
