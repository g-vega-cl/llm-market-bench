import type { LLMLeaderboardRow } from '@llm-market-bench/database';
import { Badge, Card } from '@llm-market-bench/ui-design-system';
import { getModelDisplayInfo } from '../lib/model-helper';

interface LeaderboardPodiumProps {
    models: LLMLeaderboardRow[];
}

interface PodiumCardProps {
    model: LLMLeaderboardRow;
    place: number;
}

function PodiumCard({ model, place }: PodiumCardProps) {
    const info = getModelDisplayInfo(model.model_name);
    const isFirst = place === 1;
    const isSecond = place === 2;

    const heightClass = isFirst
        ? 'md:min-h-[400px] h-auto border-emerald-500/50 dark:border-emerald-500/30 shadow-[0_0_25px_rgba(52,211,153,0.15)]'
        : isSecond
          ? 'md:min-h-[350px] h-auto border-blue-500/30 dark:border-blue-500/20'
          : 'md:min-h-[320px] h-auto border-amber-500/30 dark:border-amber-500/20';

    const badgeColor = isFirst ? 'success' : isSecond ? 'accent' : 'warning';

    return (
        <Card
            variant="glass"
            isHoverable
            radius="3xl"
            className={`relative flex flex-col justify-between w-full md:w-80 p-8 ${heightClass}`}
        >
            {/* Rank Badge */}
            <div className="absolute -top-4 left-1/2 -translate-x-1/2">
                <Badge colorScheme={badgeColor} variant="solid" size="md">
                    Place #{place}
                </Badge>
            </div>

            {/* Top Section */}
            <div className="text-center pt-4 space-y-4">
                <div className="text-4xl">{info.emoji}</div>
                <div>
                    <h3 className="font-heading text-lg font-bold text-zinc-100 line-clamp-1">
                        {info.name}
                    </h3>
                    <p className="text-xs text-zinc-500 font-mono tracking-wider truncate">
                        {model.model_name}
                    </p>
                </div>

                {/* Composite Leaderboard Score */}
                <div className="inline-block px-4 py-2 bg-white/5 border border-white/10 rounded-2xl">
                    <span className="text-[10px] font-black text-zinc-400 uppercase tracking-widest block">
                        Leaderboard Score
                    </span>
                    <span className="text-3xl font-black font-mono text-zinc-100">
                        {model.composite_score.toFixed(1)}%
                    </span>
                </div>
            </div>

            {/* Metrics Breakdown */}
            <div className="mt-8 space-y-3 pt-6 border-t border-white/5 text-xs font-mono">
                <div className="flex justify-between items-center">
                    <span className="text-zinc-500 uppercase tracking-wider text-[10px]">
                        Return %
                    </span>
                    <span
                        className={`font-black ${model.return_pct >= 0 ? 'text-success' : 'text-danger'}`}
                    >
                        {model.return_pct >= 0 ? '+' : ''}
                        {model.return_pct.toFixed(2)}%
                    </span>
                </div>
                <div className="flex justify-between items-center">
                    <span className="text-zinc-500 uppercase tracking-wider text-[10px]">
                        Win Rate
                    </span>
                    <span className="text-zinc-300 font-bold">{model.win_rate.toFixed(1)}%</span>
                </div>
                <div className="flex justify-between items-center">
                    <span className="text-zinc-500 uppercase tracking-wider text-[10px]">
                        Approval
                    </span>
                    <span className="text-zinc-300 font-bold">
                        {model.verifier_approval_rate !== null &&
                        model.verifier_approval_rate !== undefined
                            ? `${model.verifier_approval_rate.toFixed(1)}%`
                            : '—'}
                    </span>
                </div>
                <div className="flex justify-between items-center">
                    <span className="text-zinc-500 uppercase tracking-wider text-[10px]">
                        Consistency
                    </span>
                    <span className="text-zinc-300 font-bold">
                        {model.consistency_score.toFixed(1)}%
                    </span>
                </div>
            </div>
        </Card>
    );
}

export function LeaderboardPodium({ models }: LeaderboardPodiumProps) {
    // Top 3 models
    const top3 = models.slice(0, 3);
    if (top3.length === 0) return null;

    // We want to order them as: 2nd, 1st, 3rd for athletic podium look
    const podiumItems = [];
    if (top3[1]) podiumItems.push({ model: top3[1], place: 2 });
    if (top3[0]) podiumItems.push({ model: top3[0], place: 1 });
    if (top3[2]) podiumItems.push({ model: top3[2], place: 3 });

    // Ensure they are rendered in the correct visual order (Left: 2nd, Center: 1st, Right: 3rd)
    const sortedPodium = podiumItems.sort((a, b) => {
        const order = [2, 1, 3];
        return order.indexOf(a.place) - order.indexOf(b.place);
    });

    return (
        <div className="flex flex-col md:flex-row items-stretch md:items-end justify-center gap-6 py-8 animate-slide-up">
            {sortedPodium.map(({ model, place }) => (
                <PodiumCard key={model.model_name} model={model} place={place} />
            ))}
        </div>
    );
}
