import { Link } from '@tanstack/react-router';
import type { LeaderboardRow } from '../api/portfolio-leaderboard';
import { formatPct } from './format-pct';

export interface TopPortfoliosProps {
    rows: LeaderboardRow[];
    trackedCount: number | null;
    windowDays: number;
    degraded?: boolean;
    starterNames?: string[];
}

function returnClass(value: number): string {
    return value >= 0 ? 'text-success' : 'text-danger';
}

export function TopPortfolios({
    rows,
    trackedCount,
    windowDays,
    degraded = false,
    starterNames = [],
}: TopPortfoliosProps) {
    if (rows.length === 0) {
        return (
            <p className="text-xs font-normal text-voxel-muted">
                {degraded
                    ? 'The portfolio board is unavailable right now — the desk below is unaffected.'
                    : 'The portfolio board fills after the next close.'}
            </p>
        );
    }

    return (
        <div className="flex flex-wrap items-start gap-4 w-full">
            <ul className="flex-1 basis-80 min-w-0 flex flex-col gap-1">
                {rows.map((row, index) => (
                    <li
                        key={row.portfolioId}
                        className="voxel-trough px-3 py-2 flex flex-wrap items-baseline gap-2"
                    >
                        <span className="font-mono text-xs font-normal text-voxel-muted">
                            {index + 1}
                        </span>
                        <span className="flex-1 min-w-0 truncate text-sm font-bold text-voxel-ink">
                            {row.label}
                        </span>
                        <span
                            className={`font-mono text-xs font-normal tabular-nums ${returnClass(row.returnPct)}`}
                        >
                            {formatPct(row.returnPct)}
                        </span>
                    </li>
                ))}
            </ul>

            <div className="flex-1 basis-64 min-w-0 flex flex-col gap-3 voxel-trough p-3">
                <p className="text-xs font-normal text-voxel-muted">
                    {trackedCount === null
                        ? `Portfolios ranked on the ${windowDays}-day board: the return each carried from the window open, its chart, and every loser behind them.`
                        : `${trackedCount} portfolios are on the ${windowDays}-day board: the return each carried from the window open, its chart, and every loser behind them.`}
                </p>
                {starterNames.length > 0 ? (
                    <div className="flex flex-wrap gap-2">
                        {starterNames.map((name) => (
                            <Link
                                key={name}
                                to="/recipes"
                                className="voxel-btn inline-flex items-center px-2 py-1 text-xs font-normal bg-voxel-surface text-voxel-ink hover:bg-voxel-elevated"
                            >
                                {name}
                            </Link>
                        ))}
                    </div>
                ) : null}
                <div className="flex flex-wrap gap-2">
                    <Link
                        to="/portfolios"
                        className="voxel-btn inline-flex items-center px-3 py-1.5 text-xs font-normal bg-voxel-surface text-voxel-ink hover:bg-voxel-elevated"
                    >
                        See all portfolios
                    </Link>
                    <Link
                        to="/recipes"
                        className="voxel-btn inline-flex items-center px-3 py-1.5 text-xs font-normal bg-voxel-surface text-voxel-ink hover:bg-voxel-elevated"
                    >
                        Need inspiration?
                    </Link>
                </div>
            </div>
        </div>
    );
}
