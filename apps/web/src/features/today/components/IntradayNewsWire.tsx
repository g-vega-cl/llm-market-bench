import { Badge, Card, SectionHeading } from '@llm-market-bench/ui-design-system';
import type { FormattedIntradayNews } from '../api/fetch-intraday-news';

interface IntradayNewsWireProps {
    items: FormattedIntradayNews[];
}

export function IntradayNewsWire({ items }: IntradayNewsWireProps) {
    if (!items || items.length === 0) {
        return (
            <section className="space-y-4 animate-slide-up">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <SectionHeading gradient="electric">⚡ Intraday Market Wire</SectionHeading>
                    <div className="flex items-center gap-2 px-3 py-1.5 bg-electric-blue-50 dark:bg-electric-blue-950/20 border border-electric-blue-200 dark:border-electric-blue-900/30 rounded-xl shadow-sm">
                        <span className="text-[10px] font-black text-electric-blue-600 dark:text-electric-blue-400 uppercase tracking-widest">
                            Vetted by Jev AI
                        </span>
                    </div>
                </div>
                <div className="flex flex-col items-center justify-center py-10 rounded-3xl border border-dashed border-zinc-200 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-900/30 text-center gap-2.5">
                    <span className="text-3xl">📡</span>
                    <p className="text-sm font-semibold text-zinc-300">
                        No breaking catalysts detected yet today
                    </p>
                    <p className="text-xs text-zinc-500 max-w-md font-light leading-relaxed">
                        TypeSafe Jev actively screens live macro releases, Fed speeches, and
                        breaking headlines for material market impact.
                    </p>
                </div>
            </section>
        );
    }

    return (
        <section className="space-y-4 animate-slide-up">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div className="flex items-center gap-3 flex-wrap">
                    <SectionHeading gradient="electric">⚡ Intraday Market Wire</SectionHeading>
                    <Badge variant="soft" colorScheme="accent" size="xs">
                        Vetted by Jev AI
                    </Badge>
                </div>

                <div className="flex items-center gap-2 px-3 py-1.5 bg-emerald-500/10 border border-emerald-500/20 rounded-xl shadow-sm">
                    <span className="text-[10px] font-black text-emerald-400 uppercase tracking-widest">
                        🔴 Live • {items.length} Catalyst{items.length !== 1 ? 's' : ''}
                    </span>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {items.map((item, idx) => {
                    const tickersList = Array.isArray(item.tickers)
                        ? (item.tickers as string[])
                        : [];

                    return (
                        <Card
                            key={item.id || item.source_id_hash || idx}
                            isHoverable
                            className="relative overflow-hidden group/wire flex flex-col justify-between"
                        >
                            <div className="relative space-y-3">
                                {/* Header: Timestamp, Source & Jev Badge */}
                                <div className="flex items-center justify-between gap-2 flex-wrap">
                                    <div className="flex items-center gap-2">
                                        <span className="text-[10px] text-zinc-400 font-mono tabular-nums">
                                            {item.formattedTime} ET
                                        </span>
                                        <span className="text-zinc-600 text-xs">•</span>
                                        <span className="text-[10px] text-zinc-400 uppercase tracking-wider font-semibold">
                                            {item.source}
                                        </span>
                                    </div>

                                    <Badge
                                        variant="soft"
                                        colorScheme="success"
                                        size="xs"
                                        className="font-mono text-[9px] font-black tracking-wider"
                                    >
                                        ⚡ {item.jev_choice} {item.jev_confidence}%
                                    </Badge>
                                </div>

                                {/* Headline */}
                                <h4 className="text-base font-bold text-zinc-100 group-hover/wire:text-electric-blue-400 transition-colors leading-snug">
                                    {item.headline}
                                </h4>

                                {/* Summary Context */}
                                {item.summary && (
                                    <p className="text-xs text-zinc-400 font-light leading-relaxed line-clamp-3">
                                        {item.summary}
                                    </p>
                                )}
                            </div>

                            {/* Footer: Ticker tags and Source link */}
                            <div className="mt-4 pt-3 border-t border-zinc-800/60 flex items-center justify-between gap-2 flex-wrap">
                                <div className="flex items-center gap-1.5 flex-wrap">
                                    {tickersList.slice(0, 4).map((t) => (
                                        <Badge
                                            key={t}
                                            variant="outline"
                                            colorScheme="neutral"
                                            size="xs"
                                            className="font-mono text-[9px] uppercase tracking-wider"
                                        >
                                            ${t}
                                        </Badge>
                                    ))}
                                </div>

                                {item.url && (
                                    <a
                                        href={item.url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="text-[10px] font-bold text-electric-blue-400 hover:text-electric-blue-300 transition-colors inline-flex items-center gap-1"
                                    >
                                        <span>Source</span>
                                        <span>↗</span>
                                    </a>
                                )}
                            </div>
                        </Card>
                    );
                })}
            </div>
        </section>
    );
}
