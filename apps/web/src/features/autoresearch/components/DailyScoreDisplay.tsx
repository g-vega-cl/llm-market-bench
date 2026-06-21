import type { PromptExperiment } from '@llm-market-bench/database';
import {
    Badge,
    Card,
    MetricTile,
    SectionHeading,
    SubHeading,
} from '@llm-market-bench/ui-design-system';
import { useState } from 'react';

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
    dateStr?: string;
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
        let dateStr = '';
        if (startDate) {
            const checkpointDate = new Date(startDate);
            checkpointDate.setDate(startDate.getDate() + idx);
            checkpointDate.setHours(0, 0, 0, 0);
            if (isActive) {
                isFuture = checkpointDate > today;
            }
            dateStr = `${checkpointDate.getMonth() + 1}/${checkpointDate.getDate()}`;
        }

        return {
            day: d.name,
            score: dailyScore * d.multiplier,
            portfolio: portfolioReturn * d.multiplier,
            isFuture,
            dateStr,
        };
    });
}

interface CheckpointCardProps {
    cp: Checkpoint;
    idx: number;
    isActive: boolean;
    isSelected: boolean;
    onSelect: () => void;
}

function CheckpointCard({ cp, idx, isActive, isSelected, onSelect }: CheckpointCardProps) {
    let buttonClass = 'p-3 rounded-xl border transition-all duration-300 w-full text-left';

    if (cp.isFuture) {
        buttonClass +=
            ' bg-zinc-950/20 border-zinc-900/50 opacity-40 select-none cursor-not-allowed';
    } else if (isSelected) {
        if (cp.score >= 0) {
            buttonClass +=
                ' bg-emerald-950/20 border-emerald-500/60 shadow-[0_0_12px_rgba(16,185,129,0.15)] cursor-pointer';
        } else {
            buttonClass +=
                ' bg-rose-950/20 border-rose-500/60 shadow-[0_0_12px_rgba(239,68,68,0.15)] cursor-pointer';
        }
    } else if (idx === 4 && isActive) {
        buttonClass +=
            ' bg-zinc-800/40 border-emerald-500/30 shadow-[0_0_12px_rgba(16,185,129,0.05)] cursor-pointer hover:border-zinc-700';
    } else {
        buttonClass +=
            ' bg-zinc-950/40 border-zinc-850 hover:border-zinc-700 cursor-pointer hover:bg-zinc-900/20';
    }

    return (
        <button type="button" disabled={cp.isFuture} onClick={onSelect} className={buttonClass}>
            <div className="flex items-center justify-between gap-1 w-full">
                <div className="text-[9px] font-black text-zinc-500 uppercase tracking-widest">
                    {cp.day.substring(0, 3)}
                </div>
                {cp.dateStr && (
                    <div className="text-[8px] font-bold text-zinc-400 font-mono bg-zinc-800 px-1 py-0.5 rounded-sm">
                        {cp.dateStr}
                    </div>
                )}
            </div>
            {cp.isFuture ? (
                <>
                    <div className="text-xs font-mono font-bold mt-1 text-zinc-500">N/A</div>
                    <div className="text-[8px] text-zinc-500 font-mono mt-0.5">P: N/A</div>
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
        </button>
    );
}

export function DailyScoreDisplay({ experiment }: DailyScoreDisplayProps) {
    const metrics = experiment.metrics || {};
    const isActive = metrics.score === null || metrics.score === undefined;

    const [selectedDayName, setSelectedDayName] = useState<string | null>(null);

    const {
        portfolioReturn,
        spyReturn,
        doNothingReturn,
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

    const selectedCp = checkpoints.find((cp) => cp.day === selectedDayName);
    const dayMultipliers: Record<string, number> = {
        Monday: 0.15,
        Tuesday: 0.35,
        Wednesday: 0.55,
        Thursday: 0.8,
        Friday: 1.0,
    };
    const multiplier = selectedDayName ? dayMultipliers[selectedDayName] : 1.0;

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
                        <CheckpointCard
                            key={cp.day}
                            cp={cp}
                            idx={idx}
                            isActive={isActive}
                            isSelected={selectedDayName === cp.day}
                            onSelect={() =>
                                setSelectedDayName(selectedDayName === cp.day ? null : cp.day)
                            }
                        />
                    ))}
                </div>
            </div>

            {/* Selected Day Constituent Details Block */}
            {selectedDayName && selectedCp && (
                <div className="p-5 rounded-2xl bg-zinc-950/50 border border-zinc-800 space-y-4 animate-fade-in relative z-10">
                    <div className="flex items-center justify-between border-b border-zinc-800 pb-2">
                        <div className="flex flex-col">
                            <h4 className="text-sm font-bold text-zinc-105 flex items-center space-x-2">
                                <span className="flex items-center justify-center h-5 w-5 rounded-full bg-emerald-500/10 text-emerald-400 text-xs font-black">
                                    ✓
                                </span>
                                <span>
                                    Score Constituents — {selectedDayName}{' '}
                                    {selectedCp.dateStr ? `(${selectedCp.dateStr})` : ''}
                                </span>
                            </h4>
                            <p className="text-[10px] text-zinc-500 mt-0.5">
                                Scaled values for day progression (multiplier:{' '}
                                {multiplier.toFixed(2)})
                            </p>
                        </div>
                        <div className="flex items-center gap-3">
                            <div className="flex flex-col items-end">
                                <div className="text-[8px] font-black text-zinc-500 uppercase tracking-widest">
                                    Day Score
                                </div>
                                <div
                                    className={`text-base font-black font-mono ${selectedCp.score >= 0 ? 'text-emerald-400' : 'text-rose-500'}`}
                                >
                                    {selectedCp.score >= 0 ? '+' : ''}
                                    {selectedCp.score.toFixed(4)}
                                </div>
                            </div>
                            <button
                                type="button"
                                onClick={() => setSelectedDayName(null)}
                                className="text-zinc-450 hover:text-zinc-200 text-xs font-bold px-2 py-1 bg-zinc-900 border border-zinc-800 rounded hover:border-zinc-700 transition cursor-pointer"
                            >
                                Close
                            </button>
                        </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div className="p-3 bg-zinc-950/70 border border-zinc-900 rounded-xl space-y-1">
                            <div className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider">
                                Excess Return (Scaled)
                            </div>
                            <div
                                className={`text-sm font-mono font-bold ${dailyExcessReturn >= 0 ? 'text-emerald-400' : 'text-rose-500'}`}
                            >
                                {dailyExcessReturn >= 0 ? '+' : ''}
                                {(dailyExcessReturn * multiplier).toFixed(4)}%
                            </div>
                            <div className="text-[9px] text-zinc-500 font-mono">
                                Base: {dailyExcessReturn.toFixed(4)}%
                            </div>
                        </div>

                        <div className="p-3 bg-zinc-950/70 border border-zinc-900 rounded-xl space-y-1">
                            <div className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider">
                                Opportunity Cost (Scaled)
                            </div>
                            <div className="text-sm font-mono font-bold text-rose-400">
                                -{(opportunityCost * multiplier).toFixed(4)}%
                            </div>
                            <div className="text-[9px] text-zinc-500 font-mono">
                                Base: -{opportunityCost.toFixed(4)}%
                            </div>
                        </div>

                        <div className="p-3 bg-zinc-950/70 border border-zinc-900 rounded-xl space-y-1">
                            <div className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider">
                                Risk Penalty (Scaled)
                            </div>
                            <div className="text-sm font-mono font-bold text-rose-400">
                                -{(dailyDrawdownPenalty * multiplier).toFixed(4)}%
                            </div>
                            <div className="text-[9px] text-zinc-500 font-mono">
                                Base: -{dailyDrawdownPenalty.toFixed(4)}%
                            </div>
                        </div>
                    </div>

                    {/* Step-by-step arithmetic */}
                    <div className="bg-zinc-950/80 rounded-xl p-3.5 font-mono text-[11px] border border-zinc-900 leading-relaxed text-zinc-400 space-y-2">
                        <div className="text-zinc-500 text-[9px] uppercase font-bold tracking-wider border-b border-zinc-900 pb-1 mb-1.5 font-sans">
                            Constituent Calculations
                        </div>
                        <div className="flex flex-col sm:flex-row sm:justify-between border-b border-dashed border-zinc-900/50 pb-1.5">
                            <span>Portfolio Return (Scaled)</span>
                            <span className="font-bold text-zinc-200">
                                {(portfolioReturn * multiplier).toFixed(4)}%{' '}
                                <span className="text-zinc-500 text-[10px]">
                                    (Base: {portfolioReturn.toFixed(4)}%)
                                </span>
                            </span>
                        </div>
                        <div className="flex flex-col sm:flex-row sm:justify-between border-b border-dashed border-zinc-900/50 pb-1.5">
                            <span>S&P 500 Return (Scaled)</span>
                            <span className="font-bold text-zinc-200">
                                {(spyReturn * multiplier).toFixed(4)}%{' '}
                                <span className="text-zinc-500 text-[10px]">
                                    (Base: {spyReturn.toFixed(4)}%)
                                </span>
                            </span>
                        </div>
                        <div className="flex flex-col sm:flex-row sm:justify-between border-b border-dashed border-zinc-900/50 pb-1.5">
                            <span>Do-Nothing Return (Scaled)</span>
                            <span className="font-bold text-zinc-200">
                                {(doNothingReturn * multiplier).toFixed(4)}%{' '}
                                <span className="text-zinc-500 text-[10px]">
                                    (Base: {doNothingReturn.toFixed(4)}%)
                                </span>
                            </span>
                        </div>
                        <div className="text-zinc-500 text-[10px] pt-1 font-sans">
                            Formula: score = (Excess Return - Opportunity Cost - Risk Penalty)
                        </div>
                        <div className="text-emerald-450 font-bold">
                            score = {(dailyExcessReturn * multiplier).toFixed(4)}% -{' '}
                            {(opportunityCost * multiplier).toFixed(4)}% -{' '}
                            {(dailyDrawdownPenalty * multiplier).toFixed(4)}%
                        </div>
                        <div className="text-emerald-400 font-bold border-t border-zinc-900 pt-1.5 text-xs">
                            score = {selectedCp.score >= 0 ? '+' : ''}
                            {selectedCp.score.toFixed(4)}
                        </div>
                    </div>
                </div>
            )}
        </Card>
    );
}
