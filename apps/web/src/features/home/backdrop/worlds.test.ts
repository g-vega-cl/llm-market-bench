import { describe, expect, it } from 'vitest';
import { CEDAR_WORLD_ID, extractWorldFaces, gridToUv, RU, SX, SY, SZ } from './voxel-world';
import { buildCedarSanctuary, getCedarWorldAndFaces } from './worlds';

/** Splits a world's cloud voxels into per-cloud clusters, collapsing z into columns first. */
function groupCloudClusters(cells: Array<[number, number, number]>) {
    const columns = new Map<string, Array<[number, number, number]>>();
    for (const cell of cells) {
        const key = `${cell[0]},${cell[1]}`;
        const list = columns.get(key);
        if (list) list.push(cell);
        else columns.set(key, [cell]);
    }

    const seen = new Set<string>();
    const clusters: Array<Array<[number, number, number]>> = [];
    for (const key of columns.keys()) {
        if (seen.has(key)) continue;
        seen.add(key);
        const stack = [key];
        const cluster: Array<[number, number, number]> = [];
        while (stack.length > 0) {
            const cur = stack.pop() as string;
            cluster.push(...(columns.get(cur) ?? []));
            const [cx, cy] = cur.split(',').map(Number);
            for (const [dx, dy] of [
                [1, 0],
                [-1, 0],
                [0, 1],
                [0, -1],
            ]) {
                const neighbor = `${cx + dx},${cy + dy}`;
                if (!columns.has(neighbor) || seen.has(neighbor)) continue;
                seen.add(neighbor);
                stack.push(neighbor);
            }
        }
        clusters.push(cluster);
    }
    return clusters;
}

/** True when any voxel of the cluster sits within the 3-voxel shell around non-cloud geometry. */
function touchesTerrainWithin3(
    cluster: Array<[number, number, number]>,
    terrainKeys: Set<number>,
): boolean {
    for (const [cx, cy, cz] of cluster) {
        for (let dz = -3; dz <= 3; dz++) {
            for (let dy = -3; dy <= 3; dy++) {
                for (let dx = -3; dx <= 3; dx++) {
                    const nx = cx + dx;
                    const ny = cy + dy;
                    const nz = cz + dz;
                    if (nx < 0 || nx >= SX || ny < 0 || ny >= SY || nz < 0 || nz >= SZ) continue;
                    if (terrainKeys.has((nz * SY + ny) * SX + nx)) return true;
                }
            }
        }
    }
    return false;
}

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

    it('sculpts puffy stepped cloud silhouettes instead of plain rectangular slabs', () => {
        const w = buildCedarSanctuary(20261125);
        const cloudSet = new Set(w.cloudMaterials);
        const terrainKeys = new Set<number>();
        const cells: Array<[number, number, number]> = [];

        for (let z = 0; z < SZ; z++) {
            for (let y = 0; y < SY; y++) {
                for (let x = 0; x < SX; x++) {
                    const idx = (z * SY + y) * SX + x;
                    if (!w.solid[idx]) continue;
                    if (cloudSet.has(w.material[idx])) cells.push([x, y, z]);
                    else terrainKeys.add(idx);
                }
            }
        }
        expect(cells.length).toBeGreaterThan(300);

        const clusters = groupCloudClusters(cells);
        expect(clusters.length).toBeGreaterThanOrEqual(5);

        for (const cluster of clusters) {
            const baseZ = Math.min(...cluster.map((c) => c[2]));
            const topZ = Math.max(...cluster.map((c) => c[2]));
            const baseCells = cluster.filter((c) => c[2] === baseZ);
            const topCells = cluster.filter((c) => c[2] === topZ);
            const xs = topCells.map((c) => c[0]);
            const ys = topCells.map((c) => c[1]);
            const bboxArea =
                (Math.max(...xs) - Math.min(...xs) + 1) * (Math.max(...ys) - Math.min(...ys) + 1);

            // A stepped dome: the crown must inset sharply instead of repeating the slab footprint.
            expect(topZ - baseZ).toBeGreaterThanOrEqual(2);
            expect(topCells.length / baseCells.length).toBeLessThanOrEqual(0.75);
            // A rectangular crown fills its bounding box; a rounded puff does not.
            expect(topCells.length / bboxArea).toBeLessThanOrEqual(0.92);
            // Clouds float clear of the lodge roofline and the canopy.
            expect(baseZ).toBeGreaterThanOrEqual(24);

            expect(touchesTerrainWithin3(cluster, terrainKeys)).toBe(false);
        }
    });

    it('keeps the cloud volume on the under→mid→top ramp instead of flooding it with the top tone', () => {
        const w = buildCedarSanctuary(20261125);
        const farSet = new Set(w.farCloudMaterials);
        // buildStandardClouds registers [under, mid, top] per plane, near plane first.
        const nearMats = w.cloudMaterials.filter((id) => !farSet.has(id));

        const nearSet = new Set(nearMats);
        const toneCounts = new Map<string, number>();
        let nearTotal = 0;

        for (let z = 0; z < SZ; z++) {
            for (let y = 0; y < SY; y++) {
                for (let x = 0; x < SX; x++) {
                    const idx = (z * SY + y) * SX + x;
                    if (!w.solid[idx] || !nearSet.has(w.material[idx])) continue;
                    const color = w.palette[w.material[idx] - 1].color;
                    const tone = `${color.r},${color.g},${color.b}`;
                    toneCounts.set(tone, (toneCounts.get(tone) ?? 0) + 1);
                    nearTotal++;
                }
            }
        }

        // Each cloud registers its own three materials, so rank the distinct tones by luminance.
        const tones = [...toneCounts.entries()]
            .map(([tone, count]) => {
                const [r, g, b] = tone.split(',').map(Number);
                return { count, luminance: 0.2126 * r + 0.7152 * g + 0.0722 * b };
            })
            .sort((a, b) => a.luminance - b.luminance);
        expect(tones).toHaveLength(3);

        const share = (index: number) => tones[index].count / nearTotal;
        expect(nearTotal).toBeGreaterThan(500);
        // A one-course crown can never own more than a third of the body volume.
        expect(share(2)).toBeLessThanOrEqual(0.3);
        // The mid tone must dominate, and the underside must stay a minority band.
        expect(share(1)).toBeGreaterThanOrEqual(0.45);
        expect(share(0)).toBeLessThanOrEqual(0.35);
    });
});
