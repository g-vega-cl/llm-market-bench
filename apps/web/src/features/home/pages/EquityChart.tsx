import type { EquityPoint, LeaderboardRow } from '../api/portfolio-leaderboard';
import {
    type ChartBox,
    chartDomain,
    lastPointXY,
    polylinePoints,
    valueToY,
} from '../lib/chart-geometry';

const BOX: ChartBox = { width: 640, height: 160, padding: 12 };

function dateLabel(time: number): string {
    // Session dates are stored as UTC calendar days; formatting in the viewer's
    // zone would shift the axis a day back west of UTC.
    return new Date(time).toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        timeZone: 'UTC',
    });
}

function formatAxis(value: number): string {
    return `${value > 0 ? '+' : ''}${value.toFixed(0)}%`;
}

// Literal pairs: a runtime `stroke-` -> `bg-` swap produces a class Tailwind never
// generates, which leaves the swatch invisible.
const LINE_CLASSES = [
    'stroke-accent',
    'stroke-success',
    'stroke-accent-hover',
    'stroke-danger',
    'stroke-voxel-ink',
];
const SWATCH_CLASSES = ['bg-accent', 'bg-success', 'bg-accent-hover', 'bg-danger', 'bg-voxel-ink'];

export interface EquityChartProps {
    rows: LeaderboardRow[];
    spy: EquityPoint[];
    windowDays?: number;
    spyUnavailable?: boolean;
}

/**
 * Server-rendered equity chart: no chart library, no hover tooltips (design spec
 * §10). Every series is already rebased to percent return by the loader.
 */
export function EquityChart({
    rows,
    spy,
    windowDays = 30,
    spyUnavailable = false,
}: EquityChartProps) {
    const plotted = rows.filter((row) => Array.isArray(row.series) && row.series.length > 1);
    if (plotted.length === 0) {
        return (
            <p className="text-xs font-normal text-voxel-muted">
                Equity curves appear after the first close.
            </p>
        );
    }

    const domain = chartDomain([...plotted.map((row) => row.series), spy]);
    const zeroY = valueToY(0, BOX, domain);
    const label = `Equity curves for the top ${plotted.length} portfolios against SPY over ${windowDays} days`;

    return (
        <figure className="flex flex-col gap-3">
            <svg
                viewBox={`0 0 ${BOX.width} ${BOX.height}`}
                className="w-full h-auto text-voxel-ink"
                role="img"
                aria-label={label}
            >
                <line
                    x1={BOX.padding}
                    x2={BOX.width - BOX.padding}
                    y1={zeroY}
                    y2={zeroY}
                    className="stroke-voxel-bevel-hi"
                    strokeWidth={1}
                    strokeDasharray="4 4"
                />
                {spy.length > 1 ? (
                    <polyline
                        points={polylinePoints(spy, BOX, domain)}
                        fill="none"
                        className="stroke-voxel-muted"
                        strokeWidth={1.5}
                        strokeDasharray="6 4"
                        strokeLinejoin="round"
                    />
                ) : null}
                {plotted.map((row, index) => {
                    const end = lastPointXY(row.series, BOX, domain);
                    return (
                        <g key={row.portfolioId}>
                            <polyline
                                points={polylinePoints(row.series, BOX, domain)}
                                fill="none"
                                className={LINE_CLASSES[index % LINE_CLASSES.length]}
                                strokeWidth={index === 0 ? 2.5 : 1.5}
                                strokeLinejoin="round"
                                strokeLinecap="round"
                            />
                            {end ? (
                                <>
                                    <circle
                                        cx={end.x}
                                        cy={end.y}
                                        r={3}
                                        className={SWATCH_CLASSES[index % SWATCH_CLASSES.length]}
                                    />
                                    {/* Rank label: identity without relying on colour alone. */}
                                    <text
                                        x={Math.min(end.x + 6, BOX.width - 4)}
                                        y={end.y + 3}
                                        fontSize={9}
                                        className="fill-voxel-ink"
                                    >
                                        {index + 1}
                                    </text>
                                </>
                            ) : null}
                        </g>
                    );
                })}
            </svg>
            <figcaption className="flex flex-wrap gap-3">
                {plotted.map((row, index) => (
                    <span
                        key={row.portfolioId}
                        className="flex items-baseline gap-1 text-xs font-normal text-voxel-muted"
                    >
                        <span
                            aria-hidden="true"
                            className={`inline-block w-2 h-2 ${SWATCH_CLASSES[index % SWATCH_CLASSES.length]}`}
                        />
                        <span className="text-voxel-muted">
                            {index + 1}. {row.label}
                        </span>
                    </span>
                ))}
                <span className="text-xs font-normal text-voxel-muted">
                    {spyUnavailable ? 'SPY unavailable · ' : 'SPY dashed · '}
                    {dateLabel(domain.start)} to {dateLabel(domain.end)} · scale{' '}
                    {formatAxis(domain.min)} to {formatAxis(domain.max)}
                </span>
            </figcaption>
        </figure>
    );
}
