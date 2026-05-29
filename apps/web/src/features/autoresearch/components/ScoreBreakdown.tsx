import type { PromptExperiment } from '@llm-market-bench/database';
import { Card, SectionHeading } from '@llm-market-bench/ui-design-system';

interface ScoreBreakdownProps {
    experiment: PromptExperiment;
}

export function ScoreBreakdown({ experiment }: ScoreBreakdownProps) {
    const metrics = experiment.metrics || {};

    if (metrics.score === undefined || metrics.score === null) {
        return (
            <Card className="p-8 space-y-4 bg-gradient-to-br from-white to-zinc-50 dark:from-zinc-900 dark:to-zinc-950 border-zinc-200 dark:border-zinc-800 animate-fade-in">
                <div className="space-y-2">
                    <SectionHeading>Score Breakdown</SectionHeading>
                    <p className="text-zinc-500 dark:text-zinc-400 text-sm leading-relaxed">
                        This experiment variant is currently active. Performance metrics and the
                        risk-adjusted scoring breakdown will be computed automatically at the close
                        of the trading week.
                    </p>
                </div>
            </Card>
        );
    }

    const portfolioReturn = metrics.portfolio_return_pct ?? 0;
    const spyReturn = metrics.spy_return_pct ?? 0;
    const doNothingReturn = metrics.do_nothing_return_pct ?? 0;
    const excessReturn = metrics.excess_return ?? 0;
    const opportunityCost = metrics.opportunity_cost_penalty ?? 0;
    const maxDrawdown = metrics.max_drawdown ?? 0;
    const drawdownPenalty = metrics.drawdown_penalty ?? 0;
    const score = metrics.score ?? 0;

    return (
        <Card className="p-8 space-y-6 bg-gradient-to-br from-white to-zinc-50 dark:from-zinc-900 dark:to-zinc-950 border-zinc-200 dark:border-zinc-800">
            <div className="space-y-2">
                <SectionHeading>Score Breakdown</SectionHeading>
                <p className="text-zinc-600 dark:text-zinc-400 max-w-2xl text-sm">
                    How this experiment's risk-adjusted score was calculated.
                </p>
            </div>

            <div className="py-6 px-6 bg-zinc-100/50 dark:bg-zinc-800/50 rounded-2xl border border-zinc-200 dark:border-zinc-700 flex flex-col space-y-4">
                <div className="flex flex-col space-y-3 font-mono text-sm md:text-base text-zinc-700 dark:text-zinc-300">
                    {/* Excess Return row */}
                    <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-2">
                            <span>Excess Return</span>
                            <span className="text-xs text-zinc-400">
                                (({portfolioReturn.toFixed(2)}% - {spyReturn.toFixed(2)}%) + (
                                {portfolioReturn.toFixed(2)}% - {doNothingReturn.toFixed(2)}%))
                            </span>
                        </div>
                        <span className={excessReturn >= 0 ? 'text-emerald-500' : 'text-rose-500'}>
                            {excessReturn >= 0 ? '+' : ''}
                            {excessReturn.toFixed(4)}
                        </span>
                    </div>

                    {/* Opportunity Cost Penalty row */}
                    <div className="flex items-center justify-between">
                        <span>Opportunity Cost Penalty</span>
                        <span className="text-rose-500">- {opportunityCost.toFixed(4)}</span>
                    </div>

                    {/* Drawdown Penalty row */}
                    <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-2">
                            <span>Drawdown Penalty</span>
                            <span className="text-xs text-zinc-400">
                                ({maxDrawdown.toFixed(2)}% × 0.3)
                            </span>
                        </div>
                        <span className="text-rose-500">- {drawdownPenalty.toFixed(4)}</span>
                    </div>

                    <div className="h-px w-full bg-zinc-300 dark:bg-zinc-700 my-2" />

                    {/* Final Score row */}
                    <div className="flex items-center justify-between font-bold text-lg text-zinc-900 dark:text-zinc-100">
                        <span>Final Score</span>
                        <span className={score >= 0 ? 'text-emerald-500' : 'text-rose-500'}>
                            {score.toFixed(4)}
                        </span>
                    </div>
                </div>
            </div>
        </Card>
    );
}
