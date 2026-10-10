import { Badge, Card } from '@llm-market-bench/ui-design-system';
import type { DailyPrediction } from '../api/fetch-daily-predictions';

export interface HeroPredictionCardProps {
    prediction: DailyPrediction;
}

export function HeroPredictionCard({ prediction }: HeroPredictionCardProps) {
    const isNoTrade =
        (prediction.predicted_direction as string) === 'NO_TRADE' || prediction.confidence === 0;
    const isUp = prediction.predicted_direction === 'UP';

    const directionColor = isNoTrade
        ? 'text-amber-400'
        : isUp
          ? 'text-emerald-400'
          : 'text-rose-400';

    const directionText = isNoTrade ? '⚡ NO TRADE' : isUp ? '▲ UP' : '▼ DOWN';

    return (
        <Card className="p-6 bg-gradient-to-br from-slate-900 to-slate-950 text-white rounded-2xl border border-slate-800 shadow-xl mb-8">
            <div className="flex justify-between items-center mb-4">
                <span className="text-xs uppercase tracking-wider text-slate-400 font-semibold">
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

            <div className="flex items-baseline gap-4 mb-4 flex-wrap">
                <span className={`text-4xl font-black ${directionColor}`}>{directionText}</span>
                <span className="text-xl font-semibold text-slate-200">
                    {prediction.confidence}% Confidence
                </span>
                {prediction.expected_return_pct !== null && (
                    <span className="text-base text-slate-400">
                        (Expected Return: {prediction.expected_return_pct > 0 ? '+' : ''}
                        {prediction.expected_return_pct}%)
                    </span>
                )}
            </div>

            {prediction.rationale && (
                <div className="text-sm leading-relaxed text-slate-300 mb-4">
                    <strong>Rationale:</strong> {prediction.rationale}
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
                            className="text-slate-200 bg-slate-800 border border-slate-700"
                        >
                            {cat}
                        </Badge>
                    ))}
                </div>
            )}
        </Card>
    );
}
