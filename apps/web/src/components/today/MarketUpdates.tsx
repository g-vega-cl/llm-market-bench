import * as React from 'react'

export function MarketUpdates({ priceUpdates }: { priceUpdates: any[] }) {
    if (!priceUpdates.length) return null;

    // Deduplicate updates by ticker and show most recent
    const latestPrices = priceUpdates.reduce((acc: any, curr: any) => {
        if (!acc[curr.ticker] || new Date(curr.fetched_at) > new Date(acc[curr.ticker].fetched_at)) {
            acc[curr.ticker] = curr;
        }
        return acc;
    }, {});

    const sortedPrices = Object.values(latestPrices).sort((a: any, b: any) => a.ticker.localeCompare(b.ticker));

    return (
        <section className="space-y-6">
             <h2 className="text-2xl font-black text-zinc-900 dark:text-white flex items-center gap-3">
                <span className="w-2 h-8 bg-amber-500 rounded-full" />
                Live Market Pulse
            </h2>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
                {sortedPrices.map((update: any) => (
                    <div key={update.ticker} className="p-4 border border-zinc-200 dark:border-zinc-800 rounded-2xl bg-white dark:bg-zinc-900 shadow-sm text-center">
                        <div className="text-xs font-black text-zinc-400 mb-1 uppercase tracking-widest">{update.ticker}</div>
                        <div className="text-lg font-bold text-zinc-900 dark:text-white">${Number(update.price).toFixed(2)}</div>
                        <div className="text-[8px] text-zinc-400 font-mono mt-1">
                            {new Date(update.fetched_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </div>
                    </div>
                ))}
            </div>
        </section>
    )
}
