import { Badge, Button, Card, SectionHeading } from '@llm-market-bench/ui-design-system';
import { useState } from 'react';
import type { FormattedIntradayNews } from '../api/fetch-intraday-news';

interface IntradayNewsWireProps {
    items: FormattedIntradayNews[];
}

export function IntradayNewsWire({ items }: IntradayNewsWireProps) {
    const [activeTab, setActiveTab] = useState<'catalysts' | 'noise'>('catalysts');

    const safeItems = items || [];
    const catalysts = safeItems.filter((item) => item.jev_choice !== 'NOISE');
    const noiseItems = safeItems.filter((item) => item.jev_choice === 'NOISE');

    if (safeItems.length === 0) {
        return (
            <section className="flex flex-col gap-4 animate-slide-up">
                <div className="flex items-center justify-between gap-4 flex-wrap">
                    <SectionHeading gradient="electric">⚡ Intraday Market Wire</SectionHeading>
                    <Badge variant="soft" colorScheme="accent" size="xs" radius="none">
                        Vetted by Jev AI
                    </Badge>
                </div>
                <div className="flex flex-col items-center justify-center py-10 rounded-none border border-dashed border-zinc-800 bg-zinc-900/30 text-center gap-2">
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

    const visibleItems = activeTab === 'catalysts' ? catalysts : noiseItems;

    return (
        <section className="flex flex-col gap-4 animate-slide-up">
            <div className="flex items-center justify-between gap-4 flex-wrap">
                <div className="flex items-center gap-2 flex-wrap">
                    <SectionHeading gradient="electric">⚡ Intraday Market Wire</SectionHeading>
                    <Badge variant="soft" colorScheme="accent" size="xs" radius="none">
                        Vetted by Jev AI
                    </Badge>
                </div>

                <div className="flex items-center gap-2 flex-wrap">
                    <Button
                        size="sm"
                        rounded="none"
                        colorScheme={activeTab === 'catalysts' ? 'success' : 'neutral'}
                        variant={activeTab === 'catalysts' ? 'soft' : 'ghost'}
                        onClick={() => setActiveTab('catalysts')}
                    >
                        ⚡ Catalysts ({catalysts.length})
                    </Button>
                    <Button
                        size="sm"
                        rounded="none"
                        colorScheme={activeTab === 'noise' ? 'warning' : 'neutral'}
                        variant={activeTab === 'noise' ? 'soft' : 'ghost'}
                        onClick={() => setActiveTab('noise')}
                    >
                        🔇 Filtered Noise ({noiseItems.length})
                    </Button>
                </div>
            </div>

            {visibleItems.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-10 rounded-none border border-dashed border-zinc-800 bg-zinc-900/30 text-center gap-2">
                    <span className="text-lg">{activeTab === 'catalysts' ? '📡' : '🧹'}</span>
                    <p className="text-sm font-bold text-zinc-300">
                        {activeTab === 'catalysts'
                            ? 'No breaking catalysts detected yet today'
                            : 'No filtered noise headlines recorded yet today'}
                    </p>
                    <p className="text-xs font-normal text-zinc-500 max-w-md leading-relaxed">
                        {activeTab === 'catalysts'
                            ? 'TypeSafe Jev actively screens live macro releases, Fed speeches, and breaking headlines for material market impact.'
                            : 'Headlines rejected by Jev as routine corporate PR or low-impact chatter appear here.'}
                    </p>
                </div>
            ) : (
                <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,18rem),1fr))] gap-4 items-stretch">
                    {visibleItems.map((item, idx) => {
                        const tickersList = Array.isArray(item.tickers)
                            ? (item.tickers as string[])
                            : [];
                        const isNoise = item.jev_choice === 'NOISE';

                        return (
                            <Card
                                key={item.id || item.source_id_hash || idx}
                                isHoverable
                                className="relative overflow-hidden group/wire flex flex-col justify-between rounded-none shadow-sm gap-4"
                            >
                                <div className="relative flex flex-col gap-2">
                                    {/* Header: Timestamp, Source & Jev Badge */}
                                    <div className="flex items-center justify-between gap-2 flex-wrap">
                                        <div className="flex items-center gap-2 flex-wrap">
                                            <span className="text-xs font-normal text-zinc-400 font-mono tabular-nums whitespace-nowrap">
                                                {item.formattedTime} ET
                                            </span>
                                            <span className="text-zinc-600 text-xs">•</span>
                                            <span className="text-xs font-bold text-zinc-400 uppercase tracking-wider whitespace-nowrap">
                                                {item.source}
                                            </span>
                                        </div>

                                        <Badge
                                            variant="soft"
                                            colorScheme={isNoise ? 'neutral' : 'success'}
                                            size="xs"
                                            radius="none"
                                            className="font-mono text-xs font-bold tracking-wider whitespace-nowrap"
                                        >
                                            {isNoise ? '🔇' : '⚡'} {item.jev_choice}{' '}
                                            {item.jev_confidence}%
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
                                <div className="pt-2 border-t border-zinc-800/60 flex items-center justify-between gap-2 flex-wrap">
                                    <div className="flex items-center gap-2 flex-wrap">
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
                                            className="text-xs font-bold text-electric-blue-400 hover:text-electric-blue-300 transition-colors inline-flex items-center gap-2"
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
            )}
        </section>
    );
}
