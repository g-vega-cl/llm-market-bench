import type { PromptExperiment } from '@llm-market-bench/database';
import {
    Badge,
    Button,
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@llm-market-bench/ui-design-system';
import { useState } from 'react';
import type { DailyPrediction } from '../api/fetch-daily-predictions';
import { DailyPostMortemCard } from './DailyPostMortemCard';
import { MarketContextViewer } from './MarketContextViewer';

export interface PredictionsTableProps {
    predictions: DailyPrediction[];
    experiments: PromptExperiment[];
}

interface PredictionRowProps {
    p: DailyPrediction;
    isExpanded: boolean;
    onToggleExpand: () => void;
    matchingExp?: PromptExperiment;
}

function PredictionExpandedDetail({
    p,
    matchingExp,
}: {
    p: DailyPrediction;
    matchingExp?: PromptExperiment;
}) {
    return (
        <TableRow className="bg-zinc-50 dark:bg-zinc-950/60 border-b border-zinc-200 dark:border-zinc-800">
            <TableCell colSpan={11} className="p-6">
                <div className="flex flex-col gap-4">
                    {/* Rationale & Catalysts */}
                    <div>
                        <div className="text-xs font-bold text-zinc-500 dark:text-zinc-400 mb-1.5 uppercase tracking-wider">
                            Prediction Rationale & Catalysts
                        </div>
                        <p className="text-sm text-zinc-800 dark:text-zinc-200 mb-2.5 leading-relaxed">
                            {p.rationale || 'No detailed rationale recorded for this prediction.'}
                        </p>
                        {p.catalysts && p.catalysts.length > 0 && (
                            <div className="flex gap-2 flex-wrap">
                                {p.catalysts.map((cat) => (
                                    <Badge key={cat} colorScheme="neutral" variant="soft" size="xs">
                                        {cat}
                                    </Badge>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* Price & Intraday Metrics */}
                    <div className="flex gap-5 text-xs text-zinc-500 dark:text-zinc-400 flex-wrap">
                        <div>
                            <strong>Expected Return:</strong>{' '}
                            {p.expected_return_pct !== null
                                ? `${p.expected_return_pct > 0 ? '+' : ''}${p.expected_return_pct}%`
                                : '-'}
                        </div>
                        <div>
                            <strong>Open:</strong>{' '}
                            {p.open_price !== null ? `$${p.open_price.toFixed(2)}` : '-'}
                        </div>
                        <div>
                            <strong>High:</strong>{' '}
                            {p.high_price !== null && p.high_price !== undefined
                                ? `$${p.high_price.toFixed(2)}`
                                : '-'}
                        </div>
                        <div>
                            <strong>Low:</strong>{' '}
                            {p.low_price !== null && p.low_price !== undefined
                                ? `$${p.low_price.toFixed(2)}`
                                : '-'}
                        </div>
                        <div>
                            <strong>Close:</strong>{' '}
                            {p.close_price !== null ? `$${p.close_price.toFixed(2)}` : '-'}
                        </div>
                        <div>
                            <strong>Model:</strong> {p.model_name}
                        </div>
                    </div>

                    {/* Post-Market Post-Mortem & Causal Lessons (GPT-5.6 Luna) */}
                    <DailyPostMortemCard prediction={p} />

                    {/* Market Context Passed to Predictor */}
                    <MarketContextViewer context={p.market_context} />

                    {/* System Prompt Used */}
                    <div>
                        <div className="flex items-center gap-2 mb-2">
                            <span className="text-xs font-bold text-zinc-500 dark:text-zinc-400">
                                SYSTEM PROMPT VARIANT:
                            </span>
                            <Badge colorScheme="info" variant="soft" size="xs">
                                {p.prompt_variant_tag || 'baseline'}
                            </Badge>
                        </div>
                        <pre className="whitespace-pre-wrap break-words font-mono text-xs bg-white dark:bg-zinc-900 p-3.5 rounded-lg border border-zinc-200 dark:border-zinc-800 text-zinc-700 dark:text-zinc-300 m-0">
                            {matchingExp?.prompt_content ||
                                'Standard baseline system prompt active during prediction.'}
                        </pre>
                    </div>
                </div>
            </TableCell>
        </TableRow>
    );
}

function PredictionTableRowItem({
    p,
    isExpanded,
    onToggleExpand,
    matchingExp,
}: PredictionRowProps) {
    return (
        <>
            <TableRow className="border-b border-zinc-100 dark:border-zinc-800/60">
                <TableCell className="font-semibold text-zinc-900 dark:text-zinc-100">
                    {p.target_date}
                </TableCell>
                <TableCell>{p.ticker}</TableCell>
                <TableCell
                    className={`font-bold ${
                        p.predicted_direction === 'UP' ? 'text-emerald-600' : 'text-rose-600'
                    }`}
                >
                    {p.predicted_direction}
                </TableCell>
                <TableCell>{p.confidence}%</TableCell>
                <TableCell>{p.open_price != null ? `$${p.open_price.toFixed(2)}` : '-'}</TableCell>
                <TableCell>
                    {p.close_price != null ? `$${p.close_price.toFixed(2)}` : '-'}
                </TableCell>
                <TableCell className="font-semibold">{p.actual_direction || '-'}</TableCell>
                <TableCell>
                    {p.intraday_hit === true && (
                        <Badge colorScheme="info" variant="soft" size="xs">
                            HIT
                        </Badge>
                    )}
                    {p.intraday_hit === false && (
                        <Badge colorScheme="warning" variant="soft" size="xs">
                            MISSED
                        </Badge>
                    )}
                    {p.intraday_hit === null && <span className="text-zinc-400 text-xs">-</span>}
                </TableCell>
                <TableCell>
                    {p.is_correct === true && (
                        <Badge colorScheme="success" variant="soft" size="xs">
                            PASS
                        </Badge>
                    )}
                    {p.is_correct === false && (
                        <Badge colorScheme="danger" variant="soft" size="xs">
                            FAIL
                        </Badge>
                    )}
                    {p.is_correct === null && (
                        <Badge colorScheme="neutral" variant="soft" size="xs">
                            PENDING
                        </Badge>
                    )}
                </TableCell>
                <TableCell>{p.brier_score !== null ? p.brier_score.toFixed(4) : '-'}</TableCell>
                <TableCell>
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={onToggleExpand}
                        className="text-xs font-semibold"
                    >
                        {isExpanded ? 'Hide Details' : 'View Details & Prompt'}
                    </Button>
                </TableCell>
            </TableRow>
            {isExpanded && <PredictionExpandedDetail p={p} matchingExp={matchingExp} />}
        </>
    );
}

export function PredictionsTable({ predictions, experiments }: PredictionsTableProps) {
    const [expandedId, setExpandedId] = useState<string | null>(null);

    return (
        <Table containerClassName="rounded-xl border border-zinc-200 dark:border-zinc-800">
            <TableHeader>
                <TableRow>
                    <TableHead>Date</TableHead>
                    <TableHead>Ticker</TableHead>
                    <TableHead>Prediction</TableHead>
                    <TableHead>Confidence</TableHead>
                    <TableHead>Open Price</TableHead>
                    <TableHead>Close Price</TableHead>
                    <TableHead>Actual Dir</TableHead>
                    <TableHead>Intraday Hit</TableHead>
                    <TableHead>Outcome</TableHead>
                    <TableHead>Brier Score</TableHead>
                    <TableHead>Prompt & Rationale</TableHead>
                </TableRow>
            </TableHeader>
            <TableBody>
                {predictions.map((p) => {
                    const isExpanded = expandedId === p.id;
                    const matchingExp = experiments.find(
                        (e) => e.variant_tag === p.prompt_variant_tag,
                    );

                    return (
                        <PredictionTableRowItem
                            key={p.id}
                            p={p}
                            isExpanded={isExpanded}
                            onToggleExpand={() => setExpandedId(isExpanded ? null : p.id)}
                            matchingExp={matchingExp}
                        />
                    );
                })}

                {predictions.length === 0 && (
                    <TableRow>
                        <TableCell
                            colSpan={11}
                            className="p-6 text-center text-zinc-400 dark:text-zinc-500"
                        >
                            No daily predictions logged yet. Run `python main.py --daily-predictor`
                            to generate one.
                        </TableCell>
                    </TableRow>
                )}
            </TableBody>
        </Table>
    );
}
