import { Badge, Button, Card, SectionHeading } from '@llm-market-bench/ui-design-system';
import * as React from 'react';
import type { MacroCategory, MacroStat } from '../lib/macro-tickers';

interface GlobalMacroStatsProps {
    macroStats: MacroStat[];
}

const CATEGORIES: MacroCategory[] = [
    'Equities',
    'International',
    'Commodities',
    'Bonds & Treasury Yields',
    'FX & Risk',
    'Crypto',
];

export function GlobalMacroStats({ macroStats }: GlobalMacroStatsProps) {
    const [activeTab, setActiveTab] = React.useState<MacroCategory>('Equities');

    if (!macroStats || macroStats.length === 0) {
        return null;
    }

    // Index primary hero stats (SPY, QQQ, IWM, VIXY)
    const primaryTickers = ['SPY', 'QQQ', 'IWM', 'VIXY'];
    const heroStats = primaryTickers
        .map((ticker) => macroStats.find((s) => s.ticker === ticker))
        .filter((s): s is MacroStat => !!s);

    // Stats filtered by active category tab
    const filteredStats = macroStats.filter((s) => s.category === activeTab);

    return (
        <section className="space-y-10 animate-slide-up">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-zinc-200 dark:border-zinc-800/80 pb-6">
                <div>
                    <SectionHeading gradient="electric">Global Macro Regime</SectionHeading>
                    <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-1.5 leading-relaxed">
                        Dynamic standard deviations, current price shifts, and volatility regime
                        signals.
                    </p>
                </div>

                <div className="flex items-center gap-2 self-start px-3 py-1.5 bg-electric-blue-500/10 border border-electric-blue-500/20 rounded-xl">
                    <span className="live-dot" />
                    <span className="text-[10px] font-black text-electric-blue-600 dark:text-electric-blue-400 uppercase tracking-widest font-mono">
                        Calculated Live
                    </span>
                </div>
            </div>

            {/* Benchmark Heroes */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 animate-slide-up">
                {heroStats.map((stat, idx) => {
                    const isPositive = stat.todayPctChange >= 0;
                    return (
                        <Card
                            key={`hero-${stat.ticker}`}
                            variant="default"
                            isHoverable
                            radius="2xl"
                            padding="md"
                            className="relative overflow-hidden border border-zinc-200/60 dark:border-zinc-800/60 transition-all duration-300 hover:scale-[1.02] animate-slide-up shadow-sm hover:shadow-md"
                            style={{ animationDelay: `${idx * 75}ms` }}
                        >
                            {/* Accent indicator bar */}
                            <div
                                className={`absolute top-0 left-0 right-0 h-[3px] ${
                                    isPositive ? 'bg-neon-green-500' : 'bg-alert-red-500'
                                }`}
                            />

                            <div className="space-y-3">
                                <div className="flex justify-between items-center">
                                    <span className="text-xs font-black text-zinc-400 dark:text-zinc-500 uppercase tracking-widest font-sans">
                                        {stat.name}
                                    </span>
                                    <span className="text-xs font-black text-zinc-900 dark:text-zinc-100 font-mono">
                                        {stat.ticker}
                                    </span>
                                </div>

                                <div className="flex justify-between items-baseline gap-2">
                                    <span className="text-3xl font-black text-zinc-900 dark:text-white font-mono tracking-tight text-display">
                                        ${stat.price.toFixed(2)}
                                    </span>
                                    <span
                                        className={`text-sm font-black font-mono ${
                                            isPositive
                                                ? 'text-neon-green-500'
                                                : 'text-alert-red-500'
                                        }`}
                                    >
                                        {isPositive ? '↑' : '↓'}{' '}
                                        {Math.abs(stat.todayPctChange).toFixed(2)}%
                                    </span>
                                </div>

                                <div className="flex justify-between items-center pt-2 border-t border-zinc-100 dark:border-zinc-800/60 text-[10px] text-zinc-400 dark:text-zinc-500 font-mono">
                                    <span>30d Stdev: {stat.stdevPct.toFixed(2)}%</span>
                                    <RegimeBadge flag={stat.regimeFlag} />
                                </div>
                            </div>
                        </Card>
                    );
                })}
            </div>

            {/* Category Navigation Tabs */}
            <div className="flex justify-center border-b border-zinc-200 dark:border-zinc-800/80 pb-4 overflow-x-auto scrollbar-none">
                <div className="flex gap-1.5 p-1.5 bg-zinc-100/80 dark:bg-zinc-900/65 backdrop-blur-md rounded-2xl border border-zinc-200/50 dark:border-zinc-800/80 max-w-full">
                    {CATEGORIES.map((cat) => (
                        <Button
                            key={cat}
                            variant={activeTab === cat ? 'solid' : 'ghost'}
                            colorScheme={activeTab === cat ? 'accent' : 'neutral'}
                            onClick={() => setActiveTab(cat)}
                            className="px-4 py-2.5 rounded-xl font-bold text-xs uppercase tracking-wider transition-all duration-200 shrink-0"
                        >
                            {cat}
                        </Button>
                    ))}
                </div>
            </div>

            {/* Bonds & Treasury Yields Explanatory Banner */}
            {activeTab === 'Bonds & Treasury Yields' && (
                <div className="p-4 bg-zinc-50 dark:bg-zinc-900/40 border border-zinc-200 dark:border-zinc-800/80 rounded-2xl flex gap-3.5 items-start animate-scale-in text-sm text-zinc-600 dark:text-zinc-300 leading-relaxed shadow-inner">
                    <span className="text-xl animate-pulse">💡</span>
                    <div>
                        <span className="font-black text-zinc-900 dark:text-white uppercase tracking-wider block mb-1">
                            Bond Prices vs Treasury Yields (Inverse Rule)
                        </span>
                        The S&P 500 benchmark model tracks bond ETFs (`IEF` and `TLT`) directly.
                        Because bond prices move
                        <strong className="text-electric-blue-500 font-bold"> inversely </strong> to
                        market interest yields:
                        <ul className="list-disc list-inside mt-2 space-y-1 text-xs text-zinc-500 dark:text-zinc-400">
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
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                {filteredStats.map((stat, idx) => {
                    const isPositive = stat.todayPctChange >= 0;
                    return (
                        <Card
                            key={stat.ticker}
                            isHoverable
                            radius="2xl"
                            padding="md"
                            className="relative overflow-hidden border border-zinc-200/50 dark:border-zinc-800/80 transition-all duration-300 hover:scale-[1.02] shadow-sm animate-slide-up flex flex-col justify-between"
                            style={{ animationDelay: `${idx * 40}ms` }}
                        >
                            <div className="space-y-4">
                                <div className="flex justify-between items-start gap-2">
                                    <div className="space-y-0.5">
                                        <div className="text-xs font-black text-zinc-400 dark:text-zinc-500 uppercase tracking-widest font-sans">
                                            {stat.name}
                                        </div>
                                        <div className="text-[10px] text-zinc-400 font-mono uppercase tracking-widest">
                                            {stat.ticker}
                                        </div>
                                    </div>
                                    <RegimeBadge flag={stat.regimeFlag} />
                                </div>

                                <div className="flex justify-between items-baseline gap-2">
                                    <span className="text-2xl font-black text-zinc-900 dark:text-white font-mono tracking-tight text-display">
                                        {stat.ticker === 'BTCUSD'
                                            ? `$${stat.price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
                                            : `$${stat.price.toFixed(2)}`}
                                    </span>
                                    <span
                                        className={`text-xs font-black font-mono ${
                                            isPositive
                                                ? 'text-neon-green-500'
                                                : 'text-alert-red-500'
                                        }`}
                                    >
                                        {isPositive ? '↑' : '↓'}{' '}
                                        {Math.abs(stat.todayPctChange).toFixed(2)}%
                                    </span>
                                </div>
                            </div>

                            <div className="pt-4 mt-4 border-t border-zinc-100 dark:border-zinc-800/60 space-y-3">
                                {/* Standard deviation visual index threshold bar */}
                                <div className="space-y-1">
                                    <div className="flex justify-between text-[8px] text-zinc-400 dark:text-zinc-500 uppercase tracking-widest font-mono">
                                        <span>30d Volatility Threshold</span>
                                        <span>Stdev: {stat.stdevPct.toFixed(2)}%</span>
                                    </div>
                                    <div className="h-1 bg-zinc-100 dark:bg-zinc-800/80 rounded-full overflow-hidden relative">
                                        <div
                                            className={`h-full rounded-full transition-all duration-500 ${getBarColor(stat.regimeFlag)}`}
                                            style={{
                                                width: `${Math.min(100, Math.max(10, stat.stdevPct > 0 ? (Math.abs(stat.todayPctChange) / (2.0 * stat.stdevPct)) * 100 : 25))}%`,
                                            }}
                                        />
                                    </div>
                                </div>
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
                <Badge
                    variant="soft"
                    colorScheme="danger"
                    radius="md"
                    className="animate-pulse glow-red border border-alert-red-500/20 font-bold uppercase tracking-widest font-mono text-[8px] px-2 py-0.5"
                >
                    ⚠️ REGIME SHIFT
                </Badge>
            );
        case '❗ UNUSUAL':
            return (
                <Badge
                    variant="soft"
                    colorScheme="warning"
                    radius="md"
                    className="border border-amber-500/20 font-bold uppercase tracking-widest font-mono text-[8px] px-2 py-0.5"
                >
                    ❗ UNUSUAL
                </Badge>
            );
        default:
            return (
                <Badge
                    variant="soft"
                    colorScheme="neutral"
                    radius="md"
                    className="font-bold uppercase tracking-widest font-mono text-[8px] px-2 py-0.5 text-zinc-400 dark:text-zinc-500 bg-zinc-100 dark:bg-zinc-800/40"
                >
                    Normal
                </Badge>
            );
    }
}

function getBarColor(flag: string): string {
    switch (flag) {
        case '⚠️ HIGHLY UNUSUAL':
            return 'bg-alert-red-500 glow-red';
        case '❗ UNUSUAL':
            return 'bg-amber-500';
        default:
            return 'bg-electric-blue-500';
    }
}
