import { CX, CY, R, SX, SY, type VoxelCanvasBuilder } from '../voxel-world';

export type HeightFn = (x: number, y: number) => number | null;

/** Fills extruded island terrain from z=6 up to heightAt(x,y) via a caller-supplied depth classifier. */
export function fillTerrainVolume(
    c: VoxelCanvasBuilder,
    heightAt: HeightFn,
    pickMat: (depth: number) => number,
) {
    for (let y = 0; y < SY; y++) {
        for (let x = 0; x < SX; x++) {
            const h = heightAt(x, y);
            if (h === null) continue;
            for (let z = 6; z <= h; z++) {
                c.put(x, y, z, pickMat(h - z));
            }
        }
    }
}

/** Sculpts the tapered underside stone cone and hanging roots/stalactites beneath the island. */
export function buildIslandUndercrust(
    c: VoxelCanvasBuilder,
    darkStone: number,
    midStone: number,
    stalactiteA: number,
    stalactiteB: number,
) {
    for (let z = 0; z < 7; z++) {
        const r = Math.round(R * (0.9 - z * 0.11));
        for (let y = CY - r; y <= CY + r; y++) {
            for (let x = CX - r; x <= CX + r; x++) {
                const d = Math.hypot((x - CX) / r, (y - CY) / r);
                if (d <= 1 - c.rnd() * 0.17) {
                    c.put(x, y, z, c.rnd() < 0.5 ? darkStone : midStone);
                }
            }
        }
    }
    for (let i = 0; i < 24; i++) {
        const a = c.rnd() * Math.PI * 2;
        const r = R * (0.52 + c.rnd() * 0.42);
        const x = Math.round(CX + Math.cos(a) * r);
        const y = Math.round(CY + Math.sin(a) * r * 0.92);
        const len = c.ri(2, 4);
        for (let k = 0; k < len; k++) {
            c.put(x, y, 5 - k, k < 2 ? stalactiteA : stalactiteB);
        }
    }
}

/** Places the 6 standard 3D Minecraft cloud slabs split cleanly into far/near parallax buckets. */
export function buildStandardClouds(
    c: VoxelCanvasBuilder,
    nearHex: [string, string, string],
    farHex: [string, string, string],
) {
    const mats = {
        near: [c.cloudMat(nearHex[0]), c.cloudMat(nearHex[1]), c.cloudMat(nearHex[2])] as [
            number,
            number,
            number,
        ],
        far: [
            c.cloudMat(farHex[0], true),
            c.cloudMat(farHex[1], true),
            c.cloudMat(farHex[2], true),
        ] as [number, number, number],
    };

    c.cloudSlab(4, 34, 34, 15, 9, 2, mats, { dx: 3, dy: 2, w: 9, d: 5 }, 'far');
    c.cloudSlab(7, 72, 20, 16, 10, 2, mats, { dx: 4, dy: 2, w: 8, d: 5 }, 'near');
    c.cloudSlab(74, 6, 36, 16, 10, 2, mats, { dx: 3, dy: 2, w: 9, d: 6 }, 'far');
    c.cloudSlab(82, 32, 24, 14, 9, 2, mats, { dx: 3, dy: 2, w: 7, d: 5 }, 'near');
    c.cloudSlab(68, 82, 14, 16, 9, 2, mats, { dx: 3, dy: 2, w: 9, d: 5 }, 'near');
    c.cloudSlab(22, 6, 40, 17, 8, 2, mats, { dx: 4, dy: 2, w: 9, d: 4 }, 'far');
}
