import { describe, expect, it } from 'vitest';
import { CEDAR_WORLD_ID, extractWorldFaces, gridToUv, RU, SX, SY, SZ } from './voxel-world';
import { buildCedarSanctuary, getCedarWorldAndFaces } from './worlds';

describe('worlds (panoramic Cedar Sanctuary diorama & cached face extraction)', () => {
    it('builds the wide panoramic Cedar Sanctuary deterministically with cached face extraction', () => {
        const first = getCedarWorldAndFaces();
        const second = getCedarWorldAndFaces();
        expect(first).toBe(second);

        expect(first.world.worldId).toBe(CEDAR_WORLD_ID);
        expect(first.world.voxelCount).toBeGreaterThan(8000);
        expect(first.world.lamps.length).toBeGreaterThanOrEqual(8);
        expect(first.world.petals.length).toBe(24);
        expect(first.world.fireflies.length).toBe(18);
        expect(first.world.koi.length).toBe(2);
        expect(first.faces.island.length).toBeGreaterThan(3000);
        expect(first.faces.cloudsFar.length).toBeGreaterThan(100);
        expect(first.faces.cloudsNear.length).toBeGreaterThan(100);

        // Verify wide horizontal span along camera u-axis (> 140 diagonal voxel units)
        let minU = Number.POSITIVE_INFINITY;
        let maxU = Number.NEGATIVE_INFINITY;
        for (const [, x, y] of first.faces.island) {
            const [u] = gridToUv(x, y);
            if (u < minU) minU = u;
            if (u > maxU) maxU = u;
        }
        expect(maxU - minU).toBeGreaterThanOrEqual(RU * 1.8);
    });

    it('shapes 3D voxel clouds as flat-bottomed slabs with monotonic painter sort order', () => {
        const a = buildCedarSanctuary(20261125);
        const b = buildCedarSanctuary(20261125);
        expect(a.voxelCount).toBe(b.voxelCount);
        expect(a.lamps).toEqual(b.lamps);

        const cloudSet = new Set(a.cloudMaterials);
        const colMinZ = new Map<string, number>();
        for (let z = 0; z < SZ; z++) {
            for (let y = 0; y < SY; y++) {
                for (let x = 0; x < SX; x++) {
                    const idx = (z * SY + y) * SX + x;
                    if (!a.solid[idx] || !cloudSet.has(a.material[idx])) continue;
                    const key = `${x},${y}`;
                    if (!colMinZ.has(key)) colMinZ.set(key, z);
                }
            }
        }

        let sameBasePairs = 0;
        let totalNeighborPairs = 0;
        for (const [key, minZ] of colMinZ) {
            const [xs, ys] = key.split(',');
            const x = Number(xs);
            const y = Number(ys);
            for (const [dx, dy] of [
                [1, 0],
                [0, 1],
            ]) {
                const nMinZ = colMinZ.get(`${x + dx},${y + dy}`);
                if (nMinZ === undefined) continue;
                totalNeighborPairs++;
                if (nMinZ === minZ) sameBasePairs++;
            }
        }
        expect(totalNeighborPairs).toBeGreaterThan(50);
        expect(sameBasePairs / totalNeighborPairs).toBeGreaterThanOrEqual(0.99);

        const faces = extractWorldFaces(a);
        for (const layer of [faces.cloudsFar, faces.cloudsNear, faces.island]) {
            for (let i = 1; i < layer.length; i++) {
                expect(layer[i][0]).toBeGreaterThanOrEqual(layer[i - 1][0]);
            }
        }
    });
});
