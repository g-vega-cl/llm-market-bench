import { describe, expect, it } from 'vitest';
import { chartDomain, polylinePoints, valueToY } from './chart-geometry';

const BOX = { width: 640, height: 240, padding: 10 };

function series(values: number[]) {
    return values.map((value, index) => ({
        date: `2026-11-${String(index + 10).padStart(2, '0')}`,
        value,
    }));
}

describe('chartDomain', () => {
    it('always includes zero so gains and losses share a baseline', () => {
        const domain = chartDomain([series([1, 2, 3])]);

        expect(domain.min).toBeLessThan(0);
        expect(domain.max).toBeGreaterThan(3);
    });

    it('pads a flat series instead of collapsing to a zero-height line', () => {
        const domain = chartDomain([series([0, 0, 0])]);

        expect(domain.max).toBeGreaterThan(domain.min);
    });

    it('spans the shared date range of every series', () => {
        const domain = chartDomain([series([1, 2]), [{ date: '2026-12-01', value: 3 }]]);

        expect(domain.start).toBe(Date.parse('2026-11-10'));
        expect(domain.end).toBe(Date.parse('2026-12-01'));
    });

    it('returns a usable fallback for empty input', () => {
        expect(chartDomain([])).toEqual({ min: -1, max: 1, start: 0, end: 1 });
    });
});

describe('polylinePoints', () => {
    it('emits one coordinate pair per finite point inside the box', () => {
        const points = series([0, 1, 2]);
        const box = { ...BOX };
        const out = polylinePoints(points, box, chartDomain([points])).split(' ');

        expect(out).toHaveLength(3);
        for (const pair of out) {
            const [x, y] = pair.split(',').map(Number);
            expect(x).toBeGreaterThanOrEqual(box.padding - 0.1);
            expect(x).toBeLessThanOrEqual(box.width - box.padding + 0.1);
            expect(y).toBeGreaterThanOrEqual(box.padding - 0.1);
            expect(y).toBeLessThanOrEqual(box.height - box.padding + 0.1);
        }
    });

    it('drops points with an unparseable date', () => {
        const points = [...series([0, 1]), { date: 'not-a-date', value: 2 }];

        expect(polylinePoints(points, BOX, chartDomain([points])).split(' ')).toHaveLength(2);
    });
});

describe('valueToY', () => {
    it('places higher values nearer the top of the box', () => {
        const domain = chartDomain([series([-5, 5])]);

        expect(valueToY(5, BOX, domain)).toBeLessThan(valueToY(-5, BOX, domain));
    });
});
