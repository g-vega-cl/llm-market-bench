import { Badge, Card, SectionHeading } from '@llm-market-bench/ui-design-system';
import { formatEasternDateTime } from '~/utils/date';
import type { LiveRunResult, RecipeJobRecord } from '../types';
import { RunPaginator } from './RunPaginator';
import { TraceInspectorBlock } from './TraceInspectorBlock';

/**
 * Eastern-time stamp that names a run. Always `created_at` — the enqueue time is
 * the only stamp a run has before it produces a result, so naming a page from it
 * keeps one clock instead of switching to `as_of_utc` once a trace lands (and
 * `slot_label` is a raw `%Y-%m-%d %H:%M ET` slice, never rendered).
 */
function runStampLabel(job: RecipeJobRecord | undefined): string {
    const stamp = formatEasternDateTime(job?.created_at);
    if (stamp && stamp !== 'Unknown') return stamp;
    return job?.id.slice(0, 8) ?? 'Unknown';
}

function extractLiveResult(job: RecipeJobRecord | undefined): LiveRunResult | null {
    if (!job?.result_json) return null;
    if ('mode' in job.result_json && job.result_json.mode === 'live_turn') {
        return job.result_json as LiveRunResult;
    }
    return null;
}

/** Statuses that will never produce a trace, so the copy must not say "yet". */
const TERMINAL_JOB_STATUSES: ReadonlySet<RecipeJobRecord['status']> = new Set([
    'failed',
    'cancelled',
    'completed',
]);

const JOB_STATUS_LABELS: Record<RecipeJobRecord['status'], string> = {
    pending: 'queued',
    processing: 'running',
    completed: 'completed',
    failed: 'failed',
    cancelled: 'cancelled',
};

function describeMissingTrace(job: RecipeJobRecord): { text: string; error: string | null } {
    const terminal = TERMINAL_JOB_STATUSES.has(job.status);
    const label = JOB_STATUS_LABELS[job.status];
    return {
        text: terminal ? `${label} — no trace output` : `${label} — no trace output yet`,
        error: terminal ? job.error_message : null,
    };
}

function TraceStages({ run }: { run: LiveRunResult }) {
    const signalSummary =
        run.signals.length > 0
            ? run.signals.map((s) => `${s.action} ${s.ticker}`).join(', ')
            : 'HOLD';

    return (
        <div className="flex flex-col gap-4 min-w-0">
            {run.stages.map((st) => (
                <div
                    key={st.stage_id}
                    className="voxel-trough bg-voxel-trough p-4 flex flex-col gap-3 min-w-0"
                >
                    <div className="flex flex-wrap items-center justify-between gap-2 border-b border-voxel-bevel-lo pb-2">
                        <span className="text-sm font-bold text-voxel-ink">LLM Call</span>
                        <span className="text-xs font-normal font-mono text-voxel-muted">
                            {signalSummary}
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
    );
}

interface LiveRunTracesCardProps {
    /** Persisted live runs, newest first (the loader's order). */
    runs: RecipeJobRecord[];
    pageIndex: number;
    onOlder: () => void;
    onNewer: () => void;
}

/**
 * One run per page. Pending, failed and cancelled jobs are pages too: a job with
 * no `result_json` renders the same trough area with its state, so every page
 * names the run it is showing.
 */
export function LiveRunTracesCard({ runs, pageIndex, onOlder, onNewer }: LiveRunTracesCardProps) {
    if (runs.length === 0) return null;

    const safeIndex = Math.min(Math.max(pageIndex, 0), runs.length - 1);
    const activeJob = runs[safeIndex];
    const activeRun = extractLiveResult(activeJob);
    const activeStamp = runStampLabel(activeJob);
    const missingTrace = activeJob && !activeRun ? describeMissingTrace(activeJob) : null;

    return (
        <Card padding="md" className="flex flex-col gap-4 min-w-0">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b-2 border-voxel-bevel-hi pb-3">
                <div className="flex flex-col gap-1 min-w-0">
                    <SectionHeading>Live Run Traces</SectionHeading>
                    <span className="text-xs font-normal text-voxel-muted">
                        Runs independently on clvg.uk auto-go against your isolated $10,000 live
                        paper ledger (every 30m during market hours 09:30–16:00 ET, or every 5m
                        while Turbo is active). The latest 10 runs are kept here, newest first.
                    </span>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                    <Badge variant="soft" size="xs">
                        {activeStamp}
                    </Badge>
                    {activeRun && (
                        <Badge variant="soft" colorScheme="accent" size="xs">
                            {activeRun.signals.length} Signals
                        </Badge>
                    )}
                </div>
            </div>

            <RunPaginator
                index={safeIndex}
                total={runs.length}
                label={activeStamp}
                onOlder={onOlder}
                onNewer={onNewer}
            />

            {activeRun ? (
                <TraceStages run={activeRun} />
            ) : missingTrace ? (
                <div className="voxel-trough bg-voxel-trough p-4 flex flex-col gap-2 min-w-0">
                    <span className="text-xs font-normal text-voxel-muted">
                        {missingTrace.text}
                    </span>
                    {missingTrace.error && (
                        <span className="min-w-0 break-words text-xs font-normal text-danger">
                            {missingTrace.error}
                        </span>
                    )}
                </div>
            ) : null}
        </Card>
    );
}
