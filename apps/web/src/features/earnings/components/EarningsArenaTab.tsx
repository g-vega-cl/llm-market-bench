import {
    Badge,
    Card,
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@llm-market-bench/ui-design-system';
import { useMemo, useState } from 'react';
import type { EarningsPrediction } from '../api/fetch-earnings-predictions';

export interface EarningsArenaTabProps {
    predictions: EarningsPrediction[];
}

function formatModelName(model: string): string {
    if (model.includes('luna')) return 'GPT Luna';
    if (model.includes('deepseek')) return 'DeepSeek Flash';
    if (model.includes('jev')) return 'TypeSafe Jev';
    return model;
}

function PredictionTableRow({ pred }: { pred: EarningsPrediction }) {
    const returnPct =
        pred.open_price && pred.close_price && pred.open_price > 0
            ? ((pred.close_price - pred.open_price) / pred.open_price) * 100
            : null;

    return (
        <TableRow key={pred.id} className="border-zinc-800/50 hover:bg-zinc-800/30">
            <TableCell className="font-semibold text-white">{pred.ticker}</TableCell>
            <TableCell className="text-xs text-zinc-400">{pred.target_date}</TableCell>
            <TableCell className="text-xs text-zinc-400">
                <Badge variant="outline" className="border-zinc-700 text-zinc-400">
                    {pred.report_timing}
                </Badge>
            </TableCell>
            <TableCell className="text-xs text-zinc-300">
                {formatModelName(pred.model_name)}
            </TableCell>
            <TableCell className="text-center">
                <Badge
                    className={
                        pred.predicted_direction === 'UP'
                            ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                            : 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                    }
                >
                    {pred.predicted_direction}
                </Badge>
            </TableCell>
            <TableCell className="text-right font-mono text-xs text-zinc-300">
                {Math.round(pred.confidence)}%
            </TableCell>
            <TableCell className="text-right font-mono text-xs text-zinc-400">
                {pred.open_price ? `$${pred.open_price.toFixed(2)}` : '—'}
            </TableCell>
            <TableCell className="text-right font-mono text-xs text-zinc-400">
                {pred.close_price ? `$${pred.close_price.toFixed(2)}` : '—'}
            </TableCell>
            <TableCell
                className={`text-right font-mono text-xs font-semibold ${
                    returnPct !== null
                        ? returnPct >= 0
                            ? 'text-emerald-400'
                            : 'text-rose-400'
                        : 'text-zinc-500'
                }`}
            >
                {returnPct !== null ? `${returnPct >= 0 ? '+' : ''}${returnPct.toFixed(2)}%` : '—'}
            </TableCell>
            <TableCell className="text-center">
                {pred.status === 'evaluated' ? (
                    pred.is_correct ? (
                        <Badge className="bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                            HIT
                        </Badge>
                    ) : (
                        <Badge className="bg-rose-500/20 text-rose-300 border border-rose-500/40">
                            MISS
                        </Badge>
                    )
                ) : (
                    <Badge className="bg-amber-500/10 text-amber-400 border border-amber-500/20">
                        PENDING
                    </Badge>
                )}
            </TableCell>
        </TableRow>
    );
}

export function EarningsArenaTab({ predictions }: EarningsArenaTabProps) {
    const [selectedModel, setSelectedModel] = useState<string>('ALL');
    const [selectedDir, setSelectedDir] = useState<string>('ALL');

    // Pre-calculated model leaderboard metrics
    const modelStats = useMemo(() => {
        const models = ['gpt-5.6-luna', 'deepseek-chat', '~typesafe/jev-latest'];
        return models.map((m) => {
            const modelPreds = predictions.filter((p) => p.model_name === m);
            const evaluated = modelPreds.filter(
                (p) => p.status === 'evaluated' && p.is_correct !== null,
            );
            const correctCount = evaluated.filter((p) => p.is_correct).length;
            const hitRate = evaluated.length > 0 ? (correctCount / evaluated.length) * 100 : 0;
            const avgBrier =
                evaluated.length > 0
                    ? evaluated.reduce((acc, curr) => acc + (curr.brier_score ?? 0), 0) /
                      evaluated.length
                    : 0;

            return {
                modelId: m,
                displayName: formatModelName(m),
                total: modelPreds.length,
                evaluatedCount: evaluated.length,
                hitRate: Math.round(hitRate * 10) / 10,
                avgBrier: Math.round(avgBrier * 1000) / 1000,
            };
        });
    }, [predictions]);

    // Filter predictions
    const filteredPredictions = useMemo(() => {
        return predictions.filter((p) => {
            const matchesModel = selectedModel === 'ALL' || p.model_name === selectedModel;
            const matchesDir = selectedDir === 'ALL' || p.predicted_direction === selectedDir;
            return matchesModel && matchesDir;
        });
    }, [predictions, selectedModel, selectedDir]);

    return (
        <div className="space-y-6">
            {/* Header info */}
            <div>
                <h2 className="text-xl font-bold tracking-tight text-white">
                    Day-1 Earnings Movement Arena
                </h2>
                <p className="text-sm text-zinc-400">
                    Benchmarking LLMs on Regular Trading Hours (09:30 Open to 16:00 Close)
                    continuation versus fade reactions.
                </p>
            </div>

            {/* Model Triad Leaderboard Cards */}
            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                {modelStats.map((stat) => (
                    <Card key={stat.modelId} className="p-4 bg-zinc-900/60 border-zinc-800">
                        <div className="flex items-center justify-between">
                            <span className="text-sm font-semibold text-white">
                                {stat.displayName}
                            </span>
                            <Badge
                                variant="outline"
                                className="text-xs border-zinc-700 text-zinc-400"
                            >
                                {stat.total} Predictions
                            </Badge>
                        </div>
                        <div className="mt-3 flex items-baseline justify-between">
                            <div>
                                <div className="text-xs text-zinc-400">
                                    Hit Rate (Open to Close)
                                </div>
                                <div className="text-2xl font-bold text-emerald-400">
                                    {stat.evaluatedCount > 0 ? `${stat.hitRate}%` : 'Pending'}
                                </div>
                            </div>
                            <div className="text-right">
                                <div className="text-xs text-zinc-400">Avg Brier Score</div>
                                <div className="text-sm font-mono text-zinc-300">
                                    {stat.evaluatedCount > 0 ? stat.avgBrier.toFixed(3) : 'N/A'}
                                </div>
                            </div>
                        </div>
                    </Card>
                ))}
            </div>

            {/* Filters Bar */}
            <div className="flex flex-wrap items-center justify-between gap-4 rounded-lg bg-zinc-900/40 p-3 border border-zinc-800/80">
                <div className="flex items-center gap-2">
                    <span className="text-xs font-medium text-zinc-400">Model:</span>
                    <button
                        type="button"
                        onClick={() => setSelectedModel('ALL')}
                        className={`px-2.5 py-1 text-xs rounded transition-colors ${
                            selectedModel === 'ALL'
                                ? 'bg-zinc-700 text-white font-medium'
                                : 'text-zinc-400 hover:text-white'
                        }`}
                    >
                        All
                    </button>
                    <button
                        type="button"
                        onClick={() => setSelectedModel('gpt-5.6-luna')}
                        className={`px-2.5 py-1 text-xs rounded transition-colors ${
                            selectedModel === 'gpt-5.6-luna'
                                ? 'bg-zinc-700 text-white font-medium'
                                : 'text-zinc-400 hover:text-white'
                        }`}
                    >
                        GPT Luna
                    </button>
                    <button
                        type="button"
                        onClick={() => setSelectedModel('deepseek-chat')}
                        className={`px-2.5 py-1 text-xs rounded transition-colors ${
                            selectedModel === 'deepseek-chat'
                                ? 'bg-zinc-700 text-white font-medium'
                                : 'text-zinc-400 hover:text-white'
                        }`}
                    >
                        DeepSeek
                    </button>
                    <button
                        type="button"
                        onClick={() => setSelectedModel('~typesafe/jev-latest')}
                        className={`px-2.5 py-1 text-xs rounded transition-colors ${
                            selectedModel === '~typesafe/jev-latest'
                                ? 'bg-zinc-700 text-white font-medium'
                                : 'text-zinc-400 hover:text-white'
                        }`}
                    >
                        TypeSafe Jev
                    </button>
                </div>

                <div className="flex items-center gap-2">
                    <span className="text-xs font-medium text-zinc-400">Direction:</span>
                    <button
                        type="button"
                        onClick={() => setSelectedDir('ALL')}
                        className={`px-2.5 py-1 text-xs rounded transition-colors ${
                            selectedDir === 'ALL'
                                ? 'bg-zinc-700 text-white font-medium'
                                : 'text-zinc-400 hover:text-white'
                        }`}
                    >
                        All
                    </button>
                    <button
                        type="button"
                        onClick={() => setSelectedDir('UP')}
                        className={`px-2.5 py-1 text-xs rounded transition-colors ${
                            selectedDir === 'UP'
                                ? 'bg-emerald-500/20 text-emerald-300 font-medium'
                                : 'text-zinc-400 hover:text-white'
                        }`}
                    >
                        UP
                    </button>
                    <button
                        type="button"
                        onClick={() => setSelectedDir('DOWN')}
                        className={`px-2.5 py-1 text-xs rounded transition-colors ${
                            selectedDir === 'DOWN'
                                ? 'bg-rose-500/20 text-rose-300 font-medium'
                                : 'text-zinc-400 hover:text-white'
                        }`}
                    >
                        DOWN
                    </button>
                </div>
            </div>

            {/* Predictions Table */}
            <div className="rounded-lg border border-zinc-800 bg-zinc-900/30 overflow-hidden">
                <Table>
                    <TableHeader className="bg-zinc-900/80">
                        <TableRow className="border-zinc-800">
                            <TableHead className="text-zinc-400">Ticker</TableHead>
                            <TableHead className="text-zinc-400">Target Date</TableHead>
                            <TableHead className="text-zinc-400">Timing</TableHead>
                            <TableHead className="text-zinc-400">Model</TableHead>
                            <TableHead className="text-center text-zinc-400">Prediction</TableHead>
                            <TableHead className="text-right text-zinc-400">Confidence</TableHead>
                            <TableHead className="text-right text-zinc-400">RTH Open</TableHead>
                            <TableHead className="text-right text-zinc-400">RTH Close</TableHead>
                            <TableHead className="text-right text-zinc-400">Day-1 Return</TableHead>
                            <TableHead className="text-center text-zinc-400">Outcome</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {filteredPredictions.length === 0 ? (
                            <TableRow>
                                <TableCell colSpan={10} className="py-8 text-center text-zinc-500">
                                    No earnings predictions found matching filters.
                                </TableCell>
                            </TableRow>
                        ) : (
                            filteredPredictions.map((pred) => (
                                <PredictionTableRow key={pred.id} pred={pred} />
                            ))
                        )}
                    </TableBody>
                </Table>
            </div>
        </div>
    );
}
