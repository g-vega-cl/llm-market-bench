import { Badge, MetricTile, SectionHeading } from '@llm-market-bench/ui-design-system';

interface DailyScoreOverviewProps {
    isActive: boolean;
    dailyScore: number;
    dailyExcessReturn: number;
    opportunityCost: number;
    dailyDrawdownPenalty: number;
}

export function DailyScoreOverview({
    isActive,
    dailyScore,
    dailyExcessReturn,
    opportunityCost,
    dailyDrawdownPenalty,
}: DailyScoreOverviewProps) {
    return (
        <>
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 relative z-10">
                <div className="space-y-1">
                    <div className="flex items-center gap-2">
                        <SectionHeading className="text-zinc-50 dark:text-zinc-50 font-black tracking-tight">
                            Daily Autoresearch Score
                        </SectionHeading>
                        {isActive ? (
                            <div className="flex items-center gap-1.5 bg-emerald-500/10 border border-emerald-500/30 px-2 py-0.5 rounded text-[10px] font-black uppercase text-emerald-400 tracking-wider animate-pulse">
                                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 shadow-[0_0_8px_#34d399]" />
                                LIVE TRACKING
                            </div>
                        ) : (
                            <Badge
                                variant="soft"
                                className="text-xs bg-zinc-800 border border-zinc-700 text-zinc-300"
                            >
                                COMPLETED WEEK
                            </Badge>
                        )}
                    </div>
                    <p className="text-zinc-400 text-xs max-w-lg">
                        Real-time daily evaluation of the Meta-Researcher prompt performance against
                        active benchmark parameters.
                    </p>
                </div>

                <div className="flex flex-col items-end">
                    <div className="text-[10px] font-black text-zinc-500 uppercase tracking-widest">
                        Running Score
                    </div>
                    <div
                        className={`text-3xl font-black font-mono tracking-tight ${dailyScore >= 0 ? 'text-emerald-400 drop-shadow-[0_0_10px_rgba(52,211,153,0.15)]' : 'text-rose-500'}`}
                    >
                        {dailyScore >= 0 ? '+' : ''}
                        {dailyScore.toFixed(4)}
                    </div>
                </div>
            </div>

            {/* Daily Metric Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 relative z-10">
                <MetricTile
                    icon="⚡"
                    label="Daily Excess Return"
                    value={
                        <span
                            className={
                                dailyExcessReturn >= 0 ? 'text-emerald-400' : 'text-rose-500'
                            }
                        >
                            {dailyExcessReturn >= 0 ? '+' : ''}
                            {dailyExcessReturn.toFixed(4)}%
                        </span>
                    }
                    className="bg-zinc-950/70 border-zinc-800 hover:border-emerald-500/20"
                />
                <MetricTile
                    icon="⏳"
                    label="Risk-Free Excess (vs 10Y Bond)"
                    value={
                        <span
                            className={
                                opportunityCost >= 0
                                    ? 'text-emerald-400 font-mono'
                                    : 'text-rose-400 font-mono'
                            }
                        >
                            {opportunityCost >= 0 ? '+' : ''}
                            {opportunityCost.toFixed(4)}%
                        </span>
                    }
                    className="bg-zinc-950/70 border-zinc-800 hover:border-emerald-500/20"
                />
                <MetricTile
                    icon="🛡️"
                    label="Daily Risk Penalty"
                    value={
                        <span className="text-rose-400 font-mono">
                            -{dailyDrawdownPenalty.toFixed(4)}%
                        </span>
                    }
                    className="bg-zinc-950/70 border-zinc-800 hover:border-rose-500/20"
                />
            </div>
        </>
    );
}
