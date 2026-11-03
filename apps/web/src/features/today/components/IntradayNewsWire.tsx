import { Badge, Card, SectionHeading } from '@llm-market-bench/ui-design-system';
import type { FormattedIntradayNews } from '../api/fetch-intraday-news';

interface IntradayNewsWireProps {
    items: FormattedIntradayNews[];
}

export function IntradayNewsWire({ items }: IntradayNewsWireProps) {
    if (!items || items.length === 0) {
        return (
            <section className="flex flex-col gap-4 animate-slide-up">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <SectionHeading gradient="electric">⚡ Intraday Market Wire</SectionHeading>
                    <div className="flex items-center gap-2 px-3 py-1.5 bg-electric-blue-50 dark:bg-electric-blue-950/20 border border-electric-blue-200 dark:border-electric-blue-900/30 rounded-none shadow-sm">
                        <span className="text-xs font-bold text-electric-blue-600 dark:text-electric-blue-400 uppercase tracking-wider">
                            Vetted by Jev AI
                        </span>
                    </div>
                </div>
                <div className="flex flex-col items-center justify-center py-10 rounded-none border border-dashed border-zinc-200 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-900/30 text-center gap-2.5">
                    <span className="text-lg">📡</span>
                    <p className="text-sm font-bold text-zinc-300">
                        No breaking catalysts detected yet today
                    </p>
                    <p className="text-xs font-normal text-zinc-500 max-w-md leading-relaxed">
                        TypeSafe Jev actively screens live macro releases, Fed speeches, and
                        breaking headlines for material market impact.
                    </p>
                </div>
            </section>
        );
    }

    return (
        <section className="flex flex-col gap-4 animate-slide-up">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div className="flex items-center gap-3 flex-wrap">
                    <SectionHeading gradient="electric">⚡ Intraday Market Wire</SectionHeading>
                    <Badge variant="soft" colorScheme="accent" size="xs" radius="none">
                        Vetted by Jev AI
                    </Badge>
                </div>

                <div className="flex items-center gap-2 px-3 py-1.5 bg-emerald-500/10 border border-emerald-500/20 rounded-none shadow-sm">
                    <span className="text-xs font-bold text-emerald-400 uppercase tracking-wider">
                        🔴 Live • {items.length} Catalyst{items.length !== 1 ? 's' : ''}
                    </span>
                </div>
            </div>

            <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,18rem),1fr))] gap-4 items-stretch">
                {items.map((item, idx) => {
                    const tickersList = Array.isArray(item.tickers)
                        ? (item.tickers as string[])
                        : [];

                    return (
                        <Card
                            key={item.id || item.source_id_hash || idx}
                            isHoverable
                            className="relative overflow-hidden group/wire flex flex-col justify-between rounded-none shadow-sm gap-4"
                        >
                            <div className="relative flex flex-col gap-3">
                                {/* Header: Timestamp, Source & Jev Badge */}
                                <div className="flex items-center justify-between gap-2 flex-wrap">
                                    <div className="flex items-center gap-2">
                                        <span className="text-xs font-normal text-zinc-400 font-mono tabular-nums">
                                            {item.formattedTime} ET
                                        </span>
                                        <span className="text-zinc-600 text-xs">•</span>
                                        <span className="text-xs font-bold text-zinc-400 uppercase tracking-wider">
                                            {item.source}
                                        </span>
                                    </div>

                                    <Badge
                                        variant="soft"
                                        colorScheme="success"
                                        size="xs"
                                        radius="none"
                                        className="font-mono text-xs font-bold tracking-wider"
                                    >
                                        ⚡ {item.jev_choice} {item.jev_confidence}%
                                    </Badge>
                                </div>

                                {/* Headline */}
                                <h4 className="text-sm font-bold text-zinc-100 group-hover/wire:text-electric-blue-400 transition-colors leading-snug">
                                    {item.headline}
                                </h4>

                                {/* Summary Context */}
                                {item.summary && (
                                    <p className="text-xs font-normal text-zinc-400 leading-relaxed line-clamp-3">
                                        {item.summary}
                                    </p>
                                )}
                            </div>

                            {/* Footer: Ticker tags and Source link */}
                            <div className="pt-3 border-t border-zinc-800/60 flex items-center justify-between gap-2 flex-wrap">
                                <div className="flex items-center gap-1.5 flex-wrap">
                                    {tickersList.slice(0, 4).map((t) => (
                                        <Badge
                                            key={t}
                                            variant="outline"
                                            colorScheme="neutral"
                                            size="xs"
                                            radius="none"
                                            className="font-mono text-xs font-bold uppercase tracking-wider"
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
                                        className="text-xs font-bold text-electric-blue-400 hover:text-electric-blue-300 transition-colors inline-flex items-center gap-1"
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
