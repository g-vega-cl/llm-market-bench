import type { PromptExperiment } from '@llm-market-bench/database';
import { Card, SectionHeading, SubHeading } from '@llm-market-bench/ui-design-system';

interface VolatilityCalculationProps {
    experiment: PromptExperiment;
}

export function VolatilityCalculation({ experiment }: VolatilityCalculationProps) {
    const metrics = experiment.metrics || {};

    if (metrics.volatility === undefined || metrics.volatility === null) {
        return (
            <Card className="p-8 space-y-4 bg-gradient-to-br from-white to-zinc-50 dark:from-zinc-900 dark:to-zinc-950 border-zinc-200 dark:border-zinc-800 animate-fade-in">
                <div className="space-y-2">
                    <SectionHeading>Volatility Methodology</SectionHeading>
                    <p className="text-zinc-500 dark:text-zinc-400 text-sm leading-relaxed">
                        This experiment variant is currently active. Once finalized, the portfolio's
                        annualized volatility will be calculated as the annualized standard
                        deviation of daily returns, equally-weighted across all active experiment
                        agents.
                    </p>
                </div>
            </Card>
        );
    }

    const volatilityPct = metrics.volatility ?? 0;
    const dailyVolatility = volatilityPct / Math.sqrt(252);

    return (
        <Card className="p-8 space-y-6 bg-gradient-to-br from-white to-zinc-50 dark:from-zinc-900 dark:to-zinc-950 border-zinc-200 dark:border-zinc-800">
            <div className="space-y-2">
                <SectionHeading>Volatility Methodology</SectionHeading>
                <p className="text-zinc-600 dark:text-zinc-400 max-w-2xl text-sm">
                    How this experiment's annualized volatility was calculated from raw daily
                    returns.
                </p>
            </div>

            <div className="py-6 px-6 bg-zinc-100/50 dark:bg-zinc-800/50 rounded-2xl border border-zinc-200 dark:border-zinc-700 flex flex-col space-y-4">
                <div className="flex flex-col space-y-3 font-mono text-sm md:text-base text-zinc-700 dark:text-zinc-300">
                    {/* Daily standard deviation row */}
                    <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-2">
                            <span>Daily Volatility (σ_daily)</span>
                        </div>
                        <span className="text-zinc-900 dark:text-zinc-100 font-bold">
                            {dailyVolatility.toFixed(4)}%
                        </span>
                    </div>

                    {/* Annualization factor row */}
                    <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-2">
                            <span>Annualization Factor</span>
                            <span className="text-xs text-zinc-400">(√252 trading days)</span>
                        </div>
                        <span className="text-zinc-900 dark:text-zinc-100 font-bold">
                            × {Math.sqrt(252).toFixed(4)}
                        </span>
                    </div>

                    <div className="h-px w-full bg-zinc-300 dark:bg-zinc-700 my-2" />

                    {/* Annualized Volatility row */}
                    <div className="flex items-center justify-between font-bold text-lg text-zinc-900 dark:text-zinc-100">
                        <span>Annualized Volatility</span>
                        <span className="text-emerald-500">{volatilityPct.toFixed(2)}%</span>
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-4">
                <div className="space-y-2">
                    <SubHeading>1. Equal-Weighted Daily Returns</SubHeading>
                    <p className="text-xs text-zinc-500 dark:text-zinc-400 leading-relaxed">
                        Percentage change of total equity is computed independently for each agent's
                        portfolio, then averaged equally across all agents per day. A $10K and a $5K
                        portfolio have equal weight, eliminating capital-scale bias.
                    </p>
                </div>
                <div className="space-y-2">
                    <SubHeading>2. Sample Standard Deviation</SubHeading>
                    <p className="text-xs text-zinc-500 dark:text-zinc-400 leading-relaxed">
                        Computes the daily standard deviation (
                        <span className="font-mono text-[10px]">σ_daily</span>) of these returns
                        relative to the mean return over the trading period, using N-1 Bessel's
                        correction for unbiased variance.
                    </p>
                </div>
                <div className="space-y-2">
                    <SubHeading>3. Annualization Step</SubHeading>
                    <p className="text-xs text-zinc-500 dark:text-zinc-400 leading-relaxed">
                        Scales the daily standard deviation to a yearly rate by multiplying it by{' '}
                        <span className="font-mono text-[10px]">√252</span> (representing 252
                        standard trading days in a calendar year).
                    </p>
                </div>
            </div>
        </Card>
    );
}
