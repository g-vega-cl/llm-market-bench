import { Card, SectionHeading, SubHeading } from '@llm-market-bench/ui-design-system';

export function ScoreCalculation() {
    return (
        <Card className="p-6 flex flex-col gap-6 bg-boxel-surface border-boxel-bevel-hi">
            <div className="flex flex-col gap-2">
                <SectionHeading>Scoring Methodology</SectionHeading>
                <p className="text-boxel-muted max-w-2xl text-xs font-normal leading-relaxed">
                    Every experiment is evaluated against the market using a risk-adjusted return
                    formula. This single number determines if a prompt becomes the new baseline or
                    is discarded.
                </p>
            </div>

            <div className="py-6 px-6 bg-boxel-trough rounded-none border border-boxel-bevel-hi flex flex-col items-center justify-center gap-4">
                <div className="text-sm font-bold text-boxel-muted uppercase tracking-wider">
                    Unified Risk-Adjusted Z-Score Formula
                </div>
                <div className="text-lg font-mono font-bold text-boxel-ink text-center leading-relaxed">
                    [0.4 × (Portfolio% - SPY%) + 0.4 × (Portfolio% - Do-Nothing%) + 0.2 ×
                    (Portfolio% - 10Y Bond%) - (Max Drawdown% × 0.3)] / Weekly Effective Volatility%
                </div>
            </div>

            <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,14rem),1fr))] gap-6 items-stretch pt-2">
                <div className="flex flex-col gap-2">
                    <SubHeading>Excess Return</SubHeading>
                    <p className="text-xs font-normal text-boxel-muted leading-relaxed">
                        The primary goal: outperform the S&P 500 benchmark (40% weight) and a
                        &quot;Do-Nothing&quot; alternative (40% weight) holding inherited positions.
                        Isolates active trading value-add without previous week drag.
                    </p>
                </div>
                <div className="flex flex-col gap-2">
                    <SubHeading>Risk-Free Excess</SubHeading>
                    <p className="text-xs font-normal text-boxel-muted leading-relaxed">
                        The 10-Year Treasury Bond yield forms the 20% risk-free component of the
                        triad composite benchmark. Provides a clean 1:1 excess return signal{' '}
                        <span className="font-mono text-xs font-normal text-boxel-ink bg-boxel-trough px-1 py-0.5 rounded-none border border-boxel-bevel-hi">
                            Portfolio% - 10Y Bond%
                        </span>{' '}
                        without asymmetric double penalties.
                    </p>
                </div>
                <div className="flex flex-col gap-2">
                    <SubHeading>Risk Penalty</SubHeading>
                    <p className="text-xs font-normal text-boxel-muted leading-relaxed">
                        We multiply the maximum drawdown by 0.3. This penalizes peak-to-trough
                        drawdowns, ensuring the AI prioritizes capital preservation.
                    </p>
                </div>
                <div className="flex flex-col gap-2">
                    <SubHeading>Volatility Normalizer</SubHeading>
                    <p className="text-xs font-normal text-boxel-muted leading-relaxed">
                        Divides net excess return by weekly effective volatility{' '}
                        <span className="font-mono text-xs font-normal text-boxel-ink bg-boxel-trough px-1 py-0.5 rounded-none border border-boxel-bevel-hi">
                            max(SPY Vol, Port Vol, 10%) / √52
                        </span>
                        . Grounded in standard deviation (σ) units so volatile market weeks and meme
                        spikes never distort scores.
                    </p>
                </div>
                <div className="flex flex-col gap-2">
                    <SubHeading>The &quot;Ratchet&quot;</SubHeading>
                    <p className="text-xs font-normal text-boxel-muted leading-relaxed">
                        If the Z-score is lower than the all-time best baseline for this model
                        track, the experiment is discarded and we revert to the baseline prompt.
                    </p>
                </div>
            </div>
        </Card>
    );
}
