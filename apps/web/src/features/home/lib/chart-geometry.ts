export interface ChartPoint {
    date: string;
    value: number;
}

export interface ChartBox {
    width: number;
    height: number;
    padding: number;
}

export interface ChartDomain {
    min: number;
    max: number;
    start: number;
    end: number;
}

const PAD_RATIO = 0.15;

/** Shared y/x domain across every series so lines are comparable. */
export function chartDomain(seriesList: ChartPoint[][]): ChartDomain {
    const values: number[] = [];
    const times: number[] = [];
    for (const series of seriesList) {
        for (const point of series) {
            if (!Number.isFinite(point.value)) continue;
            values.push(point.value);
            const time = Date.parse(point.date);
            if (Number.isFinite(time)) times.push(time);
        }
    }

    if (values.length === 0 || times.length === 0) {
        return { min: -1, max: 1, start: 0, end: 1 };
    }

    // Always include zero so gains and losses read against the same baseline.
    const rawMin = Math.min(...values, 0);
    const rawMax = Math.max(...values, 0);
    const span = rawMax - rawMin || 1;
    const pad = span * PAD_RATIO;

    return {
        min: rawMin - pad,
        max: rawMax + pad,
        start: Math.min(...times),
        end: Math.max(...times),
    };
}

/** Maps a series to an SVG `points` attribute inside the box. */
export function polylinePoints(points: ChartPoint[], box: ChartBox, domain: ChartDomain): string {
    const innerWidth = box.width - box.padding * 2;
    const innerHeight = box.height - box.padding * 2;
    const xSpan = domain.end - domain.start || 1;
    const ySpan = domain.max - domain.min || 1;

    return points
        .filter((point) => Number.isFinite(point.value) && Number.isFinite(Date.parse(point.date)))
        .map((point) => {
            const x = box.padding + ((Date.parse(point.date) - domain.start) / xSpan) * innerWidth;
            const y = box.padding + (1 - (point.value - domain.min) / ySpan) * innerHeight;
            return `${x.toFixed(1)},${y.toFixed(1)}`;
        })
        .join(' ');
}

/** Y coordinate of a value, used for the zero baseline. */
export function valueToY(value: number, box: ChartBox, domain: ChartDomain): number {
    const innerHeight = box.height - box.padding * 2;
    const ySpan = domain.max - domain.min || 1;
    return box.padding + (1 - (value - domain.min) / ySpan) * innerHeight;
}
