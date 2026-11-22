import { describe, expect, it } from 'vitest';
import {
    computeAmbientEntranceAlpha,
    computeCedarFraming,
    computeEntranceProgress,
    computeIslandRevealFrame,
    computeIslandVerticalBounds,
    ENTRANCE_DURATION_S,
} from './garden-scene';
import { CX, CY } from './voxel-world';
import { getCedarWorldAndFaces } from './worlds';

describe('garden-scene (portrait mobile framing and single-island stepped entrance reveal)', () => {
    it('keeps desktop framing at 0.68*H while lowering portrait mobile originY toward 0.82*H', () => {
        const desktop = computeCedarFraming(1440, 800);
        expect(desktop.originX).toBe(720);
        expect(desktop.originY).toBeCloseTo(800 * 0.68, 5);

        const square = computeCedarFraming(800, 800);
        expect(square.originY).toBeCloseTo(800 * 0.68, 5);

        const mobile = computeCedarFraming(390, 780);
        expect(mobile.originX).toBe(195);
        expect(mobile.originY).toBeCloseTo(780 * 0.82, 5);

        const midPortrait = computeCedarFraming(850, 1000);
        expect(midPortrait.originY).toBeGreaterThan(1000 * 0.68);
        expect(midPortrait.originY).toBeLessThan(1000 * 0.82);
    });

    it('keeps Cedar Sanctuary island inside portrait mobile canvas vertical bounds without overlapping open-sky copy', () => {
        const { faces } = getCedarWorldAndFaces();
        const { scale, originX, originY } = computeCedarFraming(390, 780);
        const project = (x: number, y: number, z: number): [number, number] => [
            originX + (x - CX - (y - CY)) * scale * 0.5,
            originY + (x - CX + (y - CY)) * scale * 0.34 - (z - 16) * scale * 0.46,
        ];
        const bounds = computeIslandVerticalBounds(faces.island, project, scale, 780);
        expect(bounds.minY).toBeGreaterThan(420);
        expect(bounds.maxY).toBeLessThanOrEqual(780);
        expect(bounds.maxY).toBeGreaterThan(bounds.minY);
    });

    it('computes a stepped bottom-to-top reveal on animating state and settles immediately when settled', () => {
        const bounds = { minY: 440, maxY: 720 };
        const scale = 4.24;

        expect(computeEntranceProgress({ kind: 'animating', elapsed: 0 })).toBe(0);
        expect(
            computeEntranceProgress({ kind: 'animating', elapsed: ENTRANCE_DURATION_S / 2 }),
        ).toBe(0.5);
        expect(computeEntranceProgress({ kind: 'settled' })).toBe(1);

        const early = computeIslandRevealFrame(
            { kind: 'animating', elapsed: 0.25 },
            bounds,
            scale,
            12,
        );
        expect(early.isSettled).toBe(false);
        expect(early.alpha).toBeGreaterThan(0);
        expect(early.settleOffsetY).toBeGreaterThan(0);
        expect(early.columnTopYs).toHaveLength(12);
        for (const topY of early.columnTopYs) {
            expect(topY).toBeGreaterThanOrEqual(bounds.minY);
            expect(topY).toBeLessThanOrEqual(bounds.maxY);
        }
        expect(computeAmbientEntranceAlpha({ kind: 'animating', elapsed: 0.2 })).toBe(0);

        const settled = computeIslandRevealFrame({ kind: 'settled' }, bounds, scale, 12);
        expect(settled).toEqual({
            isSettled: true,
            alpha: 1,
            settleOffsetY: 0,
            columnTopYs: [],
        });
        expect(computeAmbientEntranceAlpha({ kind: 'settled' })).toBe(1);
    });
});
