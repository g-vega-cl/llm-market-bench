import { describe, expect, it } from 'vitest';
import { buildGarden, extractWorldFaces, SX, SY, SZ } from './garden-world';

describe('garden-world (Minecraft flat-slab clouds, 2-tier cloud planes & cached face extraction)', () => {
    it('builds deterministically for the same seed including fireflies and koi anchors', () => {
        const a = buildGarden(20261121);
        const b = buildGarden(20261121);

        expect(a.voxelCount).toBe(b.voxelCount);
        expect(a.petals).toEqual(b.petals);
        expect(a.fireflies).toEqual(b.fireflies);
        expect(a.koi).toEqual(b.koi);
        expect(a.cloudMaterials).toEqual(b.cloudMaterials);
        expect(a.fireflies.length).toBe(16);
        expect(a.koi.length).toBe(2);
    });

    it('keeps petal count sparse (<= 24) so motion stays calm and non-distracting', () => {
        const world = buildGarden();

        expect(world.petals.length).toBeGreaterThan(0);
        expect(world.petals.length).toBeLessThanOrEqual(24);
    });

    it('shapes 3D voxel clouds as flat-bottomed Minecraft slabs rather than rounded ellipsoids', () => {
        const world = buildGarden();
        const cloudSet = new Set(world.cloudMaterials);

        // Collect the lowest cloud z at every (x, y) column containing a cloud voxel.
        const colMinZ = new Map<string, number>();
        let cloudVoxels = 0;

        for (let z = 0; z < SZ; z++) {
            for (let y = 0; y < SY; y++) {
                for (let x = 0; x < SX; x++) {
                    const idx = (z * SY + y) * SX + x;
                    if (!world.solid[idx] || !cloudSet.has(world.material[idx])) continue;
                    cloudVoxels++;
                    const key = `${x},${y}`;
                    const prev = colMinZ.get(key);
                    if (prev === undefined || z < prev) {
                        colMinZ.set(key, z);
                    }
                }
            }
        }

        expect(cloudVoxels).toBeGreaterThan(100);

        // Every cloud slab sits on a flat base z plane: check that in each column
        // the majority of its 4-neighbors with cloud voxels share the exact same base z
        // (an ellipsoid curves upward at edges, giving many differing neighbor base z values).
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
        expect(sameBasePairs / totalNeighborPairs).toBeGreaterThanOrEqual(0.95);
    });

    it('extracts and sorts visible island, far-cloud, and near-cloud faces once for reuse across resizes', () => {
        const world = buildGarden();
        const faces = extractWorldFaces(world);

        expect(faces.island.length).toBeGreaterThan(1000);
        expect(faces.cloudsFar.length).toBeGreaterThan(50);
        expect(faces.cloudsNear.length).toBeGreaterThan(50);

        // Verify painter's depth order (monotonically non-decreasing sort key x + y + z).
        for (const layer of [faces.cloudsFar, faces.cloudsNear, faces.island]) {
            for (let i = 1; i < layer.length; i++) {
                expect(layer[i][0]).toBeGreaterThanOrEqual(layer[i - 1][0]);
            }
        }
    });
});
