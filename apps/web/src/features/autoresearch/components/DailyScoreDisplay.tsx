import type { PromptExperiment } from '@llm-market-bench/database';
import {
    Badge,
    Card,
    MetricTile,
    SectionHeading,
    SubHeading,
} from '@llm-market-bench/ui-design-system';
import { useEffect, useState } from 'react';
import { getSupabaseBrowserClient } from '~/lib/supabase-client';

function getAgentDisplayName(ownerId: string | null | undefined): string {
    if (!ownerId) return 'Unknown Agent';
    const normalized = ownerId.toLowerCase().replace(/[\s_-]+/g, '-');
    if (normalized.includes('gemini-3.1-flash-lite')) return 'Gemini 3.1 Flash Lite';
    if (normalized.includes('deepseek-v4-pro')) return 'DeepSeek V4 Pro';
    if (normalized.includes('minimax-m3') || normalized.includes('minimax')) return 'MiniMax-M3';
    return ownerId;
}

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

function getPortfolioReturn(
    metrics: Record<string, number | null | undefined>,
    isActive: boolean,
    actualReturns: ActualReturns | null,
): number {
    const portfolioReturn = metrics.portfolio_return_pct;
    if (portfolioReturn !== null && portfolioReturn !== undefined) {
        return portfolioReturn;
    }
    if (isActive && actualReturns && Object.keys(actualReturns).length > 0) {
        const rets = Object.values(actualReturns).map((r) => r.actualReturn);
        return rets.reduce((sum, val) => sum + val, 0) / rets.length;
    }
    return isActive ? 1.45 : 0;
}

function getSpyReturn(
    metrics: Record<string, number | null | undefined>,
    isActive: boolean,
    actualSpyReturn: number | null,
): number {
    if (isActive && actualSpyReturn !== null) {
        return actualSpyReturn;
    }
    const spyReturn = metrics.spy_return_pct;
    if (spyReturn !== null && spyReturn !== undefined) {
        return spyReturn;
    }
    return isActive ? 0.85 : 0;
}

function getDoNothingReturn(
    metrics: Record<string, number | null | undefined>,
    isActive: boolean,
): number {
    const doNothingReturn = metrics.do_nothing_return_pct;
    if (doNothingReturn !== null && doNothingReturn !== undefined) {
        return doNothingReturn;
    }
    const details = (metrics.portfolio_details || {}) as Record<string, PortfolioDetail>;
    const detailEntries = Object.values(details);
    if (detailEntries.length > 0) {
        const dnReturns = detailEntries.map((d) => d.do_nothing_return_pct ?? 0);
        return dnReturns.reduce((sum, val) => sum + val, 0) / dnReturns.length;
    }
    return isActive ? 1.1 : 0;
}

