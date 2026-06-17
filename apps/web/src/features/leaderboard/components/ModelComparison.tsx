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
            formattedA: `$${modelA.realized_pnl.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
            formattedB: `$${modelB.realized_pnl.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
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
            formattedA: `${modelA.verifier_approval_rate.toFixed(1)}%`,
            formattedB: `${modelB.verifier_approval_rate.toFixed(1)}%`,
            isHigherBetter: true,
        },
        {
            label: 'Average Confidence',
            valA: modelA.average_confidence,
            valB: modelB.average_confidence,
            formattedA: `${modelA.average_confidence.toFixed(1)}%`,
            formattedB: `${modelB.average_confidence.toFixed(1)}%`,
            isHigherBetter: true,
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

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Model A Card */}
                <Card variant="glass" radius="3xl" className="border-white/10 p-8 space-y-6">
                    <div className="flex items-center gap-4 border-b border-white/5 pb-4">
                        <span className="text-4xl">{infoA.emoji}</span>
                        <div>
                            <div className="flex items-center gap-2">
                                <h3 className="font-heading text-xl font-bold text-zinc-100">
                                    {infoA.name}
                                </h3>
                                <Badge colorScheme="neutral" variant="soft" size="xs">
                                    Model A
                                </Badge>
                            </div>
                            <span className="text-xs text-zinc-500 font-mono tracking-wider">
                                {modelA.model_name}
                            </span>
                        </div>
                    </div>

                    <div className="space-y-4">
                        {compareMetrics.map((m) => {
                            const isWin = m.isHigherBetter !== null && m.valA > m.valB;
                            const isLoss = m.isHigherBetter !== null && m.valA < m.valB;

                            return (
                                <div
                                    key={m.label}
                                    className={`flex justify-between items-center p-3 rounded-2xl border transition-all ${isWin ? 'bg-emerald-500/5 border-emerald-500/30' : isLoss ? 'bg-red-500/5 border-red-500/10' : 'bg-white/5 border-white/5'}`}
                                >
                                    <span className="text-xs text-zinc-400 font-mono uppercase tracking-wider">
                                        {m.label}
                                    </span>
                                    <div className="flex items-center gap-2">
                                        <span
                                            className={`font-mono text-sm font-bold ${isWin ? 'text-success' : isLoss ? 'text-zinc-500' : 'text-zinc-200'}`}
                                        >
                                            {m.formattedA}
                                        </span>
                                        {isWin && (
                                            <Badge
                                                colorScheme="success"
                                                variant="solid"
                                                size="xs"
                                                className="scale-90"
                                            >
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
                <Card variant="glass" radius="3xl" className="border-white/10 p-8 space-y-6">
                    <div className="flex items-center gap-4 border-b border-white/5 pb-4">
                        <span className="text-4xl">{infoB.emoji}</span>
                        <div>
                            <div className="flex items-center gap-2">
                                <h3 className="font-heading text-xl font-bold text-zinc-100">
                                    {infoB.name}
                                </h3>
                                <Badge colorScheme="neutral" variant="soft" size="xs">
                                    Model B
                                </Badge>
                            </div>
                            <span className="text-xs text-zinc-500 font-mono tracking-wider">
                                {modelB.model_name}
                            </span>
                        </div>
                    </div>

                    <div className="space-y-4">
                        {compareMetrics.map((m) => {
                            const isWin = m.isHigherBetter !== null && m.valB > m.valA;
                            const isLoss = m.isHigherBetter !== null && m.valB < m.valA;

                            return (
                                <div
                                    key={m.label}
                                    className={`flex justify-between items-center p-3 rounded-2xl border transition-all ${isWin ? 'bg-emerald-500/5 border-emerald-500/30' : isLoss ? 'bg-red-500/5 border-red-500/10' : 'bg-white/5 border-white/5'}`}
                                >
                                    <span className="text-xs text-zinc-400 font-mono uppercase tracking-wider">
                                        {m.label}
                                    </span>
                                    <div className="flex items-center gap-2">
                                        <span
                                            className={`font-mono text-sm font-bold ${isWin ? 'text-success' : isLoss ? 'text-zinc-500' : 'text-zinc-200'}`}
                                        >
                                            {m.formattedB}
                                        </span>
                                        {isWin && (
                                            <Badge
                                                colorScheme="success"
                                                variant="solid"
                                                size="xs"
                                                className="scale-90"
                                            >
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
