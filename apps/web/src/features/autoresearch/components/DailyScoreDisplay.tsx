import type { PromptExperiment } from '@llm-market-bench/database';
import { Card } from '@llm-market-bench/ui-design-system';
import { useState } from 'react';
import { DailyAuditLedger } from './daily-score/DailyAuditLedger';
import { DailyProgressionGrid } from './daily-score/DailyProgressionGrid';
import { DailyScoreOverview } from './daily-score/DailyScoreOverview';
import {
    calculateDailyMetrics,
    DAY_MULTIPLIERS,
    getCheckpoints,
    type PortfolioDetail,
} from './daily-score/daily-score-math';
import { useActualReturns } from './daily-score/useActualReturns';

export interface DailyScoreDisplayProps {
    experiment: PromptExperiment;
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
    const multiplier = selectedDayName ? DAY_MULTIPLIERS[selectedDayName] || 1.0 : 1.0;

    return (
        <Card className="p-8 space-y-6 bg-gradient-to-br from-zinc-900 to-black border-zinc-800 text-zinc-100 shadow-xl overflow-hidden relative">
            {/* Cyberpunk Grid Background */}
            <div className="absolute inset-0 bg-[linear-gradient(to_right,#27272a_1px,transparent_1px),linear-gradient(to_bottom,#27272a_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_70%,transparent_100%)] opacity-20 pointer-events-none" />

            <DailyScoreOverview
                isActive={isActive}
                dailyScore={dailyScore}
                dailyExcessReturn={dailyExcessReturn}
                opportunityCost={opportunityCost}
                dailyDrawdownPenalty={dailyDrawdownPenalty}
            />

            <DailyProgressionGrid
                checkpoints={checkpoints}
                isActive={isActive}
                selectedDayName={selectedDayName}
                onSelectDay={(dayName) =>
                    setSelectedDayName(selectedDayName === dayName ? null : dayName)
                }
            />

            {selectedDayName && selectedCp && (
                <DailyAuditLedger
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
