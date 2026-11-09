import { Badge, Card } from '@llm-market-bench/ui-design-system';
import type { DailyPrediction } from '../api/fetch-daily-predictions';

export interface HeroPredictionCardProps {
    prediction: DailyPrediction;
}

export function HeroPredictionCard({ prediction }: HeroPredictionCardProps) {
    const isHold =
        prediction.predicted_direction === 'HOLD' ||
        (prediction.predicted_direction as string) === 'NO_TRADE' ||
        prediction.confidence === 0;
    const isUp = prediction.predicted_direction === 'UP';

    const directionColor = isHold ? 'text-amber-400' : isUp ? 'text-emerald-400' : 'text-rose-400';

    const directionText = isHold ? '◆ HOLD' : isUp ? '▲ UP' : '▼ DOWN';

    return (
        <Card className="p-6 bg-boxel-surface text-boxel-ink rounded-none border border-boxel-bevel-hi flex flex-col gap-4 shadow-xl">
            <div className="flex justify-between items-center">
                <span className="text-sm font-bold uppercase tracking-wider text-boxel-muted">
                    Latest Prediction • {prediction.target_date} ({prediction.ticker})
                </span>
                <Badge
                    colorScheme={prediction.status === 'evaluated' ? 'neutral' : 'info'}
                    variant="soft"
                    size="sm"
                    className="font-bold"
                >
                    {prediction.status.toUpperCase()}
                </Badge>
            </div>

            <div className="flex items-baseline gap-4 flex-wrap">
                <span className={`text-lg font-bold ${directionColor}`}>{directionText}</span>
                <span className="text-sm font-bold text-boxel-ink">
                    {prediction.confidence}% Confidence
                </span>
                {prediction.expected_return_pct !== null && (
                    <span className="text-xs font-normal text-boxel-muted">
                        (Expected Return: {prediction.expected_return_pct > 0 ? '+' : ''}
                        {prediction.expected_return_pct}%)
                    </span>
                )}
            </div>

            {prediction.rationale && (
                <div className="text-xs font-normal leading-relaxed text-boxel-ink">
                    <strong className="font-bold">Rationale:</strong> {prediction.rationale}
                </div>
            )}

            {prediction.catalysts && prediction.catalysts.length > 0 && (
                <div className="flex gap-2 flex-wrap">
                    {prediction.catalysts.map((cat) => (
                        <Badge
                            key={cat}
                            colorScheme="neutral"
                            variant="soft"
                            size="xs"
                            className="text-boxel-ink bg-boxel-trough border border-boxel-bevel-hi"
                        >
                            {cat}
                        </Badge>
                    ))}
                </div>
            )}
        </Card>
    );
}