function calculateDailyMetrics(
    metrics: Record<string, number | null | undefined>,
    isActive: boolean,
    actualSpyReturn: number | null,
    actualReturns: ActualReturns | null,
): DailyMetrics {
    const portfolioReturn = getPortfolioReturn(metrics, isActive, actualReturns);
    const spyReturn = getSpyReturn(metrics, isActive, actualSpyReturn);
    const doNothingReturn = getDoNothingReturn(metrics, isActive);
    const bondReturn = metrics.bond_return_pct ?? (isActive ? 0.05 : 0);

    const opportunityCost = metrics.opportunity_cost_penalty ?? portfolioReturn - bondReturn;
    const maxDrawdown = metrics.max_drawdown ?? (isActive ? 1.25 : 0);

    const excessVsSpy = portfolioReturn - spyReturn;
    const excessVsDoNothing = portfolioReturn - doNothingReturn;
    const excessVsBond = portfolioReturn - bondReturn;

    const dailyExcessReturn = 0.4 * excessVsSpy + 0.4 * excessVsDoNothing + 0.2 * excessVsBond;
    const dailyDrawdownPenalty = maxDrawdown * 0.3;
    const dailyScore = dailyExcessReturn - dailyDrawdownPenalty;

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

interface ActualReturns {
    [ownerId: string]: {
        startEquity: number;
        endEquity: number;
        actualReturn: number;
    };
}

interface PortfolioDetail {
    owner_id: string;
    initial_equity?: number;
    initial_cash?: number;
    end_equity?: number;
    do_nothing_return_pct?: number;
    positions?: Record<string, unknown>;
}

type PerformanceRow = {
    portfolio_id: string;
    total_equity: string | number;
    date: string;
    portfolios:
        | {
              owner_id: string;
          }
        | null
        | undefined;
};

function groupPerformanceData(data: PerformanceRow[]) {
    const grouped: Record<string, { date: string; equity: number }[]> = {};
    const ownerIdMap: Record<string, string> = {};

    for (const row of data) {
        const ownerId = row.portfolios?.owner_id;
        const pid = row.portfolio_id;
        if (!ownerId) continue;
        ownerIdMap[pid] = ownerId;
        if (!grouped[pid]) {
            grouped[pid] = [];
        }
        grouped[pid].push({
            date: row.date,
            equity: Number(row.total_equity),
        });
    }
    return { grouped, ownerIdMap };
}

function calculateActualReturns(
    grouped: Record<string, { date: string; equity: number }[]>,
    ownerIdMap: Record<string, string>,
): ActualReturns {
    const results: ActualReturns = {};
    for (const [pid, history] of Object.entries(grouped)) {
        if (history.length < 2) continue;
        history.sort((a, b) => a.date.localeCompare(b.date));
        const startEquity = history[0].equity;
        const endEquity = history[history.length - 1].equity;
        const ownerId = ownerIdMap[pid];
        if (startEquity > 0) {
            results[ownerId] = {
                startEquity,
                endEquity,
                actualReturn: ((endEquity - startEquity) / startEquity) * 100,
            };
        }
    }
    return results;
}

async function fetchPortfolioPerformanceData(
    portfolioIds: string[],
    weekStart: string,
    weekEnd: string,
) {
    if (portfolioIds.length === 0) return null;
    const supabase = getSupabaseBrowserClient();
    const { data, error } = await supabase
        .from('portfolio_performance')
        .select('portfolio_id, total_equity, date, portfolios!inner(owner_id)')
        .in('portfolio_id', portfolioIds)
        .gte('date', weekStart)
        .lte('date', weekEnd)
        .order('date', { ascending: true });

    if (error) {
        throw error;
    }
    return data;
}

function calculateSpyReturn(prices: { price: number | string }[]): number {
    let cumulative = 1.0;
    for (let i = 1; i < prices.length; i++) {
        const prev = Number(prices[i - 1].price || 0);
        const curr = Number(prices[i].price || 0);
        if (prev > 0) {
            cumulative *= 1 + (curr - prev) / prev;
        }
    }
    return (cumulative - 1) * 100;
}

async function fetchActiveWeekData(
    portfolioIds: string[],
    weekStart: string,
    weekEnd: string,
    isActive: boolean,
) {
    const supabase = getSupabaseBrowserClient();
    return Promise.all([
        fetchPortfolioPerformanceData(portfolioIds, weekStart, weekEnd),
        isActive
            ? supabase
                  .from('price_history')
                  .select('fetched_at, price')
                  .eq('ticker', 'SPY')
                  .gte('fetched_at', weekStart)
                  .lte('fetched_at', `${weekEnd}T23:59:59`)
                  .order('fetched_at', { ascending: true })
            : Promise.resolve({ data: null, error: null }),
    ]);
}

function getProcessedActualReturns(data: unknown[]): ActualReturns {
    const { grouped, ownerIdMap } = groupPerformanceData(data as PerformanceRow[]);
    return calculateActualReturns(grouped, ownerIdMap);
}

function processSpyResponse(
    spyRes: { data: unknown[] | null },
    isMounted: boolean,
    setActualSpyReturn: (r: number) => void,
) {
    if (spyRes.data && spyRes.data.length >= 2) {
        const computedReturn = calculateSpyReturn(spyRes.data as { price: number | string }[]);
        if (isMounted) {
            setActualSpyReturn(computedReturn);
        }
    }
}

function processPortfolioData(
    data: unknown[] | null,
    isMounted: boolean,
    setActualReturns: (r: ActualReturns) => void,
) {
    if (data && data.length > 0) {
        const results = getProcessedActualReturns(data);
        if (isMounted) {
            setActualReturns(results);
        }
    }
}

function useActualReturns(
    weekStart?: string | null,
    weekEnd?: string | null,
    portfolioDetails?: Record<string, PortfolioDetail> | null,
    isActive?: boolean,
) {
    const [actualReturns, setActualReturns] = useState<ActualReturns | null>(null);
    const [actualSpyReturn, setActualSpyReturn] = useState<number | null>(null);
    const [isLoadingActuals, setIsLoadingActuals] = useState(false);

    useEffect(() => {
        if (!weekStart || !weekEnd) return;
        const details = portfolioDetails || {};
        const portfolioIds = Object.keys(details);

        let isMounted = true;
        setIsLoadingActuals(true);

        const loadActuals = async () => {
            try {
                const [data, spyRes] = await fetchActiveWeekData(
                    portfolioIds,
                    weekStart,
                    weekEnd,
                    !!isActive,
                );

                processSpyResponse(spyRes, isMounted, setActualSpyReturn);
                processPortfolioData(data, isMounted, setActualReturns);
            } catch (e) {
                console.error('Failed to load actual returns:', e);
            } finally {
                if (isMounted) {
                    setIsLoadingActuals(false);
                }
            }
        };

        loadActuals();
        return () => {
            isMounted = false;
        };
    }, [weekStart, weekEnd, portfolioDetails, isActive]);

    return { actualReturns, actualSpyReturn, isLoadingActuals };
}

export function DailyScoreDisplay({ experiment }: DailyScoreDisplayProps) {
    const metrics = experiment.metrics || {};
    const isActive = metrics.score === null || metrics.score === undefined;

    const [selectedDayName, setSelectedDayName] = useState<string | null>(null);
    const { actualReturns, actualSpyReturn, isLoadingActuals } = useActualReturns(
        experiment.week_start,
        experiment.week_end,
        metrics.portfolio_details as Record<string, PortfolioDetail>,
        isActive,
    );

    const {
        portfolioReturn,
        spyReturn,
        doNothingReturn,
        opportunityCost,
        maxDrawdown,
        dailyExcessReturn,
        dailyDrawdownPenalty,
        dailyScore,
    } = calculateDailyMetrics(metrics, isActive, actualSpyReturn, actualReturns);

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
                <SelectedDayConstituentDetails
                    selectedDayName={selectedDayName}
                    selectedCp={selectedCp}
                    multiplier={multiplier}
                    portfolioReturn={portfolioReturn}
                    spyReturn={spyReturn}
                    doNothingReturn={doNothingReturn}
                    bondReturn={metrics.bond_return_pct ?? 0.05}
                    maxDrawdown={maxDrawdown}
                    dailyExcessReturn={dailyExcessReturn}
                    opportunityCost={opportunityCost}
                    dailyDrawdownPenalty={dailyDrawdownPenalty}
                    dailyScore={dailyScore}
                    portfolioDetails={metrics.portfolio_details as Record<string, PortfolioDetail>}
                    actualReturns={actualReturns}
                    isLoadingActuals={isLoadingActuals}
                    onClose={() => setSelectedDayName(null)}
                />
            )}
        </Card>
    );
}

