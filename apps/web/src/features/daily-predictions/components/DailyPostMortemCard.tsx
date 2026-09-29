import { Badge } from '@llm-market-bench/ui-design-system';
import type { DailyPrediction } from '../api/fetch-daily-predictions';

export interface DailyPostMortemCardProps {
    prediction: DailyPrediction;
}

function getCategoryColorScheme(
    category?: string | null,
): 'success' | 'danger' | 'warning' | 'info' | 'neutral' {
    switch (category) {
        case 'ACCURATE_CAPTURE':
            return 'success';
        case 'INTRADAY_REVERSAL':
        case 'CATALYST_INVERSION':
            return 'danger';
        case 'TIMID_MAGNITUDE':
            return 'info';
        case 'OVERSHOT_TARGET':
        case 'UNFORESEEN_SHOCK':
            return 'warning';
        default:
            return 'neutral';
    }
}

export function DailyPostMortemCard({ prediction }: DailyPostMortemCardProps) {
    const hasPostMortem = Boolean(
        prediction.postmortem_evaluated_at ||
            prediction.postmortem_category ||
            prediction.postmortem_lesson,
    );

    if (!hasPostMortem) {
        return null;
    }

    const category = prediction.postmortem_category;
    const categoryScheme = getCategoryColorScheme(category);
    const hasFlawedAssumption =
        Boolean(prediction.postmortem_flawed_assumption) &&
        prediction.postmortem_flawed_assumption?.trim().toLowerCase() !== 'none';

    return (
        <div className="space-y-3 p-4 rounded-xl bg-zinc-900/60 border border-zinc-800">
            <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                    <span className="text-xs font-bold uppercase tracking-wider text-zinc-300">
                        Post-Market Evaluation (GPT-5.6 Luna)
                    </span>
                    {prediction.postmortem_evaluated_at && (
                        <span className="text-[10px] text-zinc-500 font-mono">
                            {new Date(prediction.postmortem_evaluated_at).toLocaleTimeString([], {
                                hour: '2-digit',
                                minute: '2-digit',
                            })}{' '}
                            ET
                        </span>
                    )}
                </div>

                <div className="flex flex-wrap items-center gap-2">
                    {category && (
                        <Badge variant="solid" colorScheme={categoryScheme} size="sm" radius="md">
                            {category.replace(/_/g, ' ')}
                        </Badge>
                    )}
                    {prediction.was_predictable !== null &&
                        prediction.was_predictable !== undefined && (
                            <Badge
                                variant={prediction.was_predictable ? 'outline' : 'soft'}
                                colorScheme={prediction.was_predictable ? 'accent' : 'neutral'}
                                size="sm"
                                radius="md"
                            >
                                {prediction.was_predictable
                                    ? 'PREDICTABLE PRE-MARKET'
                                    : 'UNFORESEEN / NOISE'}
                            </Badge>
                        )}
                </div>
            </div>

            {/* Flawed Assumption (if any) */}
            {hasFlawedAssumption && (
                <div className="space-y-1">
                    <div className="text-[11px] font-bold uppercase tracking-wider text-rose-400">
                        Flawed Morning Assumption
                    </div>
                    <p className="text-xs text-rose-300 leading-relaxed p-3 rounded-lg bg-rose-950/30 border border-rose-900/40">
                        {prediction.postmortem_flawed_assumption}
                    </p>
                </div>
            )}

            {/* Actionable Lesson Learned */}
            {prediction.postmortem_lesson && (
                <div className="space-y-1">
                    <div className="text-[11px] font-bold uppercase tracking-wider text-emerald-400 flex items-center gap-1.5">
                        <span>Actionable Lesson Learned</span>
                    </div>
                    <p className="text-xs text-emerald-200 leading-relaxed font-medium p-3 rounded-lg bg-emerald-950/30 border border-emerald-900/40">
                        {prediction.postmortem_lesson}
                    </p>
                </div>
            )}
        </div>
    );
}
