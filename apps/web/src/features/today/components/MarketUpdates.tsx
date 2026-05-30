import { Card, SectionHeading } from '@llm-market-bench/ui-design-system';
import { formatEasternShortTime } from '~/utils/date';

interface PriceUpdate {
    ticker: string;
    price: number;
    price_change: number;
    fetched_at: string;
}

interface MarketUpdatesProps {
    priceUpdates: PriceUpdate[];
}

export function MarketUpdates({ priceUpdates }: MarketUpdatesProps) {
    if (!priceUpdates.length) return null;

    // Deduplicate updates by ticker and show most recent
    const latestPrices = priceUpdates.reduce(
        (acc: Record<string, PriceUpdate>, curr: PriceUpdate) => {
            if (
                !acc[curr.ticker] ||
                new Date(curr.fetched_at) > new Date(acc[curr.ticker].fetched_at)
            ) {
                acc[curr.ticker] = curr;
            }
            return acc;
        },
        {},
    );

    const sortedPrices = Object.values(latestPrices).sort((a: PriceUpdate, b: PriceUpdate) =>
        a.ticker.localeCompare(b.ticker),
    );

    return (
        <section className="space-y-8 animate-slide-up">
            <div className="flex items-center justify-between">
                <SectionHeading gradient="catalyst">Live Market Pulse</SectionHeading>

                <div className="flex items-center gap-2 px-4 py-2 bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-900/30 rounded-xl">
                    <div className="live-dot" />
                    <span className="text-[10px] font-black text-amber-600 dark:text-amber-400 uppercase tracking-widest">
                        Real-time
                    </span>
                </div>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
                {sortedPrices.map((update: PriceUpdate, idx) => {
                    const priceChange = update.price_change || 0;
                    const isPositive = priceChange >= 0;

                    return (
                        <Card
                            key={update.ticker}
                            isHoverable
                            radius="2xl"
                            padding="sm"
                            className="text-center relative overflow-hidden animate-slide-up"
                            style={{ animationDelay: `${idx * 50}ms` }}
                        >
                            {/* Background Gradient on Hover */}
                            <div
                                className={`absolute inset-0 opacity-0 group-hover:opacity-5 transition-opacity duration-300 ${
                                    isPositive ? 'bg-neon-green-500' : 'bg-alert-red-500'
                                }`}
                            />

                            {/* Ticker */}
                            <div className="relative">
                                <div className="text-xs font-black text-zinc-400 mb-2 uppercase tracking-widest">
                                    {update.ticker}
                                </div>

                                {/* Price */}
                                <div className="text-2xl font-black text-zinc-900 dark:text-white mb-2 text-display">
                                    ${Number(update.price).toFixed(2)}
                                </div>

                                {/* Change Indicator */}
                                {priceChange !== 0 && (
                                    <div
                                        className={`flex items-center justify-center gap-1 text-xs font-bold ${
                                            isPositive
                                                ? 'text-neon-green-500'
                                                : 'text-alert-red-500'
                                        }`}
                                    >
                                        <span>
                                            {isPositive ? '↑' : '↓'}{' '}
                                            {Math.abs(priceChange).toFixed(2)}%
                                        </span>
                                    </div>
                                )}

                                {/* Timestamp */}
                                <div className="text-[8px] text-zinc-400 font-mono mt-2 flex items-center justify-center gap-1">
                                    <span className="w-1 h-1 bg-zinc-300 rounded-full" />
                                    {`${formatEasternShortTime(update.fetched_at)} ET`}
                                </div>
                            </div>
                        </Card>
                    );
                })}
            </div>
        </section>
    );
}
