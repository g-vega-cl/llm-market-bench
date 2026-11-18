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
        <TableRow className="bg-voxel-trough border-b border-voxel-bevel-hi">
            <TableCell colSpan={11} className="p-6">
                <div className="flex flex-col gap-4">
                    {/* Rationale & Catalysts */}
                    <div>
                        <div className="text-sm font-bold text-voxel-muted mb-1.5 uppercase tracking-wider">
                            Prediction Rationale & Catalysts
                        </div>
                        <p className="text-sm text-voxel-ink mb-2.5 leading-relaxed">
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
                    <div className="flex gap-5 text-xs text-voxel-muted flex-wrap">
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

                    {/* Post-Market Post-Mortem & Causal Lessons (GPT-6 Luna) */}
                    <DailyPostMortemCard prediction={p} />

                    {/* Market Context Passed to Predictor */}
                    <MarketContextViewer context={p.market_context} />

                    {/* System Prompt Used */}
                    <div className="flex flex-col gap-2">
                        <div className="flex items-center gap-2">
                            <span className="text-sm font-bold text-voxel-muted">
                                SYSTEM PROMPT VARIANT:
                            </span>
                            <Badge colorScheme="info" variant="soft" size="xs">
                                {p.prompt_variant_tag || 'baseline'}
                            </Badge>
                        </div>
                        <pre className="whitespace-pre-wrap break-words font-mono text-xs bg-voxel-surface p-3.5 rounded-none border border-voxel-bevel-hi text-voxel-ink m-0">
                            {matchingExp?.prompt_content ||
                                'Standard baseline system prompt active during prediction.'}
                        </pre>
                    </div>
                </div>
            </TableCell>
        </TableRow>
    );
}

function ConvictionCell({ value }: { value: number | null | undefined }) {
    if (value === null || value === undefined) {
        return <span className="font-mono text-zinc-400">-</span>;
    }
    const sign = value >= 0 ? '+' : '';
    return (
        <span className={`font-mono ${value >= 0 ? 'text-success' : 'text-danger'}`}>
            {sign}
            {value.toFixed(2)}
        </span>
    );
}

function PredictionIntradayHitBadge({ p }: { p: DailyPrediction }) {
    if (p.intraday_hit === true) {
        return (
            <Badge colorScheme="info" variant="soft" size="xs">
                HIT
            </Badge>
        );
    }
    if (p.intraday_hit === false) {
        return (
            <Badge colorScheme="warning" variant="soft" size="xs">
                MISSED
            </Badge>
        );
    }
    return <span className="text-zinc-400 text-xs">-</span>;
}

function PredictionOutcomeBadge({ p }: { p: DailyPrediction }) {
    if (p.predicted_direction === 'HOLD' && p.status === 'evaluated') {
        return (
            <Badge colorScheme="warning" variant="soft" size="xs">
                HOLD
            </Badge>
        );
    }
    if (p.is_correct === true) {
        return (
            <Badge colorScheme="success" variant="soft" size="xs">
                PASS
            </Badge>
        );
    }
    if (p.is_correct === false) {
        return (
            <Badge colorScheme="danger" variant="soft" size="xs">
                FAIL
            </Badge>
        );
    }
    return (
        <Badge colorScheme="neutral" variant="soft" size="xs">
            PENDING
        </Badge>
    );
}

function PredictionTableRowItem({
    p,
    isExpanded,
    onToggleExpand,
    matchingExp,
}: PredictionRowProps) {
    const dirClass =
        p.predicted_direction === 'UP'
            ? 'text-success'
            : p.predicted_direction === 'HOLD'
              ? 'text-accent'
              : 'text-danger';

    return (
        <>
            <TableRow className="border-b border-voxel-bevel-lo">
                <TableCell className="font-bold text-sm text-voxel-ink font-mono">
                    {p.target_date}
                </TableCell>
                <TableCell>{p.ticker}</TableCell>
                <TableCell className={`font-bold ${dirClass}`}>{p.predicted_direction}</TableCell>
                <TableCell>{p.confidence}%</TableCell>
                <TableCell>{p.open_price != null ? `$${p.open_price.toFixed(2)}` : '-'}</TableCell>
                <TableCell>
                    {p.close_price != null ? `$${p.close_price.toFixed(2)}` : '-'}
                </TableCell>
                <TableCell className="font-bold text-sm">{p.actual_direction || '-'}</TableCell>
                <TableCell>
                    <PredictionIntradayHitBadge p={p} />
                </TableCell>
                <TableCell>
                    <PredictionOutcomeBadge p={p} />
                </TableCell>
                <TableCell>
                    <ConvictionCell value={p.conviction_score} />
                </TableCell>
                <TableCell>
                    <Button
                        variant="outline"
                        colorScheme="neutral"
                        size="sm"
                        onClick={onToggleExpand}
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
        <Table containerClassName="rounded-none border border-voxel-bevel-hi">
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
                    <TableHead>Conviction</TableHead>
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
                        <TableCell colSpan={11} className="p-6 text-center text-voxel-muted">
                            No daily predictions logged yet. Run `python main.py --daily-predictor`
                            to generate one.
                        </TableCell>
                    </TableRow>
                )}
            </TableBody>
        </Table>
    );
}
