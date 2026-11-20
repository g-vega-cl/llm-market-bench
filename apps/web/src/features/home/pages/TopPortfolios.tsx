import { Link } from '@tanstack/react-router';
import type { EquityPoint, LeaderboardRow } from '../api/portfolio-leaderboard';
import { type ChartBox, chartDomain, polylinePoints, valueToY } from '../lib/chart-geometry';
import { formatPct } from './format-pct';

const SPARK: ChartBox = { width: 144, height: 34, padding: 4 };

export interface TopPortfoliosProps {
    rows: LeaderboardRow[];
    medianReturnPct?: number | null;
    worst?: LeaderboardRow | null;
    spy?: EquityPoint[];
    trackedCount: number | null;
    windowDays: number;
    degraded?: boolean;
}

function returnClass(value: number | null): string {
    if (value === null) return 'text-voxel-muted';
    return value >= 0 ? 'text-success' : 'text-danger';
}

/**
 * One lane per portfolio. Five lines in one frame cross inside a few pixels and
 * become unreadable, so each series gets its own row and they share one y-scale.
 */
function Spark({
    series,
    domain,
    label,
    lineClass,
}: {
    series: EquityPoint[];
    domain: ReturnType<typeof chartDomain>;
    label: string;
    lineClass: string;
}) {
    const points = polylinePoints(series, SPARK, domain);
    const zeroY = valueToY(0, SPARK, domain);

    return (
        <svg
            width={SPARK.width}
            height={SPARK.height}
            viewBox={`0 0 ${SPARK.width} ${SPARK.height}`}
            className="shrink-0"
            role="img"
        >
            <title>{label}</title>
            <line
                x1={SPARK.padding}
                x2={SPARK.width - SPARK.padding}
                y1={zeroY}
                y2={zeroY}
                className="stroke-voxel-bevel-hi"
                strokeWidth={1}
                strokeDasharray="3 4"
                opacity={0.8}
            />
            {points ? (
                <polyline
                    points={points}
                    fill="none"
                    className={lineClass}
                    strokeWidth={2}
                    strokeLinejoin="round"
                    strokeLinecap="round"
                />
            ) : null}
        </svg>
    );
}

/** A leaderboard row, or the benchmark row, which has no portfolio receipt. */
type RowData = {
    label: string;
    returnPct: number | null;
    observations: number;
    series: EquityPoint[];
    receiptPortfolioId?: string;
};

function RowContent({
    rank,
    row,
    domain,
    lineClass,
    suffix,
}: {
    rank: string;
    row: RowData;
    domain: ReturnType<typeof chartDomain>;
    lineClass: string;
    suffix?: string;
}) {
    return (
        <>
            <span className="font-mono text-xs font-normal text-voxel-muted tabular-nums w-6 shrink-0">
                {rank}
            </span>
            <span className="flex-1 min-w-0 truncate text-sm font-bold text-voxel-ink">
                {suffix ? `${row.label} ${suffix}` : row.label}
            </span>
            <Spark
                series={row.series}
                domain={domain}
                label={`${row.label}, ${row.series.length} sessions`}
                lineClass={lineClass}
            />
            <span
                className={`font-mono text-xs font-normal tabular-nums shrink-0 ${returnClass(row.returnPct)}`}
            >
                {formatPct(row.returnPct)}
            </span>
        </>
    );
}

function Row({
    rank,
    row,
    domain,
    lineClass,
    suffix,
}: {
    rank: string;
    row: RowData;
    domain: ReturnType<typeof chartDomain>;
    lineClass: string;
    suffix?: string;
}) {
    const sharedClass = 'voxel-trough px-3 py-2 flex items-center gap-3 min-w-0';

    if (row.receiptPortfolioId) {
        return (
            <li>
                <Link
                    to="/portfolios/$portfolioId"
                    params={{ portfolioId: row.receiptPortfolioId }}
                    className={`${sharedClass} w-full hover:bg-voxel-elevated transition-colors`}
                >
                    <RowContent
                        rank={rank}
                        row={row}
                        domain={domain}
                        lineClass={lineClass}
                        suffix={suffix}
                    />
                </Link>
            </li>
        );
    }

    return (
        <li className={sharedClass}>
            <RowContent
                rank={rank}
                row={row}
                domain={domain}
                lineClass={lineClass}
                suffix={suffix}
            />
        </li>
    );
}

