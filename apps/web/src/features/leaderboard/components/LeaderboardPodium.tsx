import type { LLMLeaderboardRow } from '@llm-market-bench/database';
import { Badge, Card } from '@llm-market-bench/ui-design-system';
import { Link } from '@tanstack/react-router';
import { formatUpDays, formatWinRate, getLeaderboardDisplayInfo } from '../lib/model-helper';

interface LeaderboardPodiumProps {
    models: LLMLeaderboardRow[];
}

interface PodiumCardProps {
    model: LLMLeaderboardRow;
    place: number;
}

function CompetitorTitle({ model, name }: { model: LLMLeaderboardRow; name: string }) {
    if (model.recipe_id) {
        return (
            <Link
                to="/recipes/$recipeId"
                params={{ recipeId: model.recipe_id }}
                className="text-sm font-bold text-voxel-ink hover:text-accent underline decoration-voxel-bevel-hi underline-offset-4 line-clamp-1"
            >
                {name}
            </Link>
        );
    }
    if (model.portfolio_id) {
        return (
            <Link
                to="/portfolios/$portfolioId"
                params={{ portfolioId: model.portfolio_id }}
                className="text-sm font-bold text-voxel-ink hover:text-accent underline decoration-voxel-bevel-hi underline-offset-4 line-clamp-1"
            >
                {name}
            </Link>
        );
    }
    return <h3 className="text-sm font-bold text-voxel-ink line-clamp-1">{name}</h3>;
}

function PodiumCard({ model, place }: PodiumCardProps) {
    const info = getLeaderboardDisplayInfo(model);
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
            className={`scene-scrim relative flex flex-col justify-between w-full h-full p-6 ${borderClass}`}
        >
            {/* Rank Badge */}
            <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-voxel-bevel-hi">
                <Badge colorScheme={badgeColor} variant="solid" size="sm">
                    Place #{place}
                </Badge>
                <Badge colorScheme={info.badgeColor} variant="soft" size="xs">
                    {info.categoryLabel}
                </Badge>
            </div>

            {/* Identity & Composite Score */}
            <div className="text-center pt-4 flex flex-col gap-3 min-w-0">
                <div className="min-w-0">
                    <CompetitorTitle model={model} name={info.name} />
                    <p className="text-xs font-normal text-voxel-muted font-mono tracking-wider truncate">
                        {info.subtitle}
                    </p>
                </div>

                <div className="voxel-trough inline-block px-4 py-2">
                    <span className="text-xs font-normal text-voxel-muted uppercase tracking-wider block">
                        Leaderboard Score
                    </span>
                    <span className="text-sm font-bold font-mono tabular-nums text-voxel-ink">
                        {model.composite_score.toFixed(1)}%
                    </span>
                </div>
            </div>

            {/* Metrics Breakdown (strictly 3 stats matching Row 3-stat budget) */}
            <div className="mt-auto pt-4 border-t border-voxel-bevel-hi flex flex-col gap-2 text-xs font-mono">
                <div className="flex justify-between items-center gap-2">
                    <span className="text-voxel-muted uppercase tracking-wider text-xs font-normal">
                        Return %
                    </span>
                    <span
                        className={`text-sm font-bold tabular-nums ${model.return_pct >= 0 ? 'text-success' : 'text-danger'}`}
                    >
                        {model.return_pct >= 0 ? '+' : ''}
                        {model.return_pct.toFixed(2)}%
                    </span>
                </div>
                <div className="flex justify-between items-center gap-2">
                    <span className="text-voxel-muted uppercase tracking-wider text-xs font-normal">
                        Win Rate
                    </span>
                    <span className="text-voxel-ink text-sm font-bold tabular-nums">
                        {formatWinRate(model.win_rate)}
                    </span>
                </div>
                <div className="flex justify-between items-center gap-2">
                    <span className="text-voxel-muted uppercase tracking-wider text-xs font-normal">
                        Up Days
                    </span>
                    <span className="text-voxel-ink text-sm font-bold tabular-nums whitespace-nowrap">
                        {formatUpDays(model.up_days, model.active_days, model.consistency_score)}
                    </span>
                </div>
            </div>
        </Card>
    );
}

export function LeaderboardPodium({ models }: LeaderboardPodiumProps) {
    const top3 = models.slice(0, 3);
    if (top3.length === 0) return null;

    // Order as 2nd, 1st, 3rd for athletic podium look
    const sortedPodium = [];
    if (top3[1]) sortedPodium.push({ model: top3[1], place: 2 });
    if (top3[0]) sortedPodium.push({ model: top3[0], place: 1 });
    if (top3[2]) sortedPodium.push({ model: top3[2], place: 3 });

    return (
        <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,18rem),1fr))] gap-6 items-stretch w-full">
            {sortedPodium.map(({ model, place }) => (
                <PodiumCard key={model.model_name} model={model} place={place} />
            ))}
        </div>
    );
}
