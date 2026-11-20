import {
    Badge,
    Button,
    Card,
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@llm-market-bench/ui-design-system';
import { useMemo, useState } from 'react';
import { signToneOrMuted } from '~/lib/sign-tone';
import { meanConvictionPoints, normalizeConvictionPoints } from '~/shared/conviction';
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
            <TableCell>{pred.ticker}</TableCell>
            <TableCell tone="muted">{pred.target_date}</TableCell>
            <TableCell>
                <Badge variant="soft" colorScheme="neutral" size="sm">
                    {pred.report_timing}
                </Badge>
            </TableCell>
            <TableCell tone="muted">{formatModelName(pred.model_name)}</TableCell>
            <TableCell align="center">
                <Badge
                    variant="soft"
                    colorScheme={pred.predicted_direction === 'UP' ? 'success' : 'danger'}
                    size="sm"
                >
                    {pred.predicted_direction}
                </Badge>
            </TableCell>
            <TableCell align="right">{Math.round(pred.confidence)}%</TableCell>
            <TableCell align="right" tone="muted">
                {pred.open_price ? `$${pred.open_price.toFixed(2)}` : '—'}
            </TableCell>
            <TableCell align="right" tone="muted">
                {pred.close_price ? `$${pred.close_price.toFixed(2)}` : '—'}
            </TableCell>
            <TableCell align="right" tone={signToneOrMuted(returnPct)}>
                {returnPct !== null ? `${returnPct >= 0 ? '+' : ''}${returnPct.toFixed(2)}%` : '—'}
            </TableCell>
            <TableCell align="center">
                {pred.status === 'evaluated' ? (
                    pred.is_correct ? (
                        <Badge variant="soft" colorScheme="success" size="sm">
                            HIT
                        </Badge>
                    ) : (
                        <Badge variant="soft" colorScheme="danger" size="sm">
                            MISS
                        </Badge>
                    )
                ) : (
                    <Badge variant="soft" colorScheme="warning" size="sm">
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
        const models = ['gpt-6-luna', 'deepseek-chat', '~typesafe/jev-latest'];
        return models.map((m) => {
            const modelPreds = predictions.filter((p) => p.model_name === m);
            const evaluated = modelPreds.filter(
                (p) => p.status === 'evaluated' && p.is_correct !== null,
            );
            const correctCount = evaluated.filter((p) => p.is_correct).length;
            const hitRate = evaluated.length > 0 ? (correctCount / evaluated.length) * 100 : 0;
            const meanCp = meanConvictionPoints(evaluated);
            const conviction =
                meanCp === null ? null : Math.round(normalizeConvictionPoints(meanCp) * 10) / 10;

            return {
                modelId: m,
                displayName: formatModelName(m),
                total: modelPreds.length,
                evaluatedCount: evaluated.length,
                hitRate: Math.round(hitRate * 10) / 10,
                conviction,
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
        <div className="flex flex-col gap-6">
            {/* Header info */}
            <div>
                <h2 className="text-sm font-bold font-display uppercase tracking-wider text-voxel-ink">
                    Day-1 Earnings Movement Arena
                </h2>
                <p className="text-xs font-normal text-voxel-muted">
                    Benchmarking LLMs on Regular Trading Hours (09:30 Open to 16:00 Close)
                    continuation versus fade reactions.
                </p>
            </div>

            {/* Model Triad Leaderboard Cards */}
            <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,16rem),1fr))] gap-4 items-stretch">
                {modelStats.map((stat) => (
                    <Card
                        key={stat.modelId}
                        className="p-4 bg-zinc-900/60 border-zinc-800 rounded-none shadow-sm flex flex-col justify-between gap-3"
                    >
                        <div className="flex items-center justify-between">
                            <span className="text-sm font-bold text-voxel-ink">
                                {stat.displayName}
                            </span>
                            <Badge variant="soft" colorScheme="neutral" size="sm">
                                {stat.total} Predictions
                            </Badge>
                        </div>
                        <div className="flex items-baseline justify-between">
                            <div>
                                <div className="text-xs font-normal text-zinc-400">
                                    Hit Rate (Open to Close)
                                </div>
                                <div className="text-sm font-bold font-mono text-emerald-400">
                                    {stat.evaluatedCount > 0 ? `${stat.hitRate}%` : 'Pending'}
                                </div>
                            </div>
                            <div className="text-right">
                                <div className="text-xs font-normal text-zinc-400">
                                    Conviction Score
                                </div>
                                <div className="text-sm font-bold font-mono text-zinc-300">
                                    {stat.conviction === null ? 'N/A' : stat.conviction.toFixed(1)}
                                </div>
                            </div>
                        </div>
                    </Card>
                ))}
            </div>

            {/* Filters Bar */}
            <div className="flex flex-wrap items-center justify-between gap-4 rounded-none bg-zinc-900/40 p-3 border border-zinc-800 shadow-sm">
                <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-sm font-bold text-voxel-muted">Model:</span>
                    <Button
                        type="button"
                        size="sm"
                        variant={selectedModel === 'ALL' ? 'solid' : 'outline'}
                        colorScheme={selectedModel === 'ALL' ? 'accent' : 'neutral'}
                        onClick={() => setSelectedModel('ALL')}
                    >
                        All
                    </Button>
                    <Button
                        type="button"
                        size="sm"
                        variant={selectedModel === 'gpt-6-luna' ? 'solid' : 'outline'}
                        colorScheme={selectedModel === 'gpt-6-luna' ? 'accent' : 'neutral'}
                        onClick={() => setSelectedModel('gpt-6-luna')}
                    >
                        GPT Luna
                    </Button>
                    <Button
                        type="button"
                        size="sm"
                        variant={selectedModel === 'deepseek-chat' ? 'solid' : 'outline'}
                        colorScheme={selectedModel === 'deepseek-chat' ? 'accent' : 'neutral'}
                        onClick={() => setSelectedModel('deepseek-chat')}
                    >
                        DeepSeek
                    </Button>
                    <Button
                        type="button"
                        size="sm"
                        variant={selectedModel === '~typesafe/jev-latest' ? 'solid' : 'outline'}
                        colorScheme={
                            selectedModel === '~typesafe/jev-latest' ? 'accent' : 'neutral'
                        }
                        onClick={() => setSelectedModel('~typesafe/jev-latest')}
                    >
                        TypeSafe Jev
                    </Button>
                </div>

                <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-sm font-bold text-voxel-muted">Direction:</span>
                    <Button
                        type="button"
                        size="sm"
                        variant={selectedDir === 'ALL' ? 'solid' : 'outline'}
                        colorScheme={selectedDir === 'ALL' ? 'accent' : 'neutral'}
                        onClick={() => setSelectedDir('ALL')}
                    >
                        All
                    </Button>
                    <Button
                        type="button"
                        size="sm"
                        variant={selectedDir === 'UP' ? 'solid' : 'outline'}
                        colorScheme={selectedDir === 'UP' ? 'success' : 'neutral'}
                        onClick={() => setSelectedDir('UP')}
                    >
                        UP
                    </Button>
                    <Button
                        type="button"
                        size="sm"
                        variant={selectedDir === 'DOWN' ? 'solid' : 'outline'}
                        colorScheme={selectedDir === 'DOWN' ? 'danger' : 'neutral'}
                        onClick={() => setSelectedDir('DOWN')}
                    >
                        DOWN
                    </Button>
                </div>
            </div>

            {/* Predictions Table */}
            <div className="rounded-none border border-zinc-800 bg-zinc-900/30 overflow-hidden shadow-sm">
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
                                <TableCell
                                    colSpan={10}
                                    align="center"
                                    tone="muted"
                                    className="py-8"
                                >
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
