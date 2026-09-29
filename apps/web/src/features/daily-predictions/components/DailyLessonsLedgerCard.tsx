import { Badge, Card, SectionHeading } from '@llm-market-bench/ui-design-system';
import type { DailyPrediction } from '../api/fetch-daily-predictions';

export interface DailyLessonsLedgerCardProps {
    predictions?: DailyPrediction[];
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

function LessonItem({ prediction }: { prediction: DailyPrediction }) {
    const category = prediction.postmortem_category;
    const categoryScheme = getCategoryColorScheme(category);
    const hasFlawedAssumption =
        Boolean(prediction.postmortem_flawed_assumption) &&
        prediction.postmortem_flawed_assumption?.trim().toLowerCase() !== 'none';

    return (
        <div className="p-4 rounded-xl bg-zinc-900/40 border border-zinc-800 space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-bold text-zinc-300">
                        {prediction.target_date}
                    </span>
                    <Badge
                        variant="soft"
                        colorScheme={prediction.is_correct ? 'success' : 'danger'}
                        size="xs"
                        radius="md"
                    >
                        {prediction.is_correct ? 'CORRECT' : 'MISSED'}
                    </Badge>
                    <span className="text-xs font-bold text-zinc-400">
                        {prediction.predicted_direction === 'UP' ? '▲ UP' : '▼ DOWN'} (
                        {prediction.confidence}%)
                    </span>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                    {category && (
                        <Badge variant="solid" colorScheme={categoryScheme} size="xs" radius="md">
                            {category.replace(/_/g, ' ')}
                        </Badge>
                    )}
                    {prediction.was_predictable !== null &&
                        prediction.was_predictable !== undefined && (
                            <Badge
                                variant={prediction.was_predictable ? 'outline' : 'soft'}
                                colorScheme={prediction.was_predictable ? 'accent' : 'neutral'}
                                size="xs"
                                radius="md"
                            >
                                {prediction.was_predictable ? 'PREDICTABLE' : 'UNFORESEEN'}
                            </Badge>
                        )}
                </div>
            </div>

            {hasFlawedAssumption && (
                <div className="space-y-1">
                    <div className="text-[10px] font-bold uppercase tracking-wider text-rose-400">
                        Flawed Morning Assumption
                    </div>
                    <p className="text-xs text-rose-300/90 leading-relaxed p-2.5 rounded-lg bg-rose-950/20 border border-rose-900/30">
                        {prediction.postmortem_flawed_assumption}
                    </p>
                </div>
            )}

            {prediction.postmortem_lesson && (
                <div className="space-y-1">
                    <div className="text-[10px] font-bold uppercase tracking-wider text-emerald-400">
                        Actionable Lesson
                    </div>
                    <p className="text-xs text-emerald-300/90 leading-relaxed font-medium p-2.5 rounded-lg bg-emerald-950/20 border border-emerald-900/30">
                        {prediction.postmortem_lesson}
                    </p>
                </div>
            )}
        </div>
    );
}

export function DailyLessonsLedgerCard({ predictions = [] }: DailyLessonsLedgerCardProps) {
    const predictionsWithLessons = predictions.filter((p) =>
        Boolean(p.postmortem_lesson || p.postmortem_category),
    );

    // Sort by target_date descending
    const sortedLessons = [...predictionsWithLessons].sort((a, b) =>
        b.target_date.localeCompare(a.target_date),
    );

    return (
        <Card className="p-5 space-y-5 min-w-0">
            <div className="space-y-1">
                <SectionHeading>Daily Causal Lessons & Post-Mortems</SectionHeading>
                <p className="text-xs text-zinc-400 leading-relaxed">
                    Durable causal rules and flawed assumptions diagnosed daily at 5:15 PM ET by
                    GPT-5.6 Luna to feed weekly Sunday autoresearch prompt evolution.
                </p>
            </div>

            {sortedLessons.length === 0 ? (
                <div className="p-4 bg-zinc-900/40 rounded-xl border border-zinc-800 text-xs text-zinc-400 italic">
                    No daily post-mortem lessons recorded for this track yet. Evaluations run
                    automatically at session close (5:15 PM ET).
                </div>
            ) : (
                <div className="space-y-3">
                    {sortedLessons.map((p) => (
                        <LessonItem key={p.id} prediction={p} />
                    ))}
                </div>
            )}
        </Card>
    );
}
