import type { PromptExperiment } from '@llm-market-bench/database';
import { Card, SectionHeading } from '@llm-market-bench/ui-design-system';

interface ScoreBreakdownProps {
    experiment: PromptExperiment;
}

function ActiveExperimentPlaceholder() {
    return (
        <Card className="p-8 space-y-4 bg-gradient-to-br from-white to-zinc-50 dark:from-zinc-900 dark:to-zinc-950 border-zinc-200 dark:border-zinc-800 animate-fade-in">
            <div className="space-y-2">
                <SectionHeading>Score Breakdown</SectionHeading>
                <p className="text-zinc-500 dark:text-zinc-400 text-sm leading-relaxed">
                    This experiment variant is currently active. Performance metrics and the
                    risk-adjusted scoring breakdown will be computed automatically at the close of
                    the trading week.
                </p>
            </div>
        </Card>
    );
}

interface SignValueProps {
    value: number;
    suffix?: string;
    showSign?: boolean;
    className?: string;
}

function SignValue({ value, suffix = '', showSign = true, className = '' }: SignValueProps) {
    const isPositive = value >= 0;
    const sign = showSign && isPositive ? '+' : '';
    const colorClass = isPositive ? 'text-emerald-500' : 'text-rose-500';
    return (
        <span className={`${colorClass} ${className}`}>
            {sign}
            {value.toFixed(4)}
            {suffix}
        </span>
    );
}

interface PositionDetail {
    qty: number;
    end_price: number;
    value: number;
    start_price?: number;
    start_value?: number;
    start_date?: string;
    end_date?: string;
}

interface PortfolioDetail {
    owner_id?: string;
    initial_equity?: number;
    initial_cash?: number;
    end_equity?: number;
    do_nothing_return_pct?: number;
    positions?: Record<string, PositionDetail>;
}

