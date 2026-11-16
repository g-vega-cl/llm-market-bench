import { Badge, Button, Card, SectionHeading } from '@llm-market-bench/ui-design-system';
import { useEffect, useState } from 'react';
import type { LivePortfolioSnapshot, LiveRunResult, RecipeJobRecord } from '../types';
import { RecipePortfolioBlock } from './RecipePortfolioBlock';
import { TraceInspectorBlock } from './TraceInspectorBlock';

interface LiveRunsBlockProps {
    portfolio: LivePortfolioSnapshot | null;
    recentLiveRuns: RecipeJobRecord[];
    latestInlineRun: LiveRunResult | null;
}

const INLINE_LATEST_ID = 'inline-latest';

function extractLiveResult(job: RecipeJobRecord | undefined): LiveRunResult | null {
    if (!job?.result_json) return null;
    if ('mode' in job.result_json && job.result_json.mode === 'live_turn') {
        return job.result_json as LiveRunResult;
    }
    return null;
}

interface RunSelectorBarProps {
    recentLiveRuns: RecipeJobRecord[];
    hasLatestInline: boolean;
    isViewingInline: boolean;
    activeJobId: string | undefined;
    onSelect: (id: string) => void;
}

function RunSelectorBar({
    recentLiveRuns,
    hasLatestInline,
    isViewingInline,
    activeJobId,
    onSelect,
}: RunSelectorBarProps) {
    if (!hasLatestInline && recentLiveRuns.length === 0) return null;
    return (
        <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-normal text-boxel-muted">Recent Live Turns:</span>
            {hasLatestInline && (
                <Button
                    size="sm"
                    variant={isViewingInline ? 'solid' : 'outline'}
                    onClick={() => onSelect(INLINE_LATEST_ID)}
                >
                    Latest Turn
                </Button>
            )}
            {recentLiveRuns.map((run) => {
                const isSelected = !isViewingInline && activeJobId === run.id;
                const stamp = (run.created_at || '').slice(0, 16).replace('T', ' ');
                return (
                    <Button
                        key={run.id}
                        size="sm"
                        variant={isSelected ? 'solid' : 'outline'}
                        onClick={() => onSelect(run.id)}
                    >
                        {stamp || run.id.slice(0, 8)}
                    </Button>
                );
            })}
        </div>
    );
}

export function LiveRunsBlock({ portfolio, recentLiveRuns, latestInlineRun }: LiveRunsBlockProps) {
    const [selectedRunId, setSelectedRunId] = useState<string | null>(() =>
        latestInlineRun ? INLINE_LATEST_ID : (recentLiveRuns[0]?.id ?? null),
    );

    useEffect(() => {
        if (latestInlineRun) {
            setSelectedRunId(INLINE_LATEST_ID);
        }
    }, [latestInlineRun]);

    const activeSelection =
        selectedRunId ?? (latestInlineRun ? INLINE_LATEST_ID : (recentLiveRuns[0]?.id ?? null));
    const activeJob = recentLiveRuns.find((run) => run.id === activeSelection) ?? recentLiveRuns[0];
    const isViewingInline = activeSelection === INLINE_LATEST_ID && latestInlineRun !== null;
    const activeRun = isViewingInline ? latestInlineRun : extractLiveResult(activeJob);

    const hasPortfolio = portfolio !== null;
    const hasRuns = recentLiveRuns.length > 0 || latestInlineRun !== null;
    if (!hasPortfolio && !hasRuns) {
        return null;
    }

    return (
        <div className="flex flex-col gap-6 min-w-0">
            {portfolio && (
                <RecipePortfolioBlock
                    title="Live Paper Portfolio"
                    cash={portfolio.cash}
                    totalEquity={portfolio.total_equity}
                    openPositions={portfolio.open_positions}
                />
            )}

            {hasRuns && (
                <Card padding="md" className="flex flex-col gap-4 min-w-0">
                    <div className="flex flex-wrap items-center justify-between gap-2 border-b-2 border-boxel-bevel-hi pb-3">
                        <SectionHeading gradient="catalyst">Live Run Traces</SectionHeading>
                        {activeRun && (
                            <div className="flex flex-wrap items-center gap-2">
                                <Badge variant="outline" size="xs">
                                    {activeRun.slot_label || activeRun.as_of_utc.slice(0, 16)}
                                </Badge>
                                <Badge variant="soft" colorScheme="accent" size="xs">
                                    {activeRun.signals.length} Signals
                                </Badge>
                            </div>
                        )}
                    </div>

                    <RunSelectorBar
                        recentLiveRuns={recentLiveRuns}
                        hasLatestInline={latestInlineRun !== null}
                        isViewingInline={isViewingInline}
                        activeJobId={activeJob?.id}
                        onSelect={setSelectedRunId}
                    />

                    {activeRun ? (
                        <div className="flex flex-col gap-4 min-w-0">
                            {activeRun.stages.map((st) => (
                                <div
                                    key={st.stage_id}
                                    className="voxel-trough bg-boxel-trough p-4 flex flex-col gap-3 min-w-0"
                                >
                                    <div className="flex flex-wrap items-center justify-between gap-2 border-b border-boxel-bevel-lo pb-2">
                                        <span className="text-sm font-bold text-boxel-ink">
                                            {st.title}
                                        </span>
                                        <span className="text-xs font-normal font-mono text-boxel-muted">
                                            {activeRun.signals.length > 0
                                                ? activeRun.signals
                                                      .map((s) => `${s.action} ${s.ticker}`)
                                                      .join(', ')
                                                : 'HOLD'}
                                        </span>
                                    </div>
                                    <TraceInspectorBlock
                                        prompt={st.prompt}
                                        trace={st.trace}
                                        toolCalls={st.tool_calls}
                                        fullOutput={st.output}
                                    />
                                </div>
                            ))}
                        </div>
                    ) : (
                        <div className="voxel-trough bg-boxel-trough p-4">
                            <span className="text-xs font-normal text-boxel-muted">
                                Selected live job has no trace output yet (status:{' '}
                                {activeJob?.status ?? 'pending'}).
                            </span>
                        </div>
                    )}
                </Card>
            )}
        </div>
    );
}
