import { createFileRoute } from '@tanstack/react-router'
import { createServerFn } from '@tanstack/react-start'
import { fetchTodayData } from './-today-queries'
import { NewsletterFeed } from '~/components/today/NewsletterFeed'
import { TradeActivity } from '~/components/today/TradeActivity'
import { MarketUpdates } from '~/components/today/MarketUpdates'
import { AgentInsights } from '~/components/today/AgentInsights'
import { FutureCatalysts } from '~/components/today/FutureCatalysts'
import * as React from 'react'

const getTodayData = createServerFn({ method: 'GET' }).handler(async () => {
    return fetchTodayData()
})

export const Route = createFileRoute('/')({
    loader: async () => await getTodayData(),
    component: TodayPage,
})

function TodayPage() {
    const data = Route.useLoaderData()

    // Check if everything is empty for today (excluding future events)
    const isEmpty = !data.newsletters?.length &&
        !data.trades?.length &&
        !data.decisions?.length &&
        !data.memories?.length &&
        !data.priceUpdates?.length;

    return (
        <div className="min-h-screen bg-gray-50 dark:bg-gray-950 p-6 md:p-12 animate-slow-fade">
            <header className="mb-12 max-w-7xl mx-auto">
                <div className="flex flex-col md:flex-row md:items-center gap-4 mb-4">
                    <h1 className="text-6xl font-black text-zinc-900 dark:text-white tracking-tighter">
                        TODAY
                    </h1>
                    <div className="w-fit px-4 py-1 bg-blue-600 text-white text-sm font-black rounded-full shadow-lg shadow-blue-500/20">
                        {new Date().toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}
                    </div>
                </div>
                <p className="text-zinc-500 dark:text-zinc-400 text-xl max-w-2xl font-light leading-relaxed">
                    A real-time snapshot of the market's pulse and the collective cognition of our AI agents.
                </p>
            </header>

            <div className="max-w-7xl mx-auto space-y-24 pb-24">
                {isEmpty ? (
                    <div className="flex flex-col items-center justify-center py-24 text-center border-2 border-dashed border-zinc-200 dark:border-zinc-800 rounded-[3rem]">
                        <div className="w-24 h-24 bg-zinc-100 dark:bg-zinc-900 rounded-full flex items-center justify-center mb-6 shadow-inner">
                            <span className="text-4xl animate-bounce">☕</span>
                        </div>
                        <h2 className="text-2xl font-bold text-zinc-800 dark:text-zinc-200 mb-2">Quiet on the Western Front.</h2>
                        <p className="text-zinc-500 dark:text-zinc-400 max-w-md">
                            No news ingested, trades executed, or insights generated for this calendar day yet.
                            Check back after the morning pipeline runs (09:35 ET).
                        </p>
                    </div>
                ) : (
                    <div className="space-y-24">
                        <AgentInsights memories={data.memories} />
                        <NewsletterFeed newsletters={data.newsletters} />
                        <TradeActivity trades={data.trades} decisions={data.decisions} />
                        <FutureCatalysts events={data.futureEvents} />
                    </div>
                )}

                {/* Always show future events if they exist and page is empty */}
                {isEmpty && data.futureEvents?.length > 0 && (
                    <div className="pt-8 border-t border-zinc-200 dark:border-zinc-800">
                        <FutureCatalysts events={data.futureEvents} />
                    </div>
                )}
            </div>
        </div>
    )
}
