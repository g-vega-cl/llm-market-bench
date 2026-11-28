import { Badge, Button } from '@llm-market-bench/ui-design-system';
import { Link } from '@tanstack/react-router';
import { useCallback, useEffect, useState } from 'react';
import { fetchGuestJobFn, startGuestBacktestFn } from '../api/recipes-api';

type Phase =
    | { kind: 'idle' }
    | { kind: 'starting' }
    | { kind: 'queued'; jobId: string }
    | { kind: 'running'; jobId: string; pct: number }
    | { kind: 'done'; jobId: string }
    | { kind: 'failed'; message: string };

const POLL_MS = 5000;

async function pollOnce(jobId: string): Promise<Phase> {
    const job = await fetchGuestJobFn({ data: { jobId } });
    if (!job) return { kind: 'running', jobId, pct: 0 };
    if (job.status === 'completed') return { kind: 'done', jobId };
    if (job.status === 'failed' || job.status === 'cancelled') {
        return {
            kind: 'failed',
            message: job.error_message ?? 'The run did not finish. The token was refunded.',
        };
    }
    return { kind: 'running', jobId, pct: job.progress_pct ?? 0 };
}

/**
 * Lets a logged-out visitor spend one of their five guest tokens on this
 * template. The guest has no account to poll from, so the job id is the only
 * handle: statuses are read through a server function that returns progress and
 * nothing else.
 */
export function GuestRunPanel({
    recipeId,
    pollMs = POLL_MS,
}: {
    recipeId: string;
    pollMs?: number;
}) {
    const [phase, setPhase] = useState<Phase>({ kind: 'idle' });

    const start = useCallback(async () => {
        setPhase({ kind: 'starting' });
        try {
            const job = await startGuestBacktestFn({ data: { recipeId } });
            setPhase({ kind: 'queued', jobId: job.id });
        } catch (error) {
            setPhase({
                kind: 'failed',
                message:
                    error instanceof Error
                        ? error.message
                        : 'That run could not be started. Try again.',
            });
        }
    }, [recipeId]);

    useEffect(() => {
        if (phase.kind !== 'queued' && phase.kind !== 'running') return;

        const jobId = phase.jobId;
        let cancelled = false;
        const timer = setTimeout(async () => {
            try {
                const next = await pollOnce(jobId);
                if (!cancelled) setPhase(next);
            } catch {
                if (!cancelled) setPhase({ kind: 'running', jobId, pct: 0 });
            }
        }, pollMs);

        return () => {
            cancelled = true;
            clearTimeout(timer);
        };
    }, [phase, pollMs]);

    return (
        <div
            data-testid="guest-run-panel"
            className="voxel-trough bg-voxel-trough flex flex-wrap items-center justify-between gap-3 p-3"
        >
            <div className="flex flex-col gap-1 min-w-0">
                <span className="flex items-center gap-2 text-xs font-bold text-voxel-ink">
                    <Badge variant="soft" colorScheme="accent" size="xs">
                        5 FREE TOKENS
                    </Badge>
                    Run this one yourself
                </span>
                <span className="text-xs font-normal text-voxel-muted" role="status">
                    {phase.kind === 'idle' && 'One token buys one backtest. No account needed.'}
                    {phase.kind === 'starting' && 'Spending one token and queueing the run…'}
                    {phase.kind === 'queued' && 'Queued. Waiting for a worker…'}
                    {phase.kind === 'running' && `Running: ${phase.pct}%`}
                    {phase.kind === 'done' &&
                        'Finished. Sign in to keep this bot and see every trace.'}
                    {phase.kind === 'failed' && phase.message}
                </span>
            </div>

            <div className="flex flex-wrap items-center gap-2">
                {phase.kind === 'done' ? (
                    <Link
                        to="/recipes/$recipeId"
                        params={{ recipeId }}
                        className="voxel-btn inline-flex items-center border-2 border-accent px-3 py-1.5 text-xs font-bold text-accent"
                    >
                        Open the result →
                    </Link>
                ) : (
                    <Button
                        size="sm"
                        variant="solid"
                        onClick={start}
                        disabled={
                            phase.kind === 'starting' ||
                            phase.kind === 'queued' ||
                            phase.kind === 'running'
                        }
                    >
                        {phase.kind === 'starting' ? 'Starting…' : 'Run this one (1 token)'}
                    </Button>
                )}
                <Link
                    to="/signup"
                    className="text-xs font-normal text-voxel-muted underline decoration-voxel-bevel-hi underline-offset-4 hover:text-accent"
                >
                    Or sign in for 15 a week
                </Link>
            </div>
        </div>
    );
}
