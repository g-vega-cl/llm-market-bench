import { describe, expect, it } from 'vitest';
import {
    CLOUD_CLEAR_CORRIDOR,
    CLOUD_DRIFT_SPEED,
    type CloudLane,
    cloudAlphaAt,
    cloudDriftAt,
    computeCloudLane,
} from './garden-renderer';

const STAGE_W = 1600;
const STAGE_H = 913;
const WIDE = 340; // measured near-plane cloud width in CSS px
const NARROW = 200;
const SPRITE_H = 150;

const corridorLeft = STAGE_W * CLOUD_CLEAR_CORRIDOR.minX;
const corridorRight = STAGE_W * CLOUD_CLEAR_CORRIDOR.maxX;

const near = CLOUD_DRIFT_SPEED.near;

describe('cloud drift and copy-column visibility', () => {
    it('gives a cloud that shares the copy rows its own flank, facing the copy', () => {
        const left = computeCloudLane(126, 160, WIDE, SPRITE_H, STAGE_W, STAGE_H);
        const right = computeCloudLane(1200, 160, WIDE, SPRITE_H, STAGE_W, STAGE_H);

        expect(left.fadeAt).toBe('end');
        expect(left.max + WIDE).toBeLessThan(corridorLeft);
        expect(right.fadeAt).toBe('start');
        expect(right.min).toBeGreaterThan(corridorRight);

        // A cloud clear of the copy rows keeps the whole stage.
        expect(computeCloudLane(200, 700, NARROW, SPRITE_H, STAGE_W, STAGE_H)).toEqual({
            min: -NARROW,
            max: STAGE_W,
            fadeAt: null,
        });
    });

    it('leaves the approved flank positions fully opaque on frame one', () => {
        const leftLane = computeCloudLane(126, 160, WIDE, SPRITE_H, STAGE_W, STAGE_H);
        const rightLane = computeCloudLane(1200, 160, WIDE, SPRITE_H, STAGE_W, STAGE_H);
        expect(cloudAlphaAt({ width: WIDE }, leftLane, 126)).toBe(1);
        expect(cloudAlphaAt({ width: WIDE }, rightLane, 1200)).toBe(1);
    });

    it('never shows a flank cloud over the copy column at any point in its cycle', () => {
        const lanes = [
            computeCloudLane(126, 160, WIDE, SPRITE_H, STAGE_W, STAGE_H),
            computeCloudLane(1200, 160, WIDE, SPRITE_H, STAGE_W, STAGE_H),
        ];
        for (const lane of lanes) {
            const span = lane.max - lane.min;
            for (let i = 0; i <= 200; i++) {
                const x = lane.min + (i / 200) * span;
                if (cloudAlphaAt({ width: WIDE }, lane, x) <= 0.01) continue;
                const overlaps = x + WIDE > corridorLeft && x < corridorRight;
                expect(overlaps).toBe(false);
            }
        }
    });

    it('drops to zero exactly at the copy-facing end so the wrap never pops', () => {
        const left = computeCloudLane(126, 160, WIDE, SPRITE_H, STAGE_W, STAGE_H);
        expect(cloudAlphaAt({ width: WIDE }, left, left.max)).toBe(0);
        expect(cloudAlphaAt({ width: WIDE }, left, left.max - 400)).toBe(1);

        const right = computeCloudLane(1200, 160, WIDE, SPRITE_H, STAGE_W, STAGE_H);
        expect(cloudAlphaAt({ width: WIDE }, right, right.min)).toBe(0);
    });

    it('moves flank clouds outward, away from the copy', () => {
        const left = computeCloudLane(126, 160, WIDE, SPRITE_H, STAGE_W, STAGE_H);
        const span = left.max - left.min;
        const phase = 126 - left.min;
        expect(cloudDriftAt(left, -near, phase, 10).x).toBeLessThan(126);
        expect(cloudDriftAt(left, -near, phase, 0).x).toBeCloseTo(126, 5);

        const right = computeCloudLane(1200, 160, WIDE, SPRITE_H, STAGE_W, STAGE_H);
        const rPhase = 1200 - right.min;
        expect(cloudDriftAt(right, near, rPhase, 10).x).toBeGreaterThan(1200);
        expect(cloudDriftAt(right, near, rPhase, 0).x).toBeCloseTo(1200, 5);
        expect(span).toBeGreaterThan(0);
    });

    it('wraps without gaps and keeps near clouds faster than far ones', () => {
        const lane: CloudLane = { min: -NARROW, max: STAGE_W, fadeAt: null };
        const span = lane.max - lane.min;
        const start = cloudDriftAt(lane, near, 0, 0).x;
        expect(cloudDriftAt(lane, near, 0, 1).x - start).toBeCloseTo(near, 5);
        expect(cloudDriftAt(lane, near, 0, span / near).x).toBeCloseTo(start, 4);
        expect(CLOUD_DRIFT_SPEED.near).toBeGreaterThan(CLOUD_DRIFT_SPEED.far);
    });

    it('never dims clouds that sit below the copy band, as on every portrait viewport', () => {
        const lane = computeCloudLane(60, 567, 200, 120, 390, 844);
        expect(lane.fadeAt).toBeNull();
        for (const x of [-200, 0, 100, 300, 390]) {
            expect(cloudAlphaAt({ width: 200 }, lane, x)).toBe(1);
        }
    });
});
