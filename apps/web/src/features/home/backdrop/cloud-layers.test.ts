import { describe, expect, it } from 'vitest';
import { computeTileOffset, HORIZON_CLOUD_BANDS } from './cloud-layers';

describe('cloud-layers (seamless Minecraft-style distant horizon bands)', () => {
    it('defines 2 calm distant horizon cloud bands with glacial speeds (<= 4 px/s)', () => {
        expect(HORIZON_CLOUD_BANDS).toHaveLength(2);

        for (const band of HORIZON_CLOUD_BANDS) {
            expect(band.speed).toBeGreaterThan(0);
            expect(band.speed).toBeLessThanOrEqual(4);
            expect(band.tileWidth).toBeGreaterThanOrEqual(600);
            expect(band.slabs.length).toBeGreaterThanOrEqual(3);
            for (const slab of band.slabs) {
                expect(slab.w).toBeGreaterThan(0);
                expect(slab.h).toBeGreaterThan(0);
                // Every slab stays inside the tile so it wraps cleanly without clipping.
                expect(slab.x).toBeGreaterThanOrEqual(0);
                expect(slab.x + slab.w).toBeLessThanOrEqual(band.tileWidth);
            }
        }
    });

    it('wraps tile offsets seamlessly in (-tileWidth, 0] with zero jump across boundaries', () => {
        const tileWidth = 960;
        const speed = 2.0;

        // Walk across a full tile period (480s at 2px/s) in small steps and check continuity.
        let prev = computeTileOffset(0, speed, 0, tileWidth);
        expect(prev).toBeLessThanOrEqual(0);
        expect(prev).toBeGreaterThan(-tileWidth);

        for (let t = 1; t <= 600; t += 1) {
            const next = computeTileOffset(t, speed, 0, tileWidth);
            expect(next).toBeLessThanOrEqual(0);
            expect(next).toBeGreaterThan(-tileWidth);

            // Effective forward displacement modulo tileWidth must equal speed * dt (2px).
            const delta = (((prev - next) % tileWidth) + tileWidth) % tileWidth;
            expect(delta).toBeCloseTo(speed, 6);
            prev = next;
        }
    });

    it('handles negative parallax shifts without ever escaping (-tileWidth, 0]', () => {
        const tileWidth = 800;
        for (const parallax of [-200, -50, -0.5, 0, 0.5, 50, 200]) {
            const offset = computeTileOffset(0, 1.5, parallax, tileWidth);
            expect(offset).toBeLessThanOrEqual(0);
            expect(offset).toBeGreaterThan(-tileWidth);
        }
    });
});
