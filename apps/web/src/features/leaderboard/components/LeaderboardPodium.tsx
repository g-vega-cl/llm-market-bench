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

    const borderClass = isFirst
        ? 'border-t-success border-l-success'
        : isSecond
          ? 'border-t-accent border-l-accent'
          : 'border-t-warning border-l-warning';

    const badgeColor = isFirst ? 'success' : isSecond ? 'accent' : 'warning';

    return (
        <Card
            variant="default"
            isHoverable
            radius="none"
            className={`relative flex flex-col justify-between w-full h-full p-6 ${borderClass}`}
        >
            {/* Rank Badge */}
            <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                <Badge colorScheme={badgeColor} variant="solid" size="sm">
                    Place #{place}
                </Badge>
            </div>

            {/* Top Section */}
            <div className="text-center pt-2 flex flex-col gap-3">
                <div className="text-lg font-bold">{info.emoji}</div>
                <div>
                    <h3 className="text-sm font-bold text-boxel-ink line-clamp-1">{info.name}</h3>
                    <p className="text-xs font-normal text-boxel-muted font-mono tracking-wider truncate">
                        {model.model_name}
                    </p>
                </div>

                {/* Composite Leaderboard Score */}
                <div className="voxel-trough inline-block px-4 py-2">
                    <span className="text-xs font-normal text-boxel-muted uppercase tracking-wider block">
                        Leaderboard Score
                    </span>
                    <span className="text-lg font-bold font-mono text-boxel-ink">
                        {model.composite_score.toFixed(1)}%
                    </span>
                </div>
            </div>

            {/* Metrics Breakdown */}
            <div className="mt-6 space-y-2.5 pt-4 border-t border-boxel-bevel-hi text-xs font-mono">
                <div className="flex justify-between items-center">
                    <span className="text-boxel-muted uppercase tracking-wider text-xs font-normal">
                        Return %
                    </span>
                    <span
                        className={`text-sm font-bold ${model.return_pct >= 0 ? 'text-success' : 'text-danger'}`}
                    >
                        {model.return_pct >= 0 ? '+' : ''}
                        {model.return_pct.toFixed(2)}%
                    </span>
                </div>
                <div className="flex justify-between items-center">
                    <span className="text-boxel-muted uppercase tracking-wider text-xs font-normal">
                        Win Rate
                    </span>
                    <span className="text-boxel-ink text-sm font-bold">
                        {model.win_rate.toFixed(1)}%
                    </span>
                </div>
                <div className="flex justify-between items-center">
                    <span className="text-boxel-muted uppercase tracking-wider text-xs font-normal">
                        Approval
                    </span>
                    <span className="text-boxel-ink text-sm font-bold">
                        {model.verifier_approval_rate !== null &&
                        model.verifier_approval_rate !== undefined
                            ? `${model.verifier_approval_rate.toFixed(1)}%`
                            : '—'}
                    </span>
                </div>
                <div className="flex justify-between items-center">
                    <span className="text-boxel-muted uppercase tracking-wider text-xs font-normal">
                        Consistency
                    </span>
                    <span className="text-boxel-ink text-sm font-bold">
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
        <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,18rem),1fr))] gap-6 items-stretch py-8 animate-slide-up w-full">
            {sortedPodium.map(({ model, place }) => (
                <PodiumCard key={model.model_name} model={model} place={place} />
            ))}
        </div>
    );
}
