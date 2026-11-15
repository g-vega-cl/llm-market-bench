import { Badge, Button, Card, ErrorCard, PageLayout } from '@llm-market-bench/ui-design-system';
import { useQuery } from '@tanstack/react-query';
import { Link, useNavigate } from '@tanstack/react-router';
import { useState } from 'react';
import { isQuerySettled } from '~/lib/query-client';
import { enqueueRecipeJobFn, fetchRecipeRunDetailFn } from '../api/recipes-api';
import { BacktestTelemetryBlock } from '../components/BacktestTelemetryBlock';
import { BacktestTimelineBlock } from '../components/BacktestTimelineBlock';
import { BacktestTradesBlock } from '../components/BacktestTradesBlock';
import type {
    BacktestResultData,
    RecipeJobRecord,
    RecipeJobStatus,
    RecipeRunDetail,
} from '../types';

interface RecipeBacktestPageProps {
    jobId: string;
    initialData: RecipeRunDetail | null;
}

function resolveStatusBadge(
    status: RecipeJobStatus,
    daysCompleted: number,
    totalDays: number,
): {
    label: string;
    colorScheme: 'warning' | 'accent' | 'success' | 'danger';
} {
    if (status === 'pending') return { label: 'QUEUED', colorScheme: 'warning' };
    if (status === 'processing') {
        const label =
            totalDays > 0
                ? `SLOT ${Math.min(daysCompleted + 1, totalDays)} / ${totalDays}`
                : 'PROCESSING';
        return { label, colorScheme: 'accent' };
    }
    if (status === 'completed') return { label: 'COMPLETED', colorScheme: 'success' };
    return { label: 'FAILED', colorScheme: 'danger' };
}

function extractBacktestResults(job: RecipeJobRecord): BacktestResultData | null {
    if (!job.result_json) return null;
    if ('mode' in job.result_json && job.result_json.mode === 'live_turn') return null;
    return job.result_json as BacktestResultData;
}

function BacktestHeader({
    detail,
    results,
    canRerun,
    isRerunning,
    onRerun,
}: {
    detail: RecipeRunDetail;
    results: BacktestResultData | null;
    canRerun: boolean;
    isRerunning: boolean;
    onRerun: () => void;
}) {
    const { job, recipeName } = detail;
    const windowDates = results?.window_dates ?? [];
    const daysCompleted = results?.days_completed ?? results?.day_steps?.length ?? 0;
    const totalDays = results?.total_days ?? windowDates.length;
    const progressPct =
        job.status === 'completed' ? 100 : Math.max(0, Math.min(100, job.progress_pct ?? 0));
    const statusBadge = resolveStatusBadge(job.status, daysCompleted, totalDays);
    const windowLabel =
        windowDates.length > 0
            ? `${windowDates[0]} -> ${windowDates[windowDates.length - 1]}`
            : 'Selecting 2W window';
    const barColor =
        job.status === 'failed'
            ? 'bg-danger'
            : job.status === 'completed'
              ? 'bg-success'
              : 'bg-accent';

    return (
        <header className="flex flex-col gap-4 border-b-2 border-boxel-bevel-hi pb-4">
            <div className="flex flex-wrap items-center justify-between gap-4">
                <div className="flex flex-wrap items-center gap-4 min-w-0">
                    <Link
                        to="/recipes"
                        search={job.recipe_id ? { recipeId: job.recipe_id } : undefined}
                        className="voxel-btn inline-flex items-center px-3 py-1.5 text-sm font-bold border-2 border-accent text-accent hover:bg-accent/10 rounded-none whitespace-nowrap"
                    >
                        Edit in Studio
                    </Link>
                    <h1 className="text-lg font-bold text-boxel-ink min-w-0 break-words">
                        {recipeName || 'Recipe Backtest Run'}
                    </h1>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                    <Badge variant="solid" size="sm" colorScheme={statusBadge.colorScheme} showDot>
                        {statusBadge.label}
                    </Badge>
                    <span className="text-sm font-bold font-mono tabular-nums text-boxel-ink">
                        {progressPct}%
                    </span>
                    {canRerun && (
                        <Button
                            size="sm"
                            variant="outline"
                            onClick={onRerun}
                            isLoading={isRerunning}
                        >
                            Re-run Backtest
                        </Button>
                    )}
                </div>
            </div>

            <div
                data-testid="backtest-meta-row"
                className="flex flex-wrap items-baseline gap-x-4 gap-y-2 text-xs font-normal text-boxel-muted min-w-0"
            >
                <span className="whitespace-nowrap">Window: {windowLabel}</span>
                <span className="whitespace-nowrap">
                    • Model: {job.model || job.provider || 'auto-strata'}
                </span>
                <span className="min-w-0 break-all">
                    <span className="whitespace-nowrap">• Job:</span>{' '}
                    <span className="font-mono">{job.id}</span>
                </span>
            </div>

            <div className="w-full h-2 voxel-trough bg-boxel-trough overflow-hidden">
                <div
                    className={`h-full transition-all duration-300 ${barColor}`}
                    style={{ width: `${progressPct}%` }}
                />
            </div>
        </header>
    );
}

