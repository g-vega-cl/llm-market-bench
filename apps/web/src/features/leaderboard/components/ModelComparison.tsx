import type { LLMLeaderboardRow } from '@llm-market-bench/database';
import { Badge, Button, Card, SectionHeading } from '@llm-market-bench/ui-design-system';
import { formatWinRate, getLeaderboardDisplayInfo } from '../lib/model-helper';

interface ModelComparisonProps {
    modelA: LLMLeaderboardRow;
    modelB: LLMLeaderboardRow;
    onClear: () => void;
}

export function ModelComparison({ modelA, modelB, onClear }: ModelComparisonProps) {
    const infoA = getLeaderboardDisplayInfo(modelA);
    const infoB = getLeaderboardDisplayInfo(modelB);

    const compareMetrics = [
        {
            label: 'Composite Score',
            valA: modelA.composite_score,
            valB: modelB.composite_score,
            formattedA: `${modelA.composite_score.toFixed(1)}%`,
            formattedB: `${modelB.composite_score.toFixed(1)}%`,
            isHigherBetter: true,
        },
        {
            label: 'Total Return',
            valA: modelA.return_pct,
            valB: modelB.return_pct,
            formattedA: `${modelA.return_pct >= 0 ? '+' : ''}${modelA.return_pct.toFixed(2)}%`,
            formattedB: `${modelB.return_pct >= 0 ? '+' : ''}${modelB.return_pct.toFixed(2)}%`,
            isHigherBetter: true,
        },
        {
            label: 'Realized P&L',
            valA: modelA.realized_pnl,
            valB: modelB.realized_pnl,
            formattedA: `$${modelA.realized_pnl.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
            formattedB: `$${modelB.realized_pnl.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
            isHigherBetter: true,
        },
        {
            label: 'Win Rate',
            valA: modelA.win_rate,
            valB: modelB.win_rate,
            formattedA: formatWinRate(modelA.win_rate),
            formattedB: formatWinRate(modelB.win_rate),
            isHigherBetter:
                modelA.win_rate !== null &&
                modelA.win_rate !== undefined &&
                modelB.win_rate !== null &&
                modelB.win_rate !== undefined
                    ? true
                    : null,
        },
        {
            label: 'Total Trades',
            valA: Number(modelA.total_trades),
            valB: Number(modelB.total_trades),
            formattedA: String(modelA.total_trades),
            formattedB: String(modelB.total_trades),
            isHigherBetter: null,
        },
        {
            label: 'Consistency',
            valA: modelA.consistency_score,
            valB: modelB.consistency_score,
            formattedA: `${modelA.consistency_score.toFixed(1)}%`,
            formattedB: `${modelB.consistency_score.toFixed(1)}%`,
            isHigherBetter: true,
        },
        {
            label: 'Conviction Score',
            valA: modelA.conviction_score,
            valB: modelB.conviction_score,
            formattedA:
                modelA.conviction_score !== null && modelA.conviction_score !== undefined
                    ? `${modelA.conviction_score.toFixed(1)}`
                    : '—',
            formattedB:
                modelB.conviction_score !== null && modelB.conviction_score !== undefined
                    ? `${modelB.conviction_score.toFixed(1)}`
                    : '—',
            isHigherBetter:
                modelA.conviction_score !== null &&
                modelA.conviction_score !== undefined &&
                modelB.conviction_score !== null &&
                modelB.conviction_score !== undefined
                    ? true
                    : null,
        },
        {
            label: 'Average Confidence',
            valA: modelA.average_confidence,
            valB: modelB.average_confidence,
            formattedA:
                modelA.average_confidence !== null && modelA.average_confidence !== undefined
                    ? `${modelA.average_confidence.toFixed(1)}%`
                    : '—',
            formattedB:
                modelB.average_confidence !== null && modelB.average_confidence !== undefined
                    ? `${modelB.average_confidence.toFixed(1)}%`
                    : '—',
            isHigherBetter: null,
        },
    ];

    return (
        <section className="flex flex-col gap-6 pt-6 border-t border-voxel-bevel-hi">
            <div className="flex flex-wrap justify-between items-center gap-4">
                <SectionHeading>Comparative Diagnostics</SectionHeading>
                <Button type="button" variant="outline" onClick={onClear}>
                    Clear Selection
                </Button>
            </div>

            <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,20rem),1fr))] gap-6 items-stretch">
                {/* Competitor A */}
                <Card
                    variant="default"
                    padding="md"
                    className="scene-scrim h-full flex flex-col justify-between gap-4 min-w-0"
                >
                    <div className="flex flex-wrap items-center gap-2 border-b border-voxel-bevel-hi pb-3 min-w-0">
                        <Badge colorScheme={infoA.badgeColor} variant="soft" size="xs">
                            {infoA.categoryLabel}
                        </Badge>
                        <h3 className="text-sm font-bold text-voxel-ink truncate">{infoA.name}</h3>
                        <Badge colorScheme="neutral" variant="soft" size="xs">
                            A
                        </Badge>
                    </div>

                    <div className="flex flex-col gap-2 mt-auto">
                        {compareMetrics.map((m) => {
                            const isWin =
                                m.isHigherBetter !== null &&
                                m.valA !== null &&
                                m.valB !== null &&
                                m.valA > m.valB;
                            const isLoss =
                                m.isHigherBetter !== null &&
                                m.valA !== null &&
                                m.valB !== null &&
                                m.valA < m.valB;

                            return (
                                <div
                                    key={m.label}
                                    className={`voxel-trough rounded-none flex justify-between items-center p-2.5 gap-2 ${isWin ? 'border-success/40' : isLoss ? 'opacity-80' : ''}`}
                                >
                                    <span className="text-xs font-normal text-voxel-muted font-mono uppercase tracking-wider">
                                        {m.label}
                                    </span>
                                    <div className="flex items-center gap-2">
                                        <span
                                            className={`font-mono tabular-nums text-sm font-bold ${isWin ? 'text-success' : isLoss ? 'text-voxel-muted' : 'text-voxel-ink'}`}
                                        >
                                            {m.formattedA}
                                        </span>
                                        {isWin ? (
                                            <Badge colorScheme="success" variant="solid" size="xs">
                                                WIN
                                            </Badge>
                                        ) : null}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </Card>

                {/* Competitor B */}
                <Card
                    variant="default"
                    padding="md"
                    className="scene-scrim h-full flex flex-col justify-between gap-4 min-w-0"
                >
                    <div className="flex flex-wrap items-center gap-2 border-b border-voxel-bevel-hi pb-3 min-w-0">
                        <Badge colorScheme={infoB.badgeColor} variant="soft" size="xs">
                            {infoB.categoryLabel}
                        </Badge>
                        <h3 className="text-sm font-bold text-voxel-ink truncate">{infoB.name}</h3>
                        <Badge colorScheme="neutral" variant="soft" size="xs">
                            B
                        </Badge>
                    </div>

                    <div className="flex flex-col gap-2 mt-auto">
                        {compareMetrics.map((m) => {
                            const isWin =
                                m.isHigherBetter !== null &&
                                m.valA !== null &&
                                m.valB !== null &&
                                m.valB > m.valA;
                            const isLoss =
                                m.isHigherBetter !== null &&
                                m.valA !== null &&
                                m.valB !== null &&
                                m.valB < m.valA;

                            return (
                                <div
                                    key={m.label}
                                    className={`voxel-trough rounded-none flex justify-between items-center p-2.5 gap-2 ${isWin ? 'border-success/40' : isLoss ? 'opacity-80' : ''}`}
                                >
                                    <span className="text-xs font-normal text-voxel-muted font-mono uppercase tracking-wider">
                                        {m.label}
                                    </span>
                                    <div className="flex items-center gap-2">
                                        <span
                                            className={`font-mono tabular-nums text-sm font-bold ${isWin ? 'text-success' : isLoss ? 'text-voxel-muted' : 'text-voxel-ink'}`}
                                        >
                                            {m.formattedB}
                                        </span>
                                        {isWin ? (
                                            <Badge colorScheme="success" variant="solid" size="xs">
                                                WIN
                                            </Badge>
                                        ) : null}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </Card>
            </div>
        </section>
    );
}
