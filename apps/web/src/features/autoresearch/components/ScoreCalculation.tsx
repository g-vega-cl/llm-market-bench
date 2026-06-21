import { Card, SectionHeading, SubHeading } from '@llm-market-bench/ui-design-system';

export function ScoreCalculation() {
    return (
        <Card className="p-8 space-y-6 bg-gradient-to-br from-white to-zinc-50 dark:from-zinc-900 dark:to-zinc-950 border-zinc-200 dark:border-zinc-800">
            <div className="space-y-2">
                <SectionHeading>Scoring Methodology</SectionHeading>
                <p className="text-zinc-600 dark:text-zinc-400 max-w-2xl">
                    Every experiment is evaluated against the market using a risk-adjusted return
                    formula. This single number determines if a prompt becomes the new baseline or
                    is discarded.
                </p>
            </div>

            <div className="py-8 px-6 bg-zinc-100/50 dark:bg-zinc-800/50 rounded-2xl border border-zinc-200 dark:border-zinc-700 flex flex-col items-center justify-center space-y-4">
                <div className="text-sm font-medium text-zinc-500 dark:text-zinc-500 uppercase tracking-wider">
                    Risk-Adjusted Score Formula
                </div>
                <div className="text-2xl md:text-3xl font-mono font-bold text-zinc-900 dark:text-zinc-100 text-center leading-relaxed">
                    (Portfolio% - SPY%) + (Portfolio% - Do-Nothing%) - Opportunity Cost% - (Max
                    Drawdown% × 0.3)
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8 pt-4">
                <div className="space-y-2">
                    <SubHeading>Excess Return</SubHeading>
                    <p className="text-sm text-zinc-600 dark:text-zinc-400">
                        The primary goal: outperform the S&P 500 benchmark and a "Do-Nothing"
                        alternative (holding inherited positions). We calculate the sum of excess
                        returns over SPY and Do-Nothing to isolate active trading value-add without
                        the drag of the previous week.
                    </p>
                </div>
                <div className="space-y-2">
                    <SubHeading>Opportunity Cost</SubHeading>
                    <p className="text-sm text-zinc-600 dark:text-zinc-400">
                        If the portfolio returns fail to clear the active Treasury Bond yield hurdle
                        compounded for the week, an asymmetric penalty is applied:{' '}
                        <span className="font-mono text-xs text-zinc-900 dark:text-zinc-100 bg-zinc-200/50 dark:bg-zinc-800 px-1 py-0.5 rounded">
                            max(0, Bond Yield% - Portfolio%)
                        </span>
                        .
                    </p>
                </div>
                <div className="space-y-2">
                    <SubHeading>Risk Penalty</SubHeading>
                    <p className="text-sm text-zinc-600 dark:text-zinc-400">
                        We multiply the maximum drawdown by 0.3. This penalizes volatility and
                        ensures the AI prioritizes capital preservation.
                    </p>
                </div>
                <div className="space-y-2">
                    <SubHeading>The "Ratchet"</SubHeading>
                    <p className="text-sm text-zinc-600 dark:text-zinc-400">
                        If the score is lower than the all-time best, the experiment is discarded
                        and we revert to the baseline prompt.
                    </p>
                </div>
            </div>
        </Card>
    );
}