export function ScoreBreakdown({ experiment }: ScoreBreakdownProps) {
    const metrics = experiment.metrics || {};

    if (metrics.score === undefined || metrics.score === null) {
        return <ActiveExperimentPlaceholder />;
    }

    const portfolioReturn = metrics.portfolio_return_pct ?? 0;
    const spyReturn = metrics.spy_return_pct ?? 0;
    const doNothingReturn = metrics.do_nothing_return_pct ?? 0;
    const excessReturn = metrics.excess_return ?? 0;

    // Hurdles and context
    const bondReturn = metrics.bond_return_pct ?? 0;
    const dollarReturn = metrics.dollar_return_pct ?? 0;
    const opportunityCost = metrics.opportunity_cost_penalty ?? 0;

    // Drawdown
    const maxDrawdown = metrics.max_drawdown ?? 0;
    const drawdownPenalty = metrics.drawdown_penalty ?? 0;

    // Final
    const score = metrics.score ?? 0;

    // Intermediate calculations
    const excessVsSpy = portfolioReturn - spyReturn;
    const excessVsDoNothing = portfolioReturn - doNothingReturn;

    // Portfolio details
    const portfolioDetails = (metrics.portfolio_details || {}) as Record<string, PortfolioDetail>;
    const hasDetails = Object.keys(portfolioDetails).length > 0;

    return (
        <Card className="p-8 space-y-8 bg-gradient-to-br from-white to-zinc-50 dark:from-zinc-900 dark:to-zinc-950 border-zinc-200 dark:border-zinc-800">
            <div className="space-y-2 border-b border-zinc-200 dark:border-zinc-800 pb-4">
                <SectionHeading>Score Audit & Step-by-Step Math</SectionHeading>
                <p className="text-zinc-600 dark:text-zinc-400 max-w-2xl text-sm">
                    Review the step-by-step arithmetic, raw inputs, and portfolio ledgers used to
                    verify the final risk-adjusted prompt score.
                </p>
            </div>

            {/* Step-by-Step Audit Flow */}
            <div className="space-y-6">
                {/* Step 1: Excess Return vs Benchmarks */}
                <div className="p-5 rounded-2xl bg-zinc-50/50 dark:bg-zinc-900/50 border border-zinc-200 dark:border-zinc-800 space-y-4 hover:border-zinc-300 dark:hover:border-zinc-700 transition-all">
                    <div className="flex items-center justify-between border-b border-zinc-200 dark:border-zinc-805 pb-2">
                        <h4 className="text-sm font-bold text-zinc-900 dark:text-zinc-100 flex items-center space-x-2">
                            <span className="flex items-center justify-center h-5 w-5 rounded-full bg-emerald-500/10 text-emerald-500 text-xs font-black">
                                1
                            </span>
                            <span>Excess Return vs Benchmarks</span>
                        </h4>
                        <SignValue value={excessReturn} suffix="%" showSign={true} />
                    </div>

                    <div className="space-y-3 font-mono text-xs text-zinc-650 dark:text-zinc-400">
                        {/* Excess vs SPY */}
                        <div className="flex items-center justify-between">
                            <span className="flex flex-col">
                                <span className="font-sans font-medium text-zinc-800 dark:text-zinc-200">
                                    Excess vs S&P 500 (SPY)
                                </span>
                                <span>Formula: Portfolio - SPY</span>
                            </span>
                            <span className="flex flex-col items-end">
                                <span className="font-bold text-zinc-850 dark:text-zinc-200">
                                    {portfolioReturn.toFixed(4)}% - {spyReturn.toFixed(4)}%
                                </span>
                                <SignValue value={excessVsSpy} suffix="%" showSign={true} />
                            </span>
                        </div>

                        {/* Excess vs Do-Nothing */}
                        <div className="flex items-center justify-between pt-2 border-t border-dashed border-zinc-200 dark:border-zinc-800">
                            <span className="flex flex-col">
                                <span className="font-sans font-medium text-zinc-800 dark:text-zinc-200">
                                    Excess vs Do-Nothing Portfolio
                                </span>
                                <span>Formula: Portfolio - Do-Nothing</span>
                            </span>
                            <span className="flex flex-col items-end">
                                <span className="font-bold text-zinc-850 dark:text-zinc-200">
                                    {portfolioReturn.toFixed(4)}% - {doNothingReturn.toFixed(4)}%
                                </span>
                                <SignValue value={excessVsDoNothing} suffix="%" showSign={true} />
                            </span>
                        </div>

                        {/* Combined Excess */}
                        <div className="flex items-center justify-between pt-2 border-t border-zinc-200 dark:border-zinc-800">
                            <span className="font-sans font-bold text-zinc-800 dark:text-zinc-200">
                                Total Benchmark Excess Return
                            </span>
                            <span className="font-bold text-zinc-850 dark:text-zinc-200">
                                {excessVsSpy.toFixed(4)}% + {excessVsDoNothing.toFixed(4)}% ={' '}
                                {excessReturn.toFixed(4)}%
                            </span>
                        </div>
                    </div>
                </div>

                {/* Step 2: Opportunity Cost Hurdle */}
                <div className="p-5 rounded-2xl bg-zinc-50/50 dark:bg-zinc-900/50 border border-zinc-200 dark:border-zinc-800 space-y-4 hover:border-zinc-300 dark:hover:border-zinc-700 transition-all">
                    <div className="flex items-center justify-between border-b border-zinc-200 dark:border-zinc-805 pb-2">
                        <h4 className="text-sm font-bold text-zinc-900 dark:text-zinc-100 flex items-center space-x-2">
                            <span className="flex items-center justify-center h-5 w-5 rounded-full bg-rose-500/10 text-rose-500 text-xs font-black">
                                2
                            </span>
                            <span>Opportunity Cost Penalty</span>
                        </h4>
                        <span className="text-sm font-mono font-bold text-rose-500">
                            -{opportunityCost.toFixed(4)}%
                        </span>
                    </div>

                    <div className="space-y-3 font-mono text-xs text-zinc-650 dark:text-zinc-400">
                        {/* Compounded Bond Yield */}
                        <div className="flex items-center justify-between">
                            <span className="flex flex-col">
                                <span className="font-sans font-medium text-zinc-800 dark:text-zinc-200">
                                    10-Year Treasury Bond Yield
                                </span>
                                <span>Compounded Weekly (Active Hurdle)</span>
                            </span>
                            <span className="font-bold text-zinc-850 dark:text-zinc-200">
                                {bondReturn.toFixed(4)}%
                            </span>
                        </div>

                        {/* US Dollar Index */}
                        <div className="flex items-center justify-between pt-2 border-t border-dashed border-zinc-200 dark:border-zinc-800">
                            <span className="flex flex-col">
                                <span className="font-sans font-medium text-zinc-800 dark:text-zinc-200">
                                    US Dollar Index (DXY/UUP) Return
                                </span>
                                <span className="text-[10px] text-zinc-400 font-sans font-normal uppercase tracking-wider">
                                    Context Only (No Penalty)
                                </span>
                            </span>
                            <SignValue value={dollarReturn} suffix="%" showSign={true} />
                        </div>

                        {/* Asymmetric Penalty Formula */}
                        <div className="flex items-center justify-between pt-2 border-t border-zinc-200 dark:border-zinc-800">
                            <span className="flex flex-col font-sans text-zinc-800 dark:text-zinc-200">
                                <span className="font-bold">Hurdle Penalty Calculation</span>
                                <span className="font-mono text-[10px] text-zinc-500 lowercase">
                                    max(0.0, bond_hurdle - portfolio_return)
                                </span>
                            </span>
                            <span className="font-bold text-zinc-850 dark:text-zinc-200">
                                max(0.0, {bondReturn.toFixed(4)}% - {portfolioReturn.toFixed(4)}%) ={' '}
                                {opportunityCost.toFixed(4)}%
                            </span>
                        </div>
                    </div>
                </div>

                {/* Step 3: Drawdown Penalty */}
                <div className="p-5 rounded-2xl bg-zinc-50/50 dark:bg-zinc-900/50 border border-zinc-200 dark:border-zinc-800 space-y-4 hover:border-zinc-300 dark:hover:border-zinc-700 transition-all">
                    <div className="flex items-center justify-between border-b border-zinc-200 dark:border-zinc-805 pb-2">
                        <h4 className="text-sm font-bold text-zinc-900 dark:text-zinc-100 flex items-center space-x-2">
                            <span className="flex items-center justify-center h-5 w-5 rounded-full bg-rose-500/10 text-rose-500 text-xs font-black">
                                3
                            </span>
                            <span>Drawdown Risk Penalty</span>
                        </h4>
                        <span className="text-sm font-mono font-bold text-rose-500">
                            -{drawdownPenalty.toFixed(4)}%
                        </span>
                    </div>

                    <div className="space-y-3 font-mono text-xs text-zinc-650 dark:text-zinc-400">
                        {/* Max Drawdown */}
                        <div className="flex items-center justify-between">
                            <span className="flex flex-col font-sans text-zinc-800 dark:text-zinc-200">
                                <span className="font-medium">Maximum Drawdown</span>
                                <span className="text-zinc-500 text-[10px] font-sans">
                                    Largest peak-to-trough drop
                                </span>
                            </span>
                            <span className="font-bold text-zinc-850 dark:text-zinc-200">
                                {maxDrawdown.toFixed(4)}%
                            </span>
                        </div>

                        {/* Weighting penalty */}
                        <div className="flex items-center justify-between pt-2 border-t border-zinc-200 dark:border-zinc-800">
                            <span className="flex flex-col font-sans text-zinc-800 dark:text-zinc-200">
                                <span className="font-bold">Risk-Adjusted Penalty Formula</span>
                                <span className="font-mono text-[10px] text-zinc-500 lowercase">
                                    max_drawdown × 0.3
                                </span>
                            </span>
                            <span className="font-bold text-zinc-850 dark:text-zinc-200">
                                {maxDrawdown.toFixed(4)}% × 0.3 = {drawdownPenalty.toFixed(4)}%
                            </span>
                        </div>
                    </div>
                </div>

                {/* Step 4: Granular Portfolio & Asset Auditor (Fact Check Ledger) */}
                {hasDetails && (
                    <div className="p-5 rounded-2xl bg-zinc-50/50 dark:bg-zinc-900/50 border border-zinc-200 dark:border-zinc-800 space-y-4 hover:border-zinc-300 dark:hover:border-zinc-700 transition-all animate-fade-in">
                        <div className="flex items-center justify-between border-b border-zinc-200 dark:border-zinc-800 pb-2">
                            <h4 className="text-sm font-bold text-zinc-900 dark:text-zinc-100 flex items-center space-x-2">
                                <span className="flex items-center justify-center h-5 w-5 rounded-full bg-indigo-500/10 text-indigo-500 text-xs font-black">
                                    4
                                </span>
                                <span>Granular Portfolio & Asset Auditor</span>
                            </h4>
                            <span className="text-[10px] text-zinc-400 font-mono font-medium uppercase tracking-wider">
                                Fact-Check Ledger
                            </span>
                        </div>

                        <div className="space-y-6">
                            {Object.entries(portfolioDetails).map(
                                ([pid, detail]: [string, PortfolioDetail]) => {
                                    const initialEquity = detail.initial_equity ?? 0;
                                    const initialCash = detail.initial_cash ?? 0;
                                    const endEquity = detail.end_equity ?? 0;
                                    const dnReturn = detail.do_nothing_return_pct ?? 0;
                                    const positionsList = Object.entries(detail.positions || {});

                                    return (
                                        <div
                                            key={pid}
                                            className="space-y-3 bg-white dark:bg-zinc-950 p-4 rounded-xl border border-zinc-200 dark:border-zinc-850"
                                        >
                                            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1.5 border-b border-zinc-100 dark:border-zinc-900 pb-2">
                                                <div className="flex items-center space-x-2">
                                                    <span className="h-2 w-2 rounded-full bg-indigo-500" />
                                                    <span className="text-xs font-bold text-zinc-900 dark:text-zinc-100">
                                                        Agent: {detail.owner_id || 'Unknown'}
                                                    </span>
                                                </div>
                                                <span className="text-[10px] text-zinc-400 font-mono">
                                                    ID: {pid}
                                                </span>
                                            </div>

                                            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs font-mono">
                                                <div className="flex flex-col bg-zinc-50 dark:bg-zinc-900/40 p-2.5 rounded-lg">
                                                    <span className="text-[10px] text-zinc-400 font-sans">
                                                        Initial Equity
                                                    </span>
                                                    <span className="font-bold text-zinc-800 dark:text-zinc-200">
                                                        $
                                                        {initialEquity.toLocaleString(undefined, {
                                                            minimumFractionDigits: 2,
                                                            maximumFractionDigits: 2,
                                                        })}
                                                    </span>
                                                </div>
                                                <div className="flex flex-col bg-zinc-50 dark:bg-zinc-900/40 p-2.5 rounded-lg">
                                                    <span className="text-[10px] text-zinc-400 font-sans">
                                                        Initial Cash
                                                    </span>
                                                    <span className="font-bold text-zinc-800 dark:text-zinc-200">
                                                        $
                                                        {initialCash.toLocaleString(undefined, {
                                                            minimumFractionDigits: 2,
                                                            maximumFractionDigits: 2,
                                                        })}
                                                    </span>
                                                </div>
                                                <div className="flex flex-col bg-zinc-50 dark:bg-zinc-900/40 p-2.5 rounded-lg">
                                                    <span className="text-[10px] text-zinc-400 font-sans">
                                                        Do-Nothing End Equity
                                                    </span>
                                                    <span className="font-bold text-zinc-800 dark:text-zinc-200">
                                                        $
                                                        {endEquity.toLocaleString(undefined, {
                                                            minimumFractionDigits: 2,
                                                            maximumFractionDigits: 2,
                                                        })}
                                                    </span>
                                                </div>
                                                <div className="flex flex-col bg-zinc-50 dark:bg-zinc-900/40 p-2.5 rounded-lg">
                                                    <span className="text-[10px] text-zinc-400 font-sans">
                                                        Do-Nothing Return
                                                    </span>
                                                    <SignValue
                                                        value={dnReturn}
                                                        suffix="%"
                                                        showSign={true}
                                                        className="font-bold text-xs"
                                                    />
                                                </div>
                                            </div>

                                            {positionsList.length > 0 && (
                                                <div className="pt-2">
                                                    <div className="text-[9px] font-black text-zinc-400 dark:text-zinc-500 uppercase tracking-widest mb-1.5 font-sans">
                                                        Starting Assets & Weekly Valuation
                                                        Comparison
                                                    </div>
                                                    <div className="overflow-x-auto">
                                                        <table className="w-full text-[10px] font-mono text-zinc-650 dark:text-zinc-400">
                                                            <thead>
                                                                <tr className="border-b border-zinc-100 dark:border-zinc-900 text-left text-zinc-400 font-medium">
                                                                    <th className="pb-1 text-left">
                                                                        Asset
                                                                    </th>
                                                                    <th className="pb-1 text-right">
                                                                        Qty
                                                                    </th>
                                                                    <th className="pb-1 text-right">
                                                                        Start Price
                                                                    </th>
                                                                    <th className="pb-1 text-right">
                                                                        Start Value
                                                                    </th>
                                                                    <th className="pb-1 text-right">
                                                                        End Price
                                                                    </th>
                                                                    <th className="pb-1 text-right">
                                                                        End Value
                                                                    </th>
                                                                </tr>
                                                            </thead>
                                                            <tbody className="divide-y divide-zinc-100 dark:divide-zinc-900/50">
                                                                {positionsList.map(
                                                                    ([ticker, pos]: [
                                                                        string,
                                                                        PositionDetail,
                                                                    ]) => (
                                                                        <tr
                                                                            key={ticker}
                                                                            className="hover:bg-zinc-50/50 dark:hover:bg-zinc-900/20"
                                                                        >
                                                                            <td className="py-1.5 font-bold text-zinc-800 dark:text-zinc-200 text-left">
                                                                                {ticker}
                                                                            </td>
                                                                            <td className="py-1.5 text-right">
                                                                                {pos.qty}
                                                                            </td>
                                                                            <td className="py-1.5 text-right">
                                                                                {pos.start_price !==
                                                                                undefined ? (
                                                                                    <div className="flex flex-col items-end">
                                                                                        <span>
                                                                                            $
                                                                                            {pos.start_price.toFixed(
                                                                                                2,
                                                                                            )}
                                                                                        </span>
                                                                                        {pos.start_date && (
                                                                                            <span className="text-[8px] text-zinc-400 font-sans tracking-tight leading-none mt-0.5">
                                                                                                {
                                                                                                    pos.start_date
                                                                                                }
                                                                                            </span>
                                                                                        )}
                                                                                    </div>
                                                                                ) : (
                                                                                    <span className="text-zinc-400">
                                                                                        —
                                                                                    </span>
                                                                                )}
                                                                            </td>
                                                                            <td className="py-1.5 text-right font-medium">
                                                                                {pos.start_value !==
                                                                                undefined ? (
                                                                                    `$${pos.start_value.toLocaleString(
                                                                                        undefined,
                                                                                        {
                                                                                            minimumFractionDigits: 2,
                                                                                            maximumFractionDigits: 2,
                                                                                        },
                                                                                    )}`
                                                                                ) : (
                                                                                    <span className="text-zinc-400">
                                                                                        —
                                                                                    </span>
                                                                                )}
                                                                            </td>
                                                                            <td className="py-1.5 text-right">
                                                                                <div className="flex flex-col items-end">
                                                                                    <span>
                                                                                        $
                                                                                        {(
                                                                                            pos.end_price ??
                                                                                            0
                                                                                        ).toFixed(
                                                                                            2,
                                                                                        )}
                                                                                    </span>
                                                                                    {pos.end_date && (
                                                                                        <span className="text-[8px] text-zinc-400 font-sans tracking-tight leading-none mt-0.5">
                                                                                            {
                                                                                                pos.end_date
                                                                                            }
                                                                                        </span>
                                                                                    )}
                                                                                </div>
                                                                            </td>
                                                                            <td className="py-1.5 text-right font-bold text-zinc-800 dark:text-zinc-200">
                                                                                $
                                                                                {(
                                                                                    pos.value ?? 0
                                                                                ).toLocaleString(
                                                                                    undefined,
                                                                                    {
                                                                                        minimumFractionDigits: 2,
                                                                                        maximumFractionDigits: 2,
                                                                                    },
                                                                                )}
                                                                            </td>
                                                                        </tr>
                                                                    ),
                                                                )}
                                                            </tbody>
                                                        </table>
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                    );
                                },
                            )}
                        </div>
                    </div>
                )}

                {/* Step 5: Complete Arithmetic */}
                <div className="p-6 rounded-2xl bg-gradient-to-br from-zinc-50 to-zinc-100/50 dark:from-zinc-950 dark:to-zinc-900 border border-zinc-300 dark:border-zinc-800 space-y-4 shadow-inner">
                    <h4 className="text-sm font-bold text-zinc-900 dark:text-zinc-100 flex items-center space-x-2">
                        <span className="flex items-center justify-center h-5 w-5 rounded-full bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 text-xs font-black">
                            Σ
                        </span>
                        <span>Complete Score Arithmetic</span>
                    </h4>

                    <div className="bg-zinc-950 text-zinc-300 rounded-xl p-4 font-mono text-xs overflow-x-auto space-y-2 border border-zinc-800 leading-relaxed">
                        <div className="text-zinc-500 text-[10px] uppercase font-bold tracking-wider border-b border-zinc-800 pb-1.5 mb-2">
                            Math Equation Breakdown
                        </div>
                        <div>
                            score = (Excess vs SPY + Excess vs Do-Nothing) - Opportunity Cost -
                            Drawdown Penalty
                        </div>
                        <div className="text-emerald-400 pt-1 font-bold">
                            score = ({excessVsSpy.toFixed(4)}% + {excessVsDoNothing.toFixed(4)}%) -{' '}
                            {opportunityCost.toFixed(4)}% - {drawdownPenalty.toFixed(4)}%
                        </div>
                        <div className="text-emerald-400 font-bold">
                            score = {excessReturn.toFixed(4)}% - {opportunityCost.toFixed(4)}% -{' '}
                            {drawdownPenalty.toFixed(4)}%
                        </div>
                        <div className="text-emerald-450 font-bold text-sm pt-1.5 border-t border-zinc-800">
                            score = <SignValue value={score} showSign={false} />
                        </div>
                    </div>
                </div>
            </div>
        </Card>
    );
}
