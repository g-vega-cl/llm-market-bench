import { Badge, Button, SubHeading } from '@llm-market-bench/ui-design-system';
import { Link } from '@tanstack/react-router';
import { formatEasternDateTime } from '~/utils/date';
import type { PushStrategy, RecipeJobRecord } from '../types';
import { extractBacktestResult } from '../utils/overview-metrics';
import { formatSignedPct } from './PerformanceOverviewBlock';

function promptExcerpt(strategy: PushStrategy): string {
    const prompt = strategy.stages[0]?.blocks.find((b) => b.type === 'prompt');
    if (!prompt || prompt.type !== 'prompt') return 'No prompt instructions configured.';
    const text = prompt.text.replace(/\s+/g, ' ').trim();
    return text.length > 260 ? `${text.slice(0, 257)}…` : text;
}

function backtestStatusColor(
    status: RecipeJobRecord['status'],
): 'success' | 'accent' | 'warning' | 'danger' | 'neutral' {
    if (status === 'completed') return 'success';
    if (status === 'processing') return 'accent';
    if (status === 'pending') return 'warning';
    if (status === 'failed') return 'danger';
    return 'neutral';
}

export function OverviewBottomSection({
    recipeId,
    strategy,
    backtests,
    isOwner,
    onFork,
}: {
    recipeId: string;
    strategy: PushStrategy;
    backtests: RecipeJobRecord[];
    isOwner: boolean;
    onFork: () => void;
}) {
    const stage = strategy.stages[0];
    const blockTypes = Array.from(new Set(stage.blocks.map((b) => b.type)));

    return (
        <div className="flex flex-wrap gap-6 items-start min-w-0 w-full pt-2 border-t border-voxel-bevel-hi">
            <div className="flex-1 basis-72 flex flex-col gap-3 min-w-0">
                <SubHeading>Recent Backtests</SubHeading>
                {backtests.length === 0 ? (
                    <div className="voxel-trough bg-voxel-trough p-4">
                        <span className="text-xs font-normal text-voxel-muted">
                            No 2-week backtests run yet.
                        </span>
                    </div>
                ) : (
                    <div className="flex flex-col gap-2 min-w-0">
                        {backtests.map((job) => {
                            const res = extractBacktestResult(job);
                            const dates = res?.window_dates ?? [];
                            const windowLabel =
                                dates.length > 0
                                    ? `${dates[0]} → ${dates[dates.length - 1]}`
                                    : formatEasternDateTime(job.created_at);
                            const ret = res?.total_return_pct_net;
                            return (
                                <Link
                                    key={job.id}
                                    to="/recipes/backtest/$jobId"
                                    params={{ jobId: job.id }}
                                    className="voxel-trough bg-voxel-trough hover:bg-voxel-elevated p-3 flex flex-wrap items-center justify-between gap-2 min-w-0"
                                >
                                    <div className="flex flex-wrap items-center gap-2 min-w-0">
                                        <Badge
                                            variant="soft"
                                            colorScheme={backtestStatusColor(job.status)}
                                            size="xs"
                                        >
                                            {job.status.toUpperCase()}
                                        </Badge>
                                        <span className="text-xs font-normal font-mono text-voxel-ink truncate min-w-0">
                                            {windowLabel}
                                        </span>
                                    </div>
                                    <span
                                        className={`text-xs font-normal font-mono tabular-nums whitespace-nowrap ${
                                            typeof ret === 'number'
                                                ? ret >= 0
                                                    ? 'text-success'
                                                    : 'text-danger'
                                                : 'text-voxel-muted'
                                        }`}
                                    >
                                        {typeof ret === 'number'
                                            ? formatSignedPct(ret)
                                            : `${job.progress_pct}%`}
                                    </span>
                                </Link>
                            );
                        })}
                    </div>
                )}
            </div>

            <div className="flex-1 basis-80 flex flex-col gap-3 min-w-0">
                <SubHeading
                    rightElement={
                        isOwner ? (
                            <Link
                                to="/recipes/$recipeId/edit"
                                params={{ recipeId }}
                                className="text-xs font-normal text-accent underline underline-offset-4 hover:text-accent-hover whitespace-nowrap"
                            >
                                Edit Blueprint →
                            </Link>
                        ) : (
                            <Button size="sm" variant="outline" onClick={onFork}>
                                Fork &amp; Customize
                            </Button>
                        )
                    }
                >
                    Strategy DNA
                </SubHeading>

                <div className="voxel-trough bg-voxel-trough p-4 flex flex-col gap-3 min-w-0">
                    <div className="flex flex-wrap items-center gap-2 min-w-0">
                        {blockTypes.map((type) => (
                            <Badge key={type} colorScheme="accent" variant="soft" size="xs">
                                {type}
                            </Badge>
                        ))}
                        <Badge colorScheme="neutral" variant="soft" size="xs">
                            {stage.selected_tools.length} tools
                        </Badge>
                    </div>
                    <p className="text-xs font-normal text-voxel-muted break-words leading-relaxed">
                        {promptExcerpt(strategy)}
                    </p>
                </div>
            </div>
        </div>
    );
}
