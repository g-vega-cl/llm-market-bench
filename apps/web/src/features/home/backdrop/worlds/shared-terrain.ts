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

/** Places 6 wide 3D Minecraft-style cloud slabs around the panoramic cedar ridge flanks. */
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

    const [flx, fly] = uvToGrid(-82, -32);
    c.cloudSlab(flx, fly, 34, 18, 10, 2, mats, { dx: 4, dy: 2, w: 10, d: 5 }, 'far');

    const [frx, fry] = uvToGrid(66, -34);
    c.cloudSlab(frx - 10, fry, 32, 18, 10, 2, mats, { dx: 4, dy: 2, w: 9, d: 5 }, 'far');

    // Keep far upper cloud offset to the east flank so the central open-sky CTA corridor stays unobstructed
    const [fcx, fcy] = uvToGrid(36, -42);
    c.cloudSlab(fcx - 6, fcy, 36, 18, 9, 2, mats, { dx: 4, dy: 2, w: 10, d: 4 }, 'far');

    const [nlx, nly] = uvToGrid(-90, 14);
    c.cloudSlab(nlx, nly, 18, 17, 10, 2, mats, { dx: 4, dy: 2, w: 9, d: 5 }, 'near');

    const [nrx, nry] = uvToGrid(88, 14);
    c.cloudSlab(nrx - 4, nry, 18, 17, 10, 2, mats, { dx: 4, dy: 2, w: 9, d: 5 }, 'near');

    const [nfx, nfy] = uvToGrid(14, 54);
    c.cloudSlab(nfx - 6, nfy, 13, 16, 8, 2, mats, { dx: 3, dy: 2, w: 9, d: 4 }, 'near');
}
