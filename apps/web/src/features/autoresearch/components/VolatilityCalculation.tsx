import type { PromptExperiment } from '@llm-market-bench/database';
import { Card, SectionHeading, SubHeading } from '@llm-market-bench/ui-design-system';

interface VolatilityCalculationProps {
    experiment: PromptExperiment;
}

export function VolatilityCalculation({ experiment }: VolatilityCalculationProps) {
    const metrics = experiment.metrics || {};

    if (metrics.volatility === undefined || metrics.volatility === null) {
        return (
            <Card className="p-6 flex flex-col gap-4 bg-boxel-surface border-boxel-bevel-hi animate-fade-in">
                <div className="flex flex-col gap-2">
                    <SectionHeading>Volatility Methodology</SectionHeading>
                    <p className="text-boxel-muted text-xs font-normal leading-relaxed">
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
        <Card className="p-6 flex flex-col gap-6 bg-boxel-surface border-boxel-bevel-hi">
            <div className="flex flex-col gap-2">
                <SectionHeading>Volatility Methodology</SectionHeading>
                <p className="text-boxel-muted max-w-2xl text-xs font-normal leading-relaxed">
                    How this experiment's annualized volatility was calculated from raw daily
                    returns.
                </p>
            </div>

            <div className="p-6 bg-boxel-trough rounded-none border border-boxel-bevel-hi flex flex-col gap-4">
                <div className="flex flex-col gap-3 font-mono text-xs font-normal text-boxel-muted">
                    {/* Daily standard deviation row */}
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <span>Daily Volatility (σ_daily)</span>
                        </div>
                        <span className="text-boxel-ink font-bold">
                            {dailyVolatility.toFixed(4)}%
                        </span>
                    </div>

                    {/* Annualization factor row */}
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <span>Annualization Factor</span>
                            <span className="text-xs text-boxel-muted">(√252 trading days)</span>
                        </div>
                        <span className="text-boxel-ink font-bold">
                            × {Math.sqrt(252).toFixed(4)}
                        </span>
                    </div>

                    <div className="h-px w-full bg-boxel-bevel-hi my-1" />

                    {/* Annualized Volatility row */}
                    <div className="flex items-center justify-between text-lg font-bold text-boxel-ink">
                        <span>Annualized Volatility</span>
                        <span className="text-emerald-400">{volatilityPct.toFixed(2)}%</span>
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,16rem),1fr))] gap-6 items-stretch pt-2">
                <div className="flex flex-col gap-2">
                    <SubHeading>1. Equal-Weighted Daily Returns</SubHeading>
                    <p className="text-xs font-normal text-boxel-muted leading-relaxed">
                        Percentage change of total equity is computed independently for each agent's
                        portfolio, then averaged equally across all agents per day. A $10K and a $5K
                        portfolio have equal weight, eliminating capital-scale bias.
                    </p>
                </div>
                <div className="flex flex-col gap-2">
                    <SubHeading>2. Sample Standard Deviation</SubHeading>
                    <p className="text-xs font-normal text-boxel-muted leading-relaxed">
                        Computes the daily standard deviation (
                        <span className="font-mono text-xs font-normal">σ_daily</span>) of these
                        returns relative to the mean return over the trading period, using N-1
                        Bessel's correction for unbiased variance.
                    </p>
                </div>
                <div className="flex flex-col gap-2">
                    <SubHeading>3. Annualization Step</SubHeading>
                    <p className="text-xs font-normal text-boxel-muted leading-relaxed">
                        Scales the daily standard deviation to a yearly rate by multiplying it by{' '}
                        <span className="font-mono text-xs font-normal">√252</span> (representing
                        252 standard trading days in a calendar year).
                    </p>
                </div>
            </div>
        </Card>
    );
}
