import { Link } from '@tanstack/react-router';
import { formatPct, type Proof } from '../lib/proof';

export interface ProofStripProps {
    proof: Proof;
    liveCount: number;
}

function tone(value: number | null): string {
    if (value === null) return 'text-voxel-muted';
    return value >= 0 ? 'text-success' : 'text-danger';
}

/** One winner and one loser, side by side, with the as-of date that makes them checkable. */
export function ProofStrip({ proof, liveCount }: ProofStripProps) {
    if (proof.degraded) {
        return (
            <p className="voxel-trough p-2 text-xs font-normal text-voxel-muted">
                The public board is unavailable right now. Losers are published whenever it is not.
            </p>
        );
    }

    if (!proof.winner) {
        return (
            <p className="voxel-trough p-2 text-xs font-normal text-voxel-muted">
                No settled results yet — the desk fills as bots run. Losers will be listed here too.
            </p>
        );
    }

    return (
        <div className="voxel-trough flex flex-col gap-1 p-2 min-w-0">
            <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1 text-xs">
                <span className="font-mono text-xs font-normal text-voxel-muted uppercase tracking-wide">
                    Public desk
                </span>
                <span className="text-voxel-ink">
                    Best: <span className="font-bold">{proof.winner.label}</span>{' '}
                    <span className={`font-mono ${tone(proof.winner.returnPct)}`}>
                        {formatPct(proof.winner.returnPct)}
                    </span>
                </span>
                {proof.worst ? (
                    <span className="text-voxel-ink">
                        Worst: <span className="font-bold">{proof.worst.label}</span>{' '}
                        <span className={`font-mono ${tone(proof.worst.returnPct)}`}>
                            {formatPct(proof.worst.returnPct)}
                        </span>
                    </span>
                ) : null}
                <span className="font-mono text-voxel-muted">
                    {liveCount} live
                    {proof.trackedCount !== null ? ` · ${proof.trackedCount} tracked` : ''}
                </span>
                <Link to="/live-desk" className="text-accent hover:underline whitespace-nowrap">
                    Full desk →
                </Link>
            </div>
            <p className="font-mono text-xs font-normal text-voxel-muted">
                {proof.windowDays}-day window
                {proof.asOf ? ` · latest point ${proof.asOf}` : ''} · paper cash
            </p>
        </div>
    );
}
