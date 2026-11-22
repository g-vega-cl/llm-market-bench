import { gridToUv, RU, RV, SX, SY, uvToGrid, type VoxelCanvasBuilder } from '../voxel-world';

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

/** Sculpts the wide elliptical stone undercrust and hanging roots beneath the panoramic ridge. */
export function buildPanoramicUndercrust(
    c: VoxelCanvasBuilder,
    darkStone: number,
    midStone: number,
    rootDark: number,
    mossRoot: number,
) {
    for (let z = 0; z < 7; z++) {
        const taper = 0.92 - (6 - z) * 0.11;
        const ruZ = RU * taper;
        const rvZ = RV * taper;
        for (let y = 0; y < SY; y++) {
            for (let x = 0; x < SX; x++) {
                const [u, v] = gridToUv(x, y);
                const d = Math.hypot(u / ruZ, v / rvZ);
                if (d <= 1 - c.rnd() * 0.14) {
                    c.put(x, y, z, c.rnd() < 0.52 ? darkStone : midStone);
                }
            }
        }
    }
    for (let i = 0; i < 36; i++) {
        const a = c.rnd() * Math.PI * 2;
        const radial = 0.45 + c.rnd() * 0.46;
        const [rx, ry] = uvToGrid(Math.cos(a) * RU * radial, Math.sin(a) * RV * radial);
        const len = c.ri(2, 5);
        for (let k = 0; k < len; k++) {
            c.put(rx, ry, 5 - k, k < 2 ? rootDark : mossRoot);
        }
    }
}

/** Scatters six field-carved cloud puffs across the open-sky flanks, clear of the CTA corridor. */
export function buildStandardClouds(
    c: VoxelCanvasBuilder,
    nearHex: [string, string, string],
    farHex: [string, string, string],
) {
    const ramp = (hex: [string, string, string], far: boolean, group: number) =>
        hex.map((h) => c.cloudMat(h, far, group)) as [number, number, number];

    const clouds: Array<[number, number, number, number, number, 'far' | 'near']> = [
        [-58, -40, 44, 20, 7, 'near'],
        [-56, -8, 42, 17, 6, 'near'],
        [-62, 16, 42, 15, 6, 'far'],
        [62, -46, 46, 19, 7, 'near'],
        [48, -16, 36, 17, 6, 'near'],
        [60, 0, 39, 15, 6, 'far'],
    ];

    clouds.forEach(([u, v, z, halfU, halfV, plane], group) => {
        const mats = plane === 'far' ? ramp(farHex, true, group) : ramp(nearHex, false, group);
        c.cloudPuff(u, v, z, halfU, halfV, { near: mats, far: mats }, plane);
    });
}
