import { createFileRoute, Link } from '@tanstack/react-router'
import { createServerFn, useServerFn } from '@tanstack/react-start'
import { fetchMarketOverviewData } from './-queries'
import { queries } from '~/lib/queries'
import { useSuspenseQuery } from '@tanstack/react-query'
import * as React from 'react'
import { CorrelationHeatmap } from './components/-CorrelationHeatmap'
import { UncorrelatedPairs } from './components/-UncorrelatedPairs'
import type { MarketFeeling } from '@llm-market-bench/database'

const getMarketOverview = createServerFn({ method: 'GET' }).handler(async () => {
  return fetchMarketOverviewData()
})

export const Route = createFileRoute('/market-overview/')({
  component: MarketOverviewPage,
})

function MarketOverviewPage() {
  const initialData = Route.useLoaderData()
  const getMarketOverviewFn = useServerFn(getMarketOverview)

  const { data } = useSuspenseQuery({
    ...queries.marketOverview({ fetchFn: () => getMarketOverviewFn() }),
    initialData,
    staleTime: 1000 * 60 * 60, // 1 hour - correlation data changes weekly
  })

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950">
      <MarketOverviewHero marketFeeling={data.marketFeeling} />

      <main className="flex flex-col px-6 md:px-12 py-12 space-y-24 pb-24">
        {data.correlationRun ? (
          <div className="space-y-24 animate-slide-up">
            <CorrelationHeatmap
              correlationData={data.correlationData}
              tickers={data.correlationRun.tickers}
            />
            <UncorrelatedPairs
              correlationData={data.correlationData}
            />
            <SectorPerformanceGrid
              correlationData={data.correlationData}
              tickers={data.correlationRun.tickers}
            />
          </div>
        ) : (
          <EmptyCorrelationState />
        )}
      </main>
    </div>
  )
}

