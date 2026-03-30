import { createFileRoute } from '@tanstack/react-router'
import { createServerFn, useServerFn } from '@tanstack/react-start'
import { fetchTodayData } from './-today-queries'
import { NewsletterFeed } from '~/components/today/NewsletterFeed'
import { TradeActivity } from '~/components/today/TradeActivity'
import { AgentInsights } from '~/components/today/AgentInsights'
import { FutureCatalysts } from '~/components/today/FutureCatalysts'
import { MarketStatusHero } from '~/components/today/MarketStatusHero'
import * as React from 'react'
import { useSuspenseQuery } from '@tanstack/react-query'
import { queries } from '~/lib/queries'

const getTodayData = createServerFn({ method: 'GET' }).handler(async () => {
    return fetchTodayData()
})

export const Route = createFileRoute('/')({
    loader: async () => await getTodayData(),
    component: TodayPage,
})

function TodayPage() {
    const initialData = Route.useLoaderData()
    const getTodayDataFn = useServerFn(getTodayData)

    const { data } = useSuspenseQuery({
        ...queries.today({ fetchFn: () => getTodayDataFn() }),
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

            <main className="max-w-7xl mx-auto px-6 md:px-12 py-12 space-y-24 pb-24">
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
    ]

    const randomJoke = jokes[Math.floor(Math.random() * jokes.length)]

    return (
        <div className="animate-scale-in">
            <div className="flex flex-col items-center justify-center py-24 text-center">
                <div className="relative mb-8">
                    <div className="w-32 h-32 bg-gradient-to-br from-electric-blue-100 to-deep-purple-100 dark:from-electric-blue-950/30 dark:to-deep-purple-950/30 rounded-full flex items-center justify-center glow-electric">
                        <span className="text-6xl animate-float">{randomJoke.emoji}</span>
                    </div>
                    <div className="absolute -top-2 -right-2 w-6 h-6 bg-neon-green-500 rounded-full live-dot" />
                </div>
                <h2 className="text-3xl font-black text-zinc-900 dark:text-white mb-3 text-display">
                    {randomJoke.title}
                </h2>
                <p className="text-zinc-500 dark:text-zinc-400 max-w-md mb-8 text-lg">
                    {randomJoke.subtitle}
                </p>
                <div className="flex gap-4 flex-wrap justify-center">
                    <a
                        href="/memories"
                        className="px-6 py-3 bg-electric-blue-600 hover:bg-electric-blue-700 text-white font-bold rounded-xl transition-all card-lift"
                    >
                        View Historical Performance
                    </a>
                    <a
                        href="/how-it-works"
                        className="px-6 py-3 bg-white dark:bg-zinc-900 border-2 border-zinc-200 dark:border-zinc-800 hover:border-electric-blue-500 text-zinc-900 dark:text-white font-bold rounded-xl transition-all card-lift"
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
