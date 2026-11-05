import type { LLMLeaderboardRow } from '@llm-market-bench/database';
import { Badge, Button, Card, SectionHeading } from '@llm-market-bench/ui-design-system';
import { getModelDisplayInfo } from '../lib/model-helper';

interface ModelComparisonProps {
    modelA: LLMLeaderboardRow;
    modelB: LLMLeaderboardRow;
    onClear: () => void;
}

export function ModelComparison({ modelA, modelB, onClear }: ModelComparisonProps) {
    const infoA = getModelDisplayInfo(modelA.model_name);
    const infoB = getModelDisplayInfo(modelB.model_name);

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
            formattedA: `${modelA.win_rate.toFixed(1)}%`,
            formattedB: `${modelB.win_rate.toFixed(1)}%`,
            isHigherBetter: true,
        },
        {
            label: 'Total Trades',
            valA: Number(modelA.total_trades),
            valB: Number(modelB.total_trades),
            formattedA: String(modelA.total_trades),
            formattedB: String(modelB.total_trades),
            isHigherBetter: null, // neutral
        },
        {
            label: 'Verifier Approval',
            valA: modelA.verifier_approval_rate,
            valB: modelB.verifier_approval_rate,
            formattedA:
                modelA.verifier_approval_rate !== null &&
                modelA.verifier_approval_rate !== undefined
                    ? `${modelA.verifier_approval_rate.toFixed(1)}%`
                    : '—',
            formattedB:
                modelB.verifier_approval_rate !== null &&
                modelB.verifier_approval_rate !== undefined
                    ? `${modelB.verifier_approval_rate.toFixed(1)}%`
                    : '—',
            isHigherBetter:
                modelA.verifier_approval_rate !== null &&
                modelA.verifier_approval_rate !== undefined &&
                modelB.verifier_approval_rate !== null &&
                modelB.verifier_approval_rate !== undefined
                    ? true
                    : null,
        },
        {
            label: 'Conviction Score',
            valA: modelA.conviction_score,
            valB: modelB.conviction_score,
            formattedA: `${modelA.conviction_score.toFixed(1)}`,
            formattedB: `${modelB.conviction_score.toFixed(1)}`,
            isHigherBetter: true,
        },
        {
            label: 'Average Confidence',
            valA: modelA.average_confidence,
            valB: modelB.average_confidence,
            formattedA: `${modelA.average_confidence.toFixed(1)}%`,
            formattedB: `${modelB.average_confidence.toFixed(1)}%`,
            isHigherBetter: null, // stated confidence is informational, not a rank signal
        },
        {
            label: 'API Success Rate',
            valA: modelA.api_success_rate,
            valB: modelB.api_success_rate,
            formattedA: `${modelA.api_success_rate.toFixed(1)}%`,
            formattedB: `${modelB.api_success_rate.toFixed(1)}%`,
            isHigherBetter: true,
        },
        {
            label: 'Trading Activity',
            valA: modelA.trading_activity_rate,
            valB: modelB.trading_activity_rate,
            formattedA: `${modelA.trading_activity_rate.toFixed(1)}%`,
            formattedB: `${modelB.trading_activity_rate.toFixed(1)}%`,
            isHigherBetter: true,
        },
    ];

    return (
        <section className="space-y-6 animate-scale-in">
            <div className="flex justify-between items-center">
                <SectionHeading gradient="electric">Comparative Diagnostics</SectionHeading>
                <Button variant="glass" onClick={onClear} className="text-xs">
                    Clear Selection
                </Button>
            </div>

            <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,20rem),1fr))] gap-6 items-stretch">
                {/* Model A Card */}
                <Card
                    variant="default"
                    radius="none"
                    padding="md"
                    className="h-full flex flex-col justify-between gap-4"
                >
                    <div className="flex items-center gap-3 border-b border-boxel-bevel-hi pb-3">
                        <span className="text-lg font-bold">{infoA.emoji}</span>
                        <div>
                            <div className="flex items-center gap-2">
                                <h3 className="text-sm font-bold text-boxel-ink">{infoA.name}</h3>
                                <Badge colorScheme="neutral" variant="soft" size="xs" radius="none">
                                    Model A
                                </Badge>
                            </div>
                            <span className="text-xs font-normal text-boxel-muted font-mono tracking-wider">
                                {modelA.model_name}
                            </span>
                        </div>
                    </div>

                    <div className="space-y-2 mt-auto">
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
                                    className={`voxel-trough rounded-none flex justify-between items-center p-2.5 transition-all ${isWin ? 'border-success/40' : isLoss ? 'opacity-80' : ''}`}
                                >
                                    <span className="text-xs font-normal text-boxel-muted font-mono uppercase tracking-wider">
                                        {m.label}
                                    </span>
                                    <div className="flex items-center gap-2">
                                        <span
                                            className={`font-mono text-sm font-bold ${isWin ? 'text-success' : isLoss ? 'text-boxel-muted' : 'text-boxel-ink'}`}
                                        >
                                            {m.formattedA}
                                        </span>
                                        {isWin && (
                                            <Badge colorScheme="success" variant="solid" size="xs">
                                                WIN
                                            </Badge>
                                        )}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </Card>

                {/* Model B Card */}
                <Card
                    variant="default"
                    radius="none"
                    padding="md"
                    className="h-full flex flex-col justify-between gap-4"
                >
                    <div className="flex items-center gap-3 border-b border-boxel-bevel-hi pb-3">
                        <span className="text-lg font-bold">{infoB.emoji}</span>
                        <div>
                            <div className="flex items-center gap-2">
                                <h3 className="text-sm font-bold text-boxel-ink">{infoB.name}</h3>
                                <Badge colorScheme="neutral" variant="soft" size="xs" radius="none">
                                    Model B
                                </Badge>
                            </div>
                            <span className="text-xs font-normal text-boxel-muted font-mono tracking-wider">
                                {modelB.model_name}
                            </span>
                        </div>
                    </div>

                    <div className="space-y-2 mt-auto">
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
                                    className={`voxel-trough rounded-none flex justify-between items-center p-2.5 transition-all ${isWin ? 'border-success/40' : isLoss ? 'opacity-80' : ''}`}
                                >
                                    <span className="text-xs font-normal text-boxel-muted font-mono uppercase tracking-wider">
                                        {m.label}
                                    </span>
                                    <div className="flex items-center gap-2">
                                        <span
                                            className={`font-mono text-sm font-bold ${isWin ? 'text-success' : isLoss ? 'text-boxel-muted' : 'text-boxel-ink'}`}
                                        >
                                            {m.formattedB}
                                        </span>
                                        {isWin && (
                                            <Badge colorScheme="success" variant="solid" size="xs">
                                                WIN
                                            </Badge>
                                        )}
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