export function RecipeBacktestPage({ jobId, initialData }: RecipeBacktestPageProps) {
    const navigate = useNavigate();
    const [isRerunning, setIsRerunning] = useState(false);
    const [rerunError, setRerunError] = useState<string | null>(null);
    const [mountedAt] = useState(() => Date.now());

    const query = useQuery({
        queryKey: ['recipe-backtest-run', jobId],
        queryFn: () => fetchRecipeRunDetailFn({ data: { jobId } }),
        initialData: initialData ?? undefined,
        initialDataUpdatedAt: initialData ? mountedAt : undefined,
        staleTime: 1000,
        refetchInterval: (q) => {
            const st = q.state.data?.job.status;
            return st === 'pending' || st === 'processing' ? 1500 : false;
        },
    });

    const detail = query.data;
    if (!detail && (query.isPending || query.isFetching)) {
        return (
            <div className="min-h-screen bg-boxel-canvas text-boxel-ink">
                <PageLayout maxWidth="xl" className="flex flex-col gap-6">
                    <Card padding="md" className="flex flex-col gap-2">
                        <h1 className="text-lg font-bold text-boxel-ink">
                            Loading Backtest Run...
                        </h1>
                        <p className="text-xs font-normal text-boxel-muted">
                            Fetching job {jobId} status and checkpoints from the execution queue.
                        </p>
                    </Card>
                </PageLayout>
            </div>
        );
    }

    if (!detail) {
        return (
            <div className="min-h-screen bg-boxel-canvas text-boxel-ink">
                <PageLayout maxWidth="xl" className="flex flex-col gap-6">
                    <ErrorCard
                        title="Backtest Run Not Found"
                        message="This job could not be loaded or belongs to another session."
                    />
                    <div>
                        <Link
                            to="/recipes"
                            className="voxel-btn inline-flex items-center px-3 py-1.5 text-sm font-bold border-2 border-accent text-accent"
                        >
                            Back to Strategy Studio
                        </Link>
                    </div>
                </PageLayout>
            </div>
        );
    }

    if (detail.job.mode === 'live_turn') {
        return (
            <div className="min-h-screen bg-boxel-canvas text-boxel-ink">
                <PageLayout maxWidth="xl" className="flex flex-col gap-6">
                    <ErrorCard
                        title="Incompatible Job Mode"
                        message="This execution job is a Live Turn run rather than a 2-week backtest."
                    />
                    <div>
                        <Link
                            to="/recipes"
                            search={
                                detail.job.recipe_id
                                    ? { recipeId: detail.job.recipe_id }
                                    : undefined
                            }
                            className="voxel-btn inline-flex items-center px-3 py-1.5 text-sm font-bold border-2 border-accent text-accent"
                        >
                            Back to Strategy Studio
                        </Link>
                    </div>
                </PageLayout>
            </div>
        );
    }

    const { job } = detail;
    const isRunning = job.status === 'pending' || job.status === 'processing';
    const results = extractBacktestResults(job);
    const canRerun = Boolean(job.recipe_id) && !isRunning && isQuerySettled(query);

    const handleRerun = async () => {
        if (!job.recipe_id || isRerunning) return;
        setIsRerunning(true);
        setRerunError(null);
        try {
            const nextJob = (await enqueueRecipeJobFn({
                data: { recipeId: job.recipe_id, mode: 'backtest' },
            })) as { id: string };
            await navigate({
                to: '/recipes/backtest/$jobId',
                params: { jobId: nextJob.id },
            });
        } catch (err) {
            setRerunError(err instanceof Error ? err.message : 'Failed to queue backtest re-run');
        } finally {
            setIsRerunning(false);
        }
    };

    return (
        <div className="min-h-screen bg-boxel-canvas text-boxel-ink">
            <PageLayout maxWidth="xl" className="flex flex-col gap-6">
                <BacktestHeader
                    detail={detail}
                    results={results}
                    canRerun={canRerun}
                    isRerunning={isRerunning}
                    onRerun={handleRerun}
                />

                {(job.status === 'failed' || rerunError) && (
                    <ErrorCard
                        title="Backtest Execution Error"
                        message={rerunError || job.error_message || 'Backtest worker failed.'}
                    />
                )}

                <BacktestTimelineBlock status={job.status} results={results} />
                <BacktestTelemetryBlock results={results} isRunning={isRunning} />
                <BacktestTradesBlock results={results} />
            </PageLayout>
        </div>
    );
}
