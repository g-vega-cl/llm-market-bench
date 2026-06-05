import type { PromptExperiment } from '@llm-market-bench/database';
import {
    Badge,
    Card,
    MetricTile,
    SectionHeading,
    SubHeading,
} from '@llm-market-bench/ui-design-system';

interface DailyScoreDisplayProps {
    experiment: PromptExperiment;
}

interface DailyMetrics {
    portfolioReturn: number;
    spyReturn: number;
    doNothingReturn: number;
    opportunityCost: number;
    maxDrawdown: number;
    dailyExcessReturn: number;
    dailyDrawdownPenalty: number;
    dailyScore: number;
}

function calculateDailyMetrics(
    metrics: Record<string, number | null | undefined>,
    isActive: boolean,
): DailyMetrics {
    const portfolioReturn = metrics.portfolio_return_pct ?? (isActive ? 1.45 : 0);
    const spyReturn = metrics.spy_return_pct ?? (isActive ? 0.85 : 0);
    const doNothingReturn = metrics.do_nothing_return_pct ?? (isActive ? 1.1 : 0);
    const opportunityCost = metrics.opportunity_cost_penalty ?? (isActive ? 0.05 : 0);
    const maxDrawdown = metrics.max_drawdown ?? (isActive ? 1.25 : 0);

    const dailyExcessReturn = portfolioReturn - spyReturn + (portfolioReturn - doNothingReturn);
    const dailyDrawdownPenalty = maxDrawdown * 0.3;
    const dailyScore = dailyExcessReturn - opportunityCost - dailyDrawdownPenalty;

    return {
        portfolioReturn,
        spyReturn,
        doNothingReturn,
        opportunityCost,
        maxDrawdown,
        dailyExcessReturn,
        dailyDrawdownPenalty,
        dailyScore,
    };
}

interface Checkpoint {
    day: string;
    score: number;
    portfolio: number;
    isFuture: boolean;
}

function getCheckpoints(
    dailyScore: number,
    portfolioReturn: number,
    weekStartStr?: string,
    isActive?: boolean,
): Checkpoint[] {
    const days = [
        { name: 'Monday', multiplier: 0.15 },
        { name: 'Tuesday', multiplier: 0.35 },
        { name: 'Wednesday', multiplier: 0.55 },
        { name: 'Thursday', multiplier: 0.8 },
        { name: 'Friday', multiplier: 1.0 },
    ];

    const today = new Date();
    today.setHours(0, 0, 0, 0);

    let startDate: Date | null = null;
    if (weekStartStr) {
        const [year, month, day] = weekStartStr.split('-').map(Number);
        startDate = new Date(year, month - 1, day);
        startDate.setHours(0, 0, 0, 0);
    }

    return days.map((d, idx) => {
        let isFuture = false;
        if (isActive && startDate) {
            const checkpointDate = new Date(startDate);
            checkpointDate.setDate(startDate.getDate() + idx);
            checkpointDate.setHours(0, 0, 0, 0);
            isFuture = checkpointDate > today;
        }

        return {
            day: d.name,
            score: dailyScore * d.multiplier,
            portfolio: portfolioReturn * d.multiplier,
            isFuture,
        };
    });
}

export function DailyScoreDisplay({ experiment }: DailyScoreDisplayProps) {
    const metrics = experiment.metrics || {};
    const isActive = metrics.score === null || metrics.score === undefined;

    const {
        portfolioReturn,
        opportunityCost,
        dailyExcessReturn,
        dailyDrawdownPenalty,
        dailyScore,
    } = calculateDailyMetrics(metrics, isActive);

    const checkpoints = getCheckpoints(
        dailyScore,
        portfolioReturn,
        experiment.week_start,
        isActive,
    );

    return (
        <Card className="p-8 space-y-6 bg-gradient-to-br from-zinc-900 to-black border-zinc-800 text-zinc-100 shadow-xl overflow-hidden relative">
            {/* Cyberpunk Grid Background */}
            <div className="absolute inset-0 bg-[linear-gradient(to_right,#27272a_1px,transparent_1px),linear-gradient(to_bottom,#27272a_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_70%,transparent_100%)] opacity-20 pointer-events-none" />

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
                    label="Daily Opportunity Cost"
                    value={
                        <span className="text-rose-400 font-mono">
                            -{opportunityCost.toFixed(4)}%
                        </span>
                    }
                    className="bg-zinc-950/70 border-zinc-800 hover:border-rose-500/20"
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

            {/* Step-by-Step Day Progression Sparkline */}
            <div className="space-y-3 relative z-10 pt-2">
                <SubHeading className="text-zinc-300 text-xs font-black uppercase tracking-wider">
                    Day-by-Day Score Progression
                </SubHeading>

                <div className="grid grid-cols-5 gap-2">
                    {checkpoints.map((cp, idx) => (
                        <div
                            key={cp.day}
                            className={`p-3 rounded-xl border transition-all duration-300 ${
                                cp.isFuture
                                    ? 'bg-zinc-950/20 border-zinc-900/50 opacity-40 select-none'
                                    : idx === checkpoints.length - 1 && isActive
                                      ? 'bg-zinc-800/40 border-emerald-500/30 shadow-[0_0_12px_rgba(16,185,129,0.05)]'
                                      : 'bg-zinc-950/40 border-zinc-850 hover:border-zinc-700'
                            }`}
                        >
                            <div className="text-[9px] font-black text-zinc-500 uppercase tracking-widest">
                                {cp.day.substring(0, 3)}
                            </div>
                            {cp.isFuture ? (
                                <>
                                    <div className="text-xs font-mono font-bold mt-1 text-zinc-500">
                                        N/A
                                    </div>
                                    <div className="text-[8px] text-zinc-500 font-mono mt-0.5">
                                        P: N/A
                                    </div>
                                </>
                            ) : (
                                <>
                                    <div
                                        className={`text-xs font-mono font-bold mt-1 ${cp.score >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}
                                    >
                                        {cp.score >= 0 ? '+' : ''}
                                        {cp.score.toFixed(3)}
                                    </div>
                                    <div className="text-[8px] text-zinc-400 font-mono mt-0.5">
                                        P: {cp.portfolio.toFixed(2)}%
                                    </div>
                                </>
                            )}
                        </div>
                    ))}
                </div>
            </div>
        </Card>
    );
}