/** Decorative cue that both calls to action lead somewhere. */
function ArrowIcon() {
    return (
        <svg
            className="w-4 h-4 shrink-0"
            aria-hidden="true"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
        >
            <path d="M5 12h14" />
            <path d="M13 6l6 6-6 6" />
        </svg>
    );
}

function toReceiptRow(row: LeaderboardRow): RowData {
    const id = row.portfolioId.trim();
    return {
        label: row.label,
        returnPct: row.returnPct,
        observations: row.observations,
        series: row.series,
        receiptPortfolioId: id || undefined,
    };
}

export function TopPortfolios({
    rows,
    medianReturnPct = null,
    worst = null,
    spy = [],
    trackedCount,
    windowDays,
    degraded = false,
}: TopPortfoliosProps) {
    if (degraded) {
        return (
            <p className="text-xs font-normal text-voxel-muted">
                The portfolio board is unavailable right now — the desk below is unaffected.
            </p>
        );
    }

    if (rows.length === 0) {
        return (
            <p className="text-xs font-normal text-voxel-muted">
                The portfolio board fills after the next close.
            </p>
        );
    }

    // One scale for every sparkline, so a taller wiggle means a bigger return.
    const seriesList = [...rows, ...(worst ? [worst] : [])].map((row) => row.series);
    if (spy.length > 0) seriesList.push(spy);
    const domain = chartDomain(seriesList);
    const lastSpy = spy.length > 0 ? spy[spy.length - 1].value : null;
    const spyRow: RowData = {
        label: 'SPY',
        returnPct: lastSpy,
        observations: spy.length,
        series: spy,
    };

    return (
        <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,22rem),1fr))] gap-4 items-start">
            <figure className="flex flex-col gap-1 min-w-0">
                <ul className="flex flex-col gap-1">
                    {rows.map((row, index) => (
                        <Row
                            key={row.portfolioId || `${row.label}-${index}`}
                            rank={String(index + 1)}
                            row={toReceiptRow(row)}
                            domain={domain}
                            lineClass="stroke-accent"
                        />
                    ))}
                </ul>

                {worst ? (
                    <div className="flex flex-col gap-1 mt-2 pt-2 border-t-2 border-voxel-bevel-hi">
                        <span className="text-xs font-normal text-voxel-muted">
                            {trackedCount === null
                                ? 'Lowest on the board'
                                : `Lowest of ${trackedCount}`}
                        </span>
                        <ul className="flex flex-col gap-1">
                            <Row
                                rank={trackedCount === null ? '—' : String(trackedCount)}
                                row={toReceiptRow(worst)}
                                domain={domain}
                                lineClass="stroke-danger"
                            />
                        </ul>
                    </div>
                ) : null}

                {spy.length > 0 ? (
                    <ul className="flex flex-col gap-1 mt-1">
                        <Row
                            rank="—"
                            row={spyRow}
                            domain={domain}
                            lineClass="stroke-voxel-muted"
                            suffix="(benchmark)"
                        />
                    </ul>
                ) : null}

                <figcaption className="text-xs font-normal text-voxel-muted">
                    {windowDays} days from each portfolio's window open · one shared scale · the
                    dashed line is zero. Click any portfolio row to inspect its trades.
                </figcaption>
            </figure>

            <div className="flex flex-col gap-4 voxel-trough p-3 min-w-0">
                <p className="text-xs font-normal text-voxel-muted">
                    {trackedCount === null
                        ? `Portfolios ranked on the ${windowDays}-day board`
                        : `${trackedCount} portfolios on the ${windowDays}-day board`}
                    {medianReturnPct === null ? '' : ` · median ${formatPct(medianReturnPct)}`}
                    {
                        ': winners, the worst loser, and SPY on one scale. Click any portfolio to inspect its positions, fills, and LLM reasoning.'
                    }
                </p>
                <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,14rem),1fr))] gap-2">
                    <Link
                        to="/portfolios"
                        className="voxel-btn inline-flex items-center justify-center gap-2 w-full px-4 py-2 text-sm font-bold uppercase tracking-wider bg-accent text-voxel-trough hover:bg-accent-hover"
                    >
                        See all portfolios
                        <ArrowIcon />
                    </Link>
                    <Link
                        to="/reasoning"
                        className="voxel-btn inline-flex items-center justify-center gap-2 w-full px-4 py-2 text-sm font-bold uppercase tracking-wider border-2 border-accent text-accent bg-voxel-surface hover:bg-accent/10"
                    >
                        Read reasoning logs
                        <ArrowIcon />
                    </Link>
                </div>
            </div>
        </div>
    );
}