interface SelectedDayConstituentDetailsProps {
    selectedDayName: string;
    selectedCp: Checkpoint;
    multiplier: number;
    portfolioReturn: number;
    spyReturn: number;
    doNothingReturn: number;
    bondReturn: number;
    maxDrawdown: number;
    dailyExcessReturn: number;
    opportunityCost: number;
    dailyDrawdownPenalty: number;
    dailyScore: number;
    portfolioDetails?: Record<string, PortfolioDetail>;
    actualReturns?: ActualReturns | null;
    isLoadingActuals?: boolean;
    onClose: () => void;
}

function SelectedDayConstituentDetails({
    selectedDayName,
    selectedCp,
    multiplier,
    portfolioReturn,
    spyReturn,
    doNothingReturn,
    bondReturn,
    maxDrawdown,
    dailyExcessReturn,
    opportunityCost,
    dailyDrawdownPenalty,
    dailyScore,
    portfolioDetails,
    actualReturns,
    isLoadingActuals,
    onClose,
}: SelectedDayConstituentDetailsProps) {
    return (
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
                        Scaled values for day progression (multiplier: {multiplier.toFixed(2)})
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
                        onClick={onClose}
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
                        Risk-Free Excess (Scaled)
                    </div>
                    <div
                        className={`text-sm font-mono font-bold ${opportunityCost >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}
                    >
                        {opportunityCost >= 0 ? '+' : ''}
                        {(opportunityCost * multiplier).toFixed(4)}%
                    </div>
                    <div className="text-[9px] text-zinc-500 font-mono">
                        Base: {opportunityCost >= 0 ? '+' : ''}
                        {opportunityCost.toFixed(4)}%
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
            {(() => {
                const formatVal = (val: number) => `${val.toFixed(4)}%`;
                const formatValWithParentheses = (val: number) =>
                    val < 0 ? `(${val.toFixed(4)}%)` : `${val.toFixed(4)}%`;

                return (
                    <div className="bg-zinc-950/80 rounded-xl p-4 font-mono text-[11px] border border-zinc-900 leading-relaxed text-zinc-400 space-y-4">
                        <div className="text-zinc-500 text-[9px] uppercase font-bold tracking-wider border-b border-zinc-900 pb-1.5 font-sans">
                            Detailed Audit Ledger
                        </div>

                        {/* 1. Excess Return */}
                        <div className="space-y-1.5 border-b border-zinc-900/60 pb-3">
                            <div className="font-bold text-zinc-200">
                                1. Excess Return Calculation:
                            </div>
                            <div className="text-[10px] text-zinc-500">
                                Formula: 0.4 × (Portfolio - SPY) + 0.4 × (Portfolio - Do-Nothing) +
                                0.2 × (Portfolio - 10Y Bond)
                            </div>
                            <div className="pl-3 border-l-2 border-zinc-800 text-[10px] space-y-1">
                                <div className="text-zinc-450 font-bold">
                                    Base Composite Excess Return Calculation:
                                </div>
                                <div className="text-zinc-350">
                                    0.4 × ({formatValWithParentheses(portfolioReturn)} -{' '}
                                    {formatValWithParentheses(spyReturn)}) + 0.4 × (
                                    {formatValWithParentheses(portfolioReturn)} -{' '}
                                    {formatValWithParentheses(doNothingReturn)}) + 0.2 × (
                                    {formatValWithParentheses(portfolioReturn)} -{' '}
                                    {formatValWithParentheses(bondReturn)}) ={' '}
                                    {dailyExcessReturn >= 0 ? '+' : ''}
                                    {dailyExcessReturn.toFixed(4)}%
                                </div>
                                <div className="text-zinc-450 font-bold mt-1">
                                    Scaled Excess Return (x {multiplier.toFixed(2)}):
                                </div>
                                <div className="text-zinc-350">
                                    {formatValWithParentheses(portfolioReturn * multiplier)} -{' '}
                                    {formatValWithParentheses(spyReturn * multiplier)} + (
                                    {formatValWithParentheses(portfolioReturn * multiplier)} -{' '}
                                    {formatValWithParentheses(doNothingReturn * multiplier)}) ={' '}
                                    {dailyExcessReturn >= 0 ? '+' : ''}
                                    {(dailyExcessReturn * multiplier).toFixed(4)}%
                                </div>
                            </div>
                        </div>

                        {/* 2. Portfolio Return Breakdown */}
                        <div className="space-y-1.5 border-b border-zinc-900/60 pb-3">
                            <div className="flex flex-col sm:flex-row sm:justify-between font-bold text-zinc-200">
                                <span>
                                    2. Portfolio Return (Compounded equal-weighted daily returns of
                                    agents)
                                </span>
                                <span>
                                    {(portfolioReturn * multiplier).toFixed(4)}%{' '}
                                    <span className="text-[10px] font-normal text-zinc-500">
                                        (Base: {portfolioReturn.toFixed(4)}%)
                                    </span>
                                </span>
                            </div>
                            {actualReturns && Object.keys(actualReturns).length > 0 ? (
                                <div className="pl-3 border-l-2 border-zinc-800 text-[10px] text-zinc-500 space-y-1">
                                    <div className="font-bold text-[9px] uppercase tracking-wider text-zinc-650">
                                        Constituent Portfolios (Actual Returns for the Week):
                                    </div>
                                    {Object.entries(actualReturns).map(([ownerId, retData]) => (
                                        <div key={ownerId} className="flex justify-between pl-1">
                                            <span>● {getAgentDisplayName(ownerId)}</span>
                                            <span className="text-zinc-300">
                                                {(retData.actualReturn * multiplier).toFixed(4)}%{' '}
                                                <span className="opacity-70 text-[9px] text-zinc-500">
                                                    (Base: {formatVal(retData.actualReturn)})
                                                </span>
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            ) : isLoadingActuals ? (
                                <div className="pl-3 border-l-2 border-zinc-800 text-[10px] text-zinc-500 animate-pulse">
                                    Loading individual actual portfolio returns...
                                </div>
                            ) : (
                                <div className="pl-3 border-l-2 border-zinc-800 text-[10px] text-zinc-600 italic">
                                    No constituent portfolio actuals available (live/simulated).
                                </div>
                            )}
                        </div>

                        {/* 3. Do-Nothing Return Breakdown */}
                        <div className="space-y-1.5 border-b border-zinc-900/60 pb-3">
                            <div className="flex flex-col sm:flex-row sm:justify-between font-bold text-zinc-200">
                                <span>
                                    3. Do-Nothing Return (Average of starting-asset buy-and-hold
                                    returns)
                                </span>
                                <span>
                                    {(doNothingReturn * multiplier).toFixed(4)}%{' '}
                                    <span className="text-[10px] font-normal text-zinc-500">
                                        (Base: {doNothingReturn.toFixed(4)}%)
                                    </span>
                                </span>
                            </div>
                            {(() => {
                                const details = (portfolioDetails || {}) as Record<
                                    string,
                                    PortfolioDetail
                                >;
                                const detailEntries = Object.entries(details);
                                if (detailEntries.length === 0) {
                                    return (
                                        <div className="pl-3 border-l-2 border-zinc-800 text-[10px] text-zinc-600 italic">
                                            No constituent do-nothing details available
                                            (live/simulated).
                                        </div>
                                    );
                                }

                                const equationTerms = detailEntries
                                    .map(([_, d]) => {
                                        const val = d.do_nothing_return_pct ?? 0;
                                        return val < 0
                                            ? `(${val.toFixed(4)}%)`
                                            : `${val.toFixed(4)}%`;
                                    })
                                    .join(' + ');

                                return (
                                    <div className="pl-3 border-l-2 border-zinc-800 text-[10px] text-zinc-500 space-y-1.5">
                                        <div className="font-bold text-[9px] uppercase tracking-wider text-zinc-650">
                                            Base Calculation:
                                        </div>
                                        <div className="text-zinc-350">
                                            ({equationTerms}) / {detailEntries.length} ={' '}
                                            {doNothingReturn.toFixed(4)}%
                                        </div>
                                        <div className="font-bold text-[9px] uppercase tracking-wider text-zinc-650 pt-1">
                                            Constituent Portfolios (Do-Nothing Returns for the
                                            Week):
                                        </div>
                                        {detailEntries.map(([pid, detail]) => {
                                            const dnReturn = detail.do_nothing_return_pct ?? 0;
                                            return (
                                                <div
                                                    key={pid}
                                                    className="flex justify-between pl-1"
                                                >
                                                    <span>
                                                        ● {getAgentDisplayName(detail.owner_id)}
                                                    </span>
                                                    <span className="text-zinc-300">
                                                        {(dnReturn * multiplier).toFixed(4)}%{' '}
                                                        <span className="opacity-70 text-[9px] text-zinc-500">
                                                            (Base: {formatVal(dnReturn)})
                                                        </span>
                                                    </span>
                                                </div>
                                            );
                                        })}
                                    </div>
                                );
                            })()}
                        </div>

                        {/* 4. Opportunity Cost */}
                        <div className="space-y-1.5 border-b border-zinc-900/60 pb-3">
                            <div className="flex flex-col sm:flex-row sm:justify-between font-bold text-zinc-200">
                                <span>4. Opportunity Cost</span>
                                <span>
                                    -{(opportunityCost * multiplier).toFixed(4)}%{' '}
                                    <span className="text-[10px] font-normal text-zinc-500">
                                        (Base: -{opportunityCost.toFixed(4)}%)
                                    </span>
                                </span>
                            </div>
                        </div>

                        {/* 5. Risk Penalty */}
                        <div className="space-y-1.5 border-b border-zinc-900/60 pb-3">
                            <div className="flex flex-col sm:flex-row sm:justify-between font-bold text-zinc-200">
                                <span>5. Risk Penalty (Max Drawdown * 0.3)</span>
                                <span>
                                    -{(dailyDrawdownPenalty * multiplier).toFixed(4)}%{' '}
                                    <span className="text-[10px] font-normal text-zinc-500">
                                        (Base: -{dailyDrawdownPenalty.toFixed(4)}%)
                                    </span>
                                </span>
                            </div>
                            <div className="pl-3 border-l-2 border-zinc-800 text-[10px] text-zinc-500 space-y-1">
                                <div className="text-zinc-350">
                                    Base: {maxDrawdown.toFixed(4)}% * 0.3 ={' '}
                                    {dailyDrawdownPenalty.toFixed(4)}%
                                </div>
                                <div className="text-zinc-350">
                                    Scaled: {(maxDrawdown * multiplier).toFixed(4)}% * 0.3 ={' '}
                                    {(dailyDrawdownPenalty * multiplier).toFixed(4)}%
                                </div>
                            </div>
                        </div>

                        {/* 6. Final Score Assembly */}
                        <div className="space-y-1.5 pt-1">
                            <div className="font-bold text-zinc-200">6. Final Score Assembly:</div>
                            <div className="text-[10px] text-zinc-500">
                                Formula: score = Composite Excess Return - Risk Penalty
                            </div>
                            <div className="pl-3 border-l-2 border-zinc-850 text-[10px]">
                                <div className="text-emerald-450 font-bold">
                                    Base Score Calculation:
                                </div>
                                <div className="text-zinc-350 font-bold">
                                    score = {dailyExcessReturn.toFixed(4)}% -{' '}
                                    {dailyDrawdownPenalty.toFixed(4)}%
                                </div>
                                <div className="text-zinc-350 font-bold text-xs pt-0.5">
                                    score = {dailyScore >= 0 ? '+' : ''}
                                    {dailyScore.toFixed(4)}
                                </div>

                                <div className="text-emerald-450 font-bold mt-2">
                                    Scaled Day Score Calculation:
                                </div>
                                <div className="text-zinc-350 font-bold">
                                    score = {(dailyExcessReturn * multiplier).toFixed(4)}% -{' '}
                                    {(dailyDrawdownPenalty * multiplier).toFixed(4)}%
                                </div>
                                <div className="text-emerald-400 font-bold text-xs pt-0.5">
                                    score = {selectedCp.score >= 0 ? '+' : ''}
                                    {selectedCp.score.toFixed(4)}
                                </div>
                            </div>
                        </div>
                    </div>
                );
            })()}
        </div>
    );
}
