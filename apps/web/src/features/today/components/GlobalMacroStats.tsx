import { Badge, Button, Card, SectionHeading } from '@llm-market-bench/ui-design-system';
import * as React from 'react';
import type { MacroCategory, MacroStat } from '../lib/macro-tickers';

interface GlobalMacroStatsProps {
    macroStats: MacroStat[];
    lastUpdated?: string | null;
}

const CATEGORIES: MacroCategory[] = [
    'Market',
    'Equities',
    'International',
    'Commodities',
    'Bonds & Treasury Yields',
    'FX & Risk',
    'Crypto',
];

function getLatestMacroTimestamp(stats: MacroStat[]): string | null {
    const withFormatted = stats.filter((s) => s.formattedTime);
    if (withFormatted.length > 0) {
        const sorted = [...withFormatted].sort((a, b) => {
            if (a.fetchedAt && b.fetchedAt) {
                return b.fetchedAt.localeCompare(a.fetchedAt);
            }
            return 0;
        });
        return sorted[0].formattedTime || null;
    }
    return null;
}

export function GlobalMacroStats({ macroStats, lastUpdated }: GlobalMacroStatsProps) {
    const [activeTab, setActiveTab] = React.useState<MacroCategory>('Market');

    if (!macroStats || macroStats.length === 0) {
        return null;
    }

    const displayLastUpdated = lastUpdated ?? getLatestMacroTimestamp(macroStats);

    // Stats filtered by active category tab
    const filteredStats = macroStats.filter((s) => s.category === activeTab);

    return (
        <section className="flex flex-col gap-6 animate-slide-up">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-voxel-bevel-hi pb-6">
                <div>
                    <SectionHeading>Global Macro Regime</SectionHeading>
                    <p className="text-xs font-normal text-voxel-muted mt-1.5 leading-relaxed">
                        Dynamic standard deviations, current price shifts, and volatility regime
                        signals.
                    </p>
                </div>

                <div className="flex flex-wrap items-center gap-3 self-start md:self-auto shrink-0">
                    {displayLastUpdated && (
                        <div className="text-xs text-zinc-400 font-mono">
                            Last updated:{' '}
                            <span className="text-zinc-200 font-bold tabular-nums">
                                {displayLastUpdated}
                            </span>
                        </div>
                    )}
                    <div className="flex items-center gap-2 px-3 py-1.5 bg-electric-blue-500/10 border border-electric-blue-500/20 rounded-none">
                        <span className="live-dot" />
                        <span className="text-sm font-bold text-info uppercase tracking-wider font-mono">
                            Calculated Live
                        </span>
                    </div>
                </div>
            </div>

            {/* Category Navigation Tabs */}
            <div className="flex justify-center border-b border-voxel-bevel-hi pb-4 overflow-x-auto scrollbar-none">
                <div className="flex gap-1.5 p-1.5 bg-voxel-trough rounded-none border border-voxel-bevel-hi max-w-full">
                    {CATEGORIES.map((cat) => (
                        <Button
                            key={cat}
                            variant={activeTab === cat ? 'solid' : 'outline'}
                            colorScheme={activeTab === cat ? 'accent' : 'neutral'}
                            onClick={() => setActiveTab(cat)}
                            className="px-4 py-2.5 rounded-none font-bold text-sm uppercase tracking-wider transition-all duration-200 shrink-0"
                        >
                            {cat}
                        </Button>
                    ))}
                </div>
            </div>

            {/* Bonds & Treasury Yields Explanatory Banner */}
            {activeTab === 'Bonds & Treasury Yields' && (
                <div className="p-4 bg-voxel-trough border border-voxel-bevel-hi rounded-none flex gap-3.5 items-start animate-scale-in text-xs font-normal text-voxel-ink leading-relaxed shadow-inner">
                    <span className="text-lg animate-pulse">💡</span>
                    <div>
                        <span className="font-bold text-voxel-ink uppercase tracking-wider block mb-1">
                            Bond Prices vs Treasury Yields (Inverse Rule)
                        </span>
                        The S&P 500 benchmark model tracks bond ETFs (`IEF` and `TLT`) directly.
                        Because bond prices move
                        <strong className="text-electric-blue-500 font-bold"> inversely </strong> to
                        market interest yields:
                        <ul className="list-disc list-inside mt-2 flex flex-col gap-1 text-xs text-voxel-muted">
                            <li>
                                If{' '}
                                <strong className="text-alert-red-500">
                                    IEF / TLT Prices drop
                                </strong>
                                , actual bond interest yields are
                                <strong className="text-neon-green-500 font-bold uppercase">
                                    {' '}
                                    rising{' '}
                                </strong>{' '}
                                (typically risk-off/hawkish).
                            </li>
                            <li>
                                If{' '}
                                <strong className="text-neon-green-500">
                                    IEF / TLT Prices rise
                                </strong>
                                , actual bond interest yields are
                                <strong className="text-alert-red-500 font-bold uppercase">
                                    {' '}
                                    falling{' '}
                                </strong>{' '}
                                (typically risk-on/dovish).
                            </li>
                        </ul>
                    </div>
                </div>
            )}

            {/* Categorized Stats Cards Grid */}
            <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,16rem),1fr))] gap-4 items-stretch">
                {filteredStats.map((stat, idx) => {
                    const isPositive = stat.todayPctChange >= 0;
                    return (
                        <Card
                            key={stat.ticker}
                            isHoverable
                            padding="md"
                            className="relative overflow-hidden border border-voxel-bevel-hi transition-all duration-300 shadow-sm animate-slide-up flex flex-col justify-between h-full"
                            style={{ animationDelay: `${idx * 40}ms` }}
                        >
                            <div className="flex flex-col gap-3">
                                <div className="flex justify-between items-start gap-2">
                                    <div className="flex flex-col gap-0.5">
                                        <div className="text-sm font-bold text-voxel-ink line-clamp-1">
                                            {stat.name}
                                        </div>
                                        <div className="text-xs font-normal text-voxel-muted font-mono uppercase tracking-wider">
                                            {stat.ticker}
                                        </div>
                                    </div>
                                    <RegimeBadge flag={stat.regimeFlag} />
                                </div>

                                <div className="flex justify-between items-baseline gap-2">
                                    <span className="text-sm font-bold text-voxel-ink font-mono tracking-tight text-display tabular-nums">
                                        {stat.ticker === 'BTCUSD'
                                            ? `$${stat.price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
                                            : `$${stat.price.toFixed(2)}`}
                                    </span>
                                    <span
                                        className={`text-sm font-bold font-mono tabular-nums ${
                                            isPositive ? 'text-success' : 'text-danger'
                                        }`}
                                    >
                                        {isPositive ? '↑' : '↓'}{' '}
                                        {Math.abs(stat.todayPctChange).toFixed(2)}%
                                    </span>
                                </div>
                            </div>

                            <div className="pt-3 mt-3 border-t border-voxel-bevel-hi flex flex-col gap-2">
                                {/* Standard deviation visual index threshold bar */}
                                <div className="flex flex-col gap-1">
                                    <div className="flex justify-between text-xs font-normal text-voxel-muted uppercase tracking-wider font-mono">
                                        <span>30d Volatility</span>
                                        <span>Stdev: {stat.stdevPct.toFixed(2)}%</span>
                                    </div>
                                    <div className="h-1.5 voxel-trough rounded-none overflow-hidden relative">
                                        <div
                                            className={`h-full rounded-none transition-all duration-500 ${getBarColor(stat.regimeFlag)}`}
                                            style={{
                                                width: `${Math.min(100, Math.max(10, stat.stdevPct > 0 ? (Math.abs(stat.todayPctChange) / (2.0 * stat.stdevPct)) * 100 : 25))}%`,
                                            }}
                                        />
                                    </div>
                                </div>

                                {stat.formattedTime && (
                                    <div className="flex justify-between items-center text-xs font-normal text-voxel-muted font-mono">
                                        <span>Updated</span>
                                        <span className="tabular-nums">{stat.formattedTime}</span>
                                    </div>
                                )}
                            </div>
                        </Card>
                    );
                })}
            </div>
        </section>
    );
}

function RegimeBadge({ flag }: { flag: 'Normal' | '❗ UNUSUAL' | '⚠️ HIGHLY UNUSUAL' }) {
    switch (flag) {
        case '⚠️ HIGHLY UNUSUAL':
            return (
                <Badge variant="soft" colorScheme="danger" size="xs">
                    ⚠️ REGIME SHIFT
                </Badge>
            );
        case '❗ UNUSUAL':
            return (
                <Badge variant="soft" colorScheme="warning" size="xs">
                    ❗ UNUSUAL
                </Badge>
            );
        default:
            return (
                <Badge variant="soft" colorScheme="neutral" size="xs">
                    Normal
                </Badge>
            );
    }
}

function getBarColor(flag: string): string {
    switch (flag) {
        case '⚠️ HIGHLY UNUSUAL':
            return 'bg-alert-red-500 glow-alert';
        case '❗ UNUSUAL':
            return 'bg-amber-500';
        default:
            return 'bg-electric-blue-500';
    }
}