function MarketOverviewHero({ marketFeeling }: { marketFeeling: MarketFeeling | null }) {
  const now = new Date()
  const currentHour = now.getUTCHours()
  const currentMinutes = now.getUTCMinutes()
  const dayOfWeek = now.getUTCDay()

  const isMarketOpen = dayOfWeek >= 1 && dayOfWeek <= 5 &&
    ((currentHour > 13 || (currentHour === 13 && currentMinutes >= 30)) && currentHour < 20)

  const formatTimeAgo = (dateStr: string | null | undefined): string => {
    if (!dateStr) return 'Unknown'
    const date = new Date(dateStr)
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMins / 60)

    if (diffMins < 1) return 'Just now'
    if (diffMins < 60) return `${diffMins}m ago`
    if (diffHours < 24) return `${diffHours}h ago`
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: 'numeric' })
  }

  const getDirectionColor = (direction: string | null | undefined): string => {
    switch (direction?.toUpperCase()) {
      case 'BULLISH': return 'text-neon-green-400'
      case 'BEARISH': return 'text-alert-red-400'
      default: return 'text-steel-400'
    }
  }

  const getConfidenceColor = (score: number | null | undefined): string => {
    if (!score) return 'bg-steel-500'
    if (score >= 70) return 'bg-neon-green-500'
    if (score >= 40) return 'bg-amber-500'
    return 'bg-alert-red-500'
  }

  const isStale = marketFeeling ? (() => {
    if (!marketFeeling.created_at) return true
    const created = new Date(marketFeeling.created_at)
    const ageHours = (now.getTime() - created.getTime()) / 3600000
    return ageHours > 4
  })() : true

  return (
    <div className="relative overflow-hidden gradient-electric">
      <div className="absolute inset-0 opacity-10">
        <div className="absolute inset-0" style={{
          backgroundImage: `radial-gradient(circle at 2px 2px, white 1px, transparent 0)`,
          backgroundSize: '40px 40px'
        }} />
      </div>

      <div className="absolute inset-0 bg-gradient-to-br from-electric-blue-600/90 via-deep-purple-600/80 to-electric-blue-800/90" />

      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-electric-blue-400/20 rounded-full blur-3xl animate-pulse" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-deep-purple-400/20 rounded-full blur-3xl animate-pulse animate-stagger-2" />

      <div className="relative max-w-7xl mx-auto px-6 md:px-12 py-16 md:py-20">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
          <div className="space-y-6 animate-slide-up">
            <div className="flex flex-col sm:flex-row sm:items-center gap-4 flex-wrap">
              <h1 className="text-5xl sm:text-6xl font-black text-white tracking-tighter text-display drop-shadow-lg">
                MARKET OVERVIEW
              </h1>
              <div className="px-4 py-2 bg-white/20 backdrop-blur-sm text-white text-sm font-bold rounded-full border border-white/30 shadow-lg">
                {now.toLocaleDateString('en-US', {
                  weekday: 'long',
                  month: 'long',
                  day: 'numeric',
                  year: 'numeric'
                })}
              </div>
            </div>

            <p className="text-lg text-electric-blue-100 font-light leading-relaxed max-w-2xl drop-shadow">
              Real-time correlation matrix, uncorrelated asset pairs, and macro sentiment analysis.
              Updated weekly on Sundays.
            </p>

            <div className="flex items-center gap-4">
              <div className={`flex items-center gap-2 px-4 py-2 rounded-full text-sm font-bold transition-all ${
                isMarketOpen
                  ? 'bg-neon-green-500/20 text-neon-green-300 border border-neon-green-500/30'
                  : 'bg-steel-500/20 text-steel-300 border border-steel-500/30'
              }`}>
                <div className={`w-2 h-2 rounded-full ${
                  isMarketOpen ? 'bg-neon-green-400 live-dot' : 'bg-steel-400'
                }`} />
                {isMarketOpen ? 'MARKET OPEN' : 'MARKET CLOSED'}
              </div>
              <Link
                to="/"
                className="text-sm text-electric-blue-200 hover:text-white transition-colors underline underline-offset-2"
              >
                View AI Trading Activity →
              </Link>
            </div>
          </div>

          <div className="space-y-6 animate-slide-up animate-stagger-2">
            <div className="bg-white/10 backdrop-blur-md border border-white/20 rounded-3xl p-6 shadow-2xl">
              <div className="flex items-center justify-between mb-4">
                <span className="text-xs font-black text-electric-blue-200 uppercase tracking-widest">
                  How I'm Feeling
                </span>
                <div className="flex items-center gap-2">
                  <span className="text-2xl animate-float">
                    {marketFeeling?.sentiment_emoji || '🤔'}
                  </span>
                  {isStale && marketFeeling && (
                    <span className="text-xs px-2 py-0.5 bg-amber-500/20 text-amber-300 rounded-full" title="Data is older than 4 hours">
                      ⚠
                    </span>
                  )}
                </div>
              </div>

              <div className={`text-3xl sm:text-4xl font-black mb-3 text-display drop-shadow ${getDirectionColor(marketFeeling?.market_direction)}`}>
                {marketFeeling?.sentiment_label || 'Analyzing...'}
              </div>

              {marketFeeling?.market_direction && (
                <div className="flex items-center gap-2 mb-4">
                  <span className={`text-xs font-bold px-2 py-1 rounded-full border ${
                    marketFeeling.market_direction === 'BULLISH'
                      ? 'bg-neon-green-500/20 text-neon-green-300 border-neon-green-500/30'
                      : marketFeeling.market_direction === 'BEARISH'
                      ? 'bg-alert-red-500/20 text-alert-red-300 border-alert-red-500/30'
                      : 'bg-steel-500/20 text-steel-300 border-steel-500/30'
                  }`}>
                    {marketFeeling.market_direction}
                  </span>
                </div>
              )}

              {marketFeeling?.confidence_score !== null && marketFeeling?.confidence_score !== undefined && (
                <div className="flex items-center gap-2 mb-4">
                  <span className="text-[10px] text-electric-blue-200 uppercase tracking-wider">Confidence</span>
                  <div className="flex-1 h-2 bg-white/10 rounded-full overflow-hidden shadow-inner max-w-[120px]">
                    <div
                      className={`h-full ${getConfidenceColor(marketFeeling.confidence_score)} transition-all duration-1000`}
                      style={{ width: `${marketFeeling.confidence_score}%` }}
                    />
                  </div>
                  <span className="text-xs font-bold text-white tabular-nums">{marketFeeling.confidence_score}%</span>
                </div>
              )}

              {marketFeeling?.why_explanation && (
                <p className="text-sm text-electric-blue-100 leading-relaxed mb-4 italic">
                  "{marketFeeling.why_explanation}"
                </p>
              )}

              {marketFeeling?.primary_concern && (
                <div className="flex flex-wrap gap-2 mb-4">
                  <span className="text-[10px] text-electric-blue-300 uppercase tracking-wider">Primary Concern:</span>
                  <span className="text-xs px-2 py-1 bg-white/5 rounded-lg text-electric-blue-100 border border-white/10">
                    {marketFeeling.primary_concern}
                  </span>
                </div>
              )}

              <div className="flex items-center gap-2 mt-4 pt-3 border-t border-white/10">
                <span className="text-[10px] text-electric-blue-300">
                  {marketFeeling?.created_at
                    ? `Last analyzed: ${formatTimeAgo(marketFeeling.created_at)}`
                    : 'Waiting for analysis...'}
                </span>
                {marketFeeling?.model_used && (
                  <span className="text-[10px] text-electric-blue-400/50">• {marketFeeling.model_used}</span>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function SectorPerformanceGrid({ correlationData, tickers }: { correlationData: any[]; tickers: string[] }) {
  const tickerReturns = React.useMemo(() => {
    const returns: Record<string, { positive: boolean; ticker: string }[]> = {}

    // Group tickers by category based on naming conventions
    const categories: Record<string, string[]> = {
      'US Sectors': ['XLK', 'XLE', 'XLF', 'XLV', 'XLY', 'XLI', 'XLB', 'XLU', 'XLRE', 'XLC'],
      'US Broad': ['QQQ', 'VIG', 'IWM', 'SPY'],
      'Intl Dev': ['EFA', 'EWJ', 'EWG', 'EWL', 'EWP', 'IFAD', 'BWX'],
      'Emerging Markets': ['EEM', 'MCHI', 'EWZ', 'EIDO', 'EPI'],
      'Commodities': ['GLD', 'SLV', 'PDBC', 'USO'],
      'Bonds': ['TLT', 'IEF', 'LQD', 'EMB', 'BNDX', 'IAGG'],
      'Real Assets': ['VNQ', 'ICF'],
      'Crypto': ['BTCUSD', 'ETHUSD'],
      'Volatility': ['VIXY', 'VIXM'],
      'Dollar': ['UUP'],
    }

    for (const [category, categoryTickers] of Object.entries(categories)) {
      returns[category] = []
      for (const ticker of categoryTickers) {
        // Find return for this ticker
        const corrEntry = correlationData.find(c => c.ticker_a === ticker)
        const return90d = corrEntry?.returns_a_90d ?? 0
        returns[category].push({ positive: return90d >= 0, ticker })
      }
    }

    return returns
  }, [correlationData])

  return (
    <section>
      <h2 className="text-2xl font-bold text-zinc-800 dark:text-zinc-100 mb-8 tracking-tight">
        Sector Performance (90-Day Trailing Returns)
      </h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {Object.entries(tickerReturns).map(([category, items]) => (
          <div key={category} className="bg-white dark:bg-zinc-900 rounded-xl border border-zinc-200 dark:border-zinc-800 p-5">
            <h3 className="text-sm font-bold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider mb-4">
              {category}
            </h3>
            <div className="space-y-2">
              {items.map(({ ticker, positive }) => (
                <div key={ticker} className="flex items-center justify-between">
                  <span className="font-mono text-sm text-zinc-700 dark:text-zinc-300">{ticker}</span>
                  <span className={`text-sm font-semibold ${positive ? 'text-neon-green-500' : 'text-alert-red-400'}`}>
                    {positive ? '↑' : '↓'}
                  </span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}

function EmptyCorrelationState() {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <div className="w-32 h-32 bg-zinc-100 dark:bg-zinc-900 rounded-full flex items-center justify-center mb-8">
        <span className="text-6xl">📊</span>
      </div>
      <h2 className="text-2xl font-bold text-zinc-700 dark:text-zinc-300 mb-4">
        Correlation Matrix Pending
      </h2>
      <p className="text-zinc-500 dark:text-zinc-500 max-w-md mb-8">
        The correlation matrix runs weekly on Sundays at 16:00 ET.
        Check back after the next scheduled run for uncorrelated asset pairs.
      </p>
      <div className="text-sm text-zinc-400">
        Next run: This Sunday at 16:00 ET
      </div>
    </div>
  )
}