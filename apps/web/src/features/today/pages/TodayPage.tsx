import * as React from 'react'
import { useSuspenseQuery } from '@tanstack/react-query'
import { todayQueries } from '../queries/options'
import { NewsletterFeed } from '../components/NewsletterFeed'
import { TradeActivity } from '../components/TradeActivity'
import { AgentInsights } from '../components/AgentInsights'
import { FutureCatalysts } from '../components/FutureCatalysts'
import { MarketStatusHero } from '../components/MarketStatusHero'

interface TodayPageProps {
  initialData: any
  fetchFn: () => Promise<any>
}

export function TodayPage({ initialData, fetchFn }: TodayPageProps) {
  const { data } = useSuspenseQuery({
    ...todayQueries.data({ fetchFn }),
    initialData,
    refetchInterval: 1000 * 60 * 5, // Auto-refetch every 5 minutes
  })

  // Check if everything is empty for today (excluding future events)
  const isEmpty = !data.newsletters?.length &&
    !data.trades?.length &&
    !data.decisions?.length &&
    !data.memories?.length &&
    !data.priceUpdates?.length;

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950">
      {/* Market Status Hero */}
      <MarketStatusHero data={data} />

      <main className="flex flex-col px-6 md:px-12 py-12 space-y-24 pb-24">
        <div className="flex flex-col w-full">
          {isEmpty ? (
            <EmptyState hasFutureEvents={!!data.futureEvents?.length} futureEvents={data.futureEvents} />
          ) : (
            <div className="space-y-24 animate-slide-up">
              <AgentInsights memories={data.memories} />
              <NewsletterFeed newsletters={data.newsletters} />
              <TradeActivity trades={data.trades} decisions={data.decisions} />
              <FutureCatalysts events={data.futureEvents} />
            </div>
          )}
        </div>
      </main>
    </div>
  )
}

function EmptyState({ hasFutureEvents, futureEvents }: { hasFutureEvents: boolean; futureEvents: any[] }) {
  const jokes = [
    { emoji: '🤖', title: 'AI is observing. Markets are sleeping.', subtitle: 'First trade incoming at 09:35 ET.' },
    { emoji: '📊', title: 'The algorithms are sharpening their models.', subtitle: 'Quiet before the storm.' },
    { emoji: '🧠', title: 'Neural networks are dreaming of electric sheep.', subtitle: 'And alpha signals.' },
    { emoji: '⚡', title: 'Charging the neural nets.', subtitle: 'Back at 09:35 ET with market-moving insights.' },
    { emoji: '🔮', title: 'Crystal ball is warming up.', subtitle: 'Predictions loading...' },
    { emoji: '💤', title: 'Agents are in power-saving mode.', subtitle: 'Wake up call at 09:35 ET.' },
  ]

  const randomJoke = jokes[Math.floor(Math.random() * jokes.length)]

  return (
    <div className="animate-scale-in">
      <div className="flex flex-col items-center justify-center py-16 md:py-24 text-center">
        <div className="relative mb-8">
          <div className="w-40 h-40 md:w-48 md:h-48 bg-gradient-to-br from-electric-blue-100 to-deep-purple-100 dark:from-electric-blue-950/30 dark:to-deep-purple-950/30 rounded-full flex items-center justify-center glow-electric shadow-2xl">
            <span className="text-7xl md:text-8xl animate-float">{randomJoke.emoji}</span>
          </div>
          <div className="absolute -top-2 -right-2 w-6 h-6 bg-neon-green-500 rounded-full live-dot shadow-lg shadow-neon-green-500/50" />
          {/* Decorative rings */}
          <div className="absolute inset-0 rounded-full border-2 border-electric-blue-200 dark:border-electric-blue-800 animate-ping opacity-20" style={{ animationDuration: '2s' }} />
          <div className="absolute inset-0 rounded-full border-2 border-deep-purple-200 dark:border-deep-purple-800 animate-ping opacity-20" style={{ animationDuration: '3s', animationDelay: '0.5s' }} />
        </div>
        <h2 className="text-2xl md:text-4xl font-black text-zinc-900 dark:text-white mb-3 text-display">
          {randomJoke.title}
        </h2>
        <p className="text-zinc-500 dark:text-zinc-400 max-w-md mb-8 text-base md:text-lg">
          {randomJoke.subtitle}
        </p>
        <div className="flex gap-4 flex-wrap justify-center">
          <a
            href="/memories"
            className="group px-6 py-3 bg-gradient-to-r from-electric-blue-600 to-deep-purple-600 hover:from-electric-blue-700 hover:to-deep-purple-700 text-white font-bold rounded-xl transition-all card-lift shadow-lg hover:shadow-xl flex items-center gap-2"
          >
            <span>View Historical Performance</span>
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" className="group-hover:translate-x-1 transition-transform">
              <path d="M5 12h14M12 5l7 7-7 7" />
            </svg>
          </a>
          <a
            href="/how-it-works"
            className="px-6 py-3 bg-white dark:bg-zinc-900 border-2 border-zinc-200 dark:border-zinc-800 hover:border-electric-blue-500 dark:hover:border-electric-blue-500 text-zinc-900 dark:text-white font-bold rounded-xl transition-all card-lift shadow-sm hover:shadow-md"
          >
            How It Works
          </a>
        </div>
      </div>

      {/* Show future events even on empty days */}
      {hasFutureEvents && (
        <div className="pt-12 border-t border-zinc-200 dark:border-zinc-800 animate-slide-up animate-stagger-2">
          <FutureCatalysts events={futureEvents} />
        </div>
      )}
    </div>
  )
}
