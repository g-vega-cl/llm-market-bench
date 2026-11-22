import {
    CEDAR_WORLD_ID,
    createVoxelCanvas,
    gridToUv,
    RU,
    RV,
    uvToGrid,
    type VoxelCanvasBuilder,
    type VoxelWorld,
} from '../voxel-world';
import {
    buildPanoramicUndercrust,
    buildStandardClouds,
    fillTerrainVolume,
    type HeightFn,
} from './shared-terrain';

function carveValleyBrook(
    c: VoxelCanvasBuilder,
    heightAt: HeightFn,
    mats: Record<string, number>,
    glints: Array<[number, number, number]>,
) {
    const seen = new Set<string>();
    for (let u = -24; u <= 34; u++) {
        const vCenter = Math.round(4 + Math.sin((u + 10) * 0.11) * 7 + u * 0.36);
        for (let dv = -3; dv <= 3; dv++) {
            for (let du = -1; du <= 1; du++) {
                const [px, py] = uvToGrid(u + du, vCenter + dv);
                const key = `${px},${py}`;
                if (seen.has(key)) continue;
                seen.add(key);
                const h = heightAt(px, py);
                if (h === null) continue;
                for (let z = h - 2; z <= h + 2; z++) c.put(px, py, z, 0);
                c.put(px, py, h - 2, mats.graniteDark);
                const isFoam = Math.abs(dv) >= 2 && c.rnd() < 0.35;
                c.put(
                    px,
                    py,
                    h - 1,
                    isFoam ? mats.foam : c.rnd() < 0.55 ? mats.waterHi : mats.water,
                );
                if (c.rnd() < 0.18) glints.push([px, py, h - 1]);
            }
        }
    }
}

function carveCliffWaterfall(
    c: VoxelCanvasBuilder,
    mats: Record<string, number>,
    glints: Array<[number, number, number]>,
) {
    for (let u = 28; u <= 36; u++) {
        const vEdge = Math.round(Math.sqrt(Math.max(0, 1 - (u / RU) ** 2)) * RV) - 2;
        for (let z = 3; z <= 14; z++) {
            const [wx, wy] = uvToGrid(u, vEdge + (14 - z > 6 ? 1 : 0));
            c.put(wx, wy, z, z <= 5 ? mats.foam : c.rnd() < 0.45 ? mats.waterHi : mats.water);
            if (z >= 5 && c.rnd() < 0.25) glints.push([wx, wy, z]);
        }
    }
}

function buildArchedFootbridge(
    c: VoxelCanvasBuilder,
    heightAt: HeightFn,
    mats: Record<string, number>,
): Array<[number, number, number]> {
    for (let v = 1; v <= 13; v++) {
        const arch = Math.round(Math.sin(((v - 1) / 12) * Math.PI) * 2.5);
        const [bx0, by0] = uvToGrid(0, v);
        const bz = (heightAt(bx0, by0) ?? 13) + 1 + arch;
        for (let du = -2; du <= 2; du++) {
            c.putUV(du, v, bz, Math.abs(du) === 2 ? mats.cedarDark : mats.cedar);
        }
        if (v === 2 || v === 7 || v === 12) {
            c.putUV(-2, v, bz + 1, mats.cedarDark);
            c.putUV(2, v, bz + 1, mats.cedarDark);
            if (v === 7) {
                c.putUV(-2, v, bz + 2, mats.lantern, true);
                c.putUV(2, v, bz + 2, mats.lantern, true);
            }
        }
    }
    const [b1x, b1y] = uvToGrid(-2, 7);
    const [b2x, b2y] = uvToGrid(2, 7);
    const bridgeLampZ = (heightAt(b1x, b1y) ?? 13) + 6;
    return [
        [b1x, b1y, bridgeLampZ],
        [b2x, b2y, bridgeLampZ],
    ];
}

function buildTimberAqueduct(
    c: VoxelCanvasBuilder,
    heightAt: HeightFn,
    mats: Record<string, number>,
    glints: Array<[number, number, number]>,
) {
    for (let u = -24; u <= 20; u++) {
        const vAq = -12 - Math.round(Math.cos(u * 0.06) * 2);
        const [ax, ay] = uvToGrid(u, vAq);
        const bz = heightAt(ax, ay) ?? 14;
        const deckZ = 20;
        for (let dv = -1; dv <= 1; dv++) {
            c.putUV(u, vAq + dv, deckZ, dv === 0 ? mats.waterHi : mats.cedar);
            c.putUV(u, vAq + dv, deckZ - 1, mats.cedarDark);
        }
        if ((u + 24) % 8 === 0) {
            for (let z = bz; z < deckZ - 1; z++) {
                c.putUV(u, vAq - 1, z, mats.cedarDark);
                c.putUV(u, vAq + 1, z, mats.cedarDark);
            }
        }
        if (u % 7 === 0) glints.push([ax, ay, deckZ]);
    }
}

/**
 * Carves the highland spring brook, arches the cedar footbridge across the
 * central valley, strings the elevated timber aqueduct, and drops the front
 * granite cliff waterfall.
 */
function buildWaterworksAndBridge(
    c: VoxelCanvasBuilder,
    heightAt: HeightFn,
    mats: Record<string, number>,
) {
    const glints: Array<[number, number, number]> = [];
    carveValleyBrook(c, heightAt, mats, glints);
    carveCliffWaterfall(c, mats, glints);
    const lamps = buildArchedFootbridge(c, heightAt, mats);
    buildTimberAqueduct(c, heightAt, mats, glints);
    return { glints, lamps };
}

/**
 * Sculpts the two-story Cedar Timber Sanctuary Lodge on the left highland bluff
 * (u = -54..-32) with dressed granite terrace, glowing paper windows, overhanging gable
 * eaves, and stone hearth chimney, plus an east stone lantern shrine terrace.
 */
function buildSanctuaryArchitecture(
    c: VoxelCanvasBuilder,
    heightAt: HeightFn,
    mats: Record<string, number>,
): Array<[number, number, number]> {
    const lamps: Array<[number, number, number]> = [];

    // Left bluff lodge platform (u = -54..-32, v = -14..+10) in grid coordinates aligned to clean rectilinear walls
    const [lx0, ly0] = uvToGrid(-43, -2);
    const baseZ = heightAt(lx0, ly0) ?? 19;

    // Cut granite plinth & stepped front timber porch
    c.box(lx0 - 8, ly0 - 7, baseZ - 1, 16, 14, 2, mats.granite);
    c.box(lx0 - 7, ly0 - 6, baseZ + 1, 14, 12, 1, mats.graniteDark);
    c.box(lx0 - 6, ly0 + 5, baseZ + 1, 12, 3, 1, mats.cedar);

    // First-story cedar frame & warm backlit window bays
    c.box(lx0 - 6, ly0 - 5, baseZ + 2, 12, 10, 6, mats.cedar);
    for (const [wx, wy] of [
        [lx0 - 6, ly0 - 5],
        [lx0 + 5, ly0 - 5],
        [lx0 - 6, ly0 + 4],
        [lx0 + 5, ly0 + 4],
    ]) {
        c.box(wx, wy, baseZ + 2, 1, 1, 6, mats.cedarDark);
    }
    // Glowing warm windows on front (+y) and right (+x) visible faces
    c.box(lx0 - 3, ly0 + 4, baseZ + 3, 2, 1, 3, mats.windowGlow, true);
    c.box(lx0 + 1, ly0 + 4, baseZ + 3, 2, 1, 3, mats.windowGlow, true);
    c.box(lx0 + 5, ly0 - 2, baseZ + 3, 1, 4, 3, mats.windowGlow, true);

    // Lower pitched cedar-slate eaves overhang
    c.box(lx0 - 8, ly0 - 7, baseZ + 8, 16, 14, 1, mats.cedarDark);
    c.box(lx0 - 7, ly0 - 6, baseZ + 9, 14, 12, 1, mats.slateRoof);

    // Upper loft gable with glowing dormer lantern
    c.box(lx0 - 4, ly0 - 4, baseZ + 10, 8, 8, 4, mats.cedar);
    c.box(lx0 - 1, ly0 + 3, baseZ + 11, 2, 1, 2, mats.windowGlow, true);
    c.box(lx0 - 6, ly0 - 6, baseZ + 14, 12, 12, 1, mats.cedarDark);
    c.box(lx0 - 4, ly0 - 4, baseZ + 15, 8, 8, 2, mats.slateRoof);
    c.box(lx0 - 2, ly0 - 2, baseZ + 17, 4, 4, 1, mats.pine);

    // Stone hearth chimney rising alongside back-left wall
    c.box(lx0 - 7, ly0 - 4, baseZ + 2, 2, 2, 16, mats.graniteDark);
    c.put(lx0 - 7, ly0 - 4, baseZ + 18, mats.granite);

    // Porch sconces
    c.put(lx0 - 4, ly0 + 7, baseZ + 3, mats.lantern, true);
    c.put(lx0 + 3, ly0 + 7, baseZ + 3, mats.lantern, true);
    lamps.push(
        [lx0 - 4, ly0 + 7, baseZ + 3],
        [lx0 + 3, ly0 + 7, baseZ + 3],
        [lx0 + 5, ly0, baseZ + 4],
    );

    // East Sanctuary cedar torii / portal gate overlooking the autumn maple bluff (u ~ +34, v ~ -6)
    const [gx, gy] = uvToGrid(34, -6);
    const gz = heightAt(gx, gy) ?? 17;
    c.box(gx - 3, gy, gz + 1, 1, 1, 7, mats.mapleCrimson);
    c.box(gx + 3, gy, gz + 1, 1, 1, 7, mats.mapleCrimson);
    c.box(gx - 4, gy, gz + 7, 9, 1, 1, mats.cedarDark);
    c.box(gx - 5, gy, gz + 8, 11, 1, 1, mats.cedarDark);
    c.put(gx, gy, gz + 6, mats.lantern, true);
    lamps.push([gx, gy, gz + 6]);

    // Granite path lantern posts across the eastern ridge
    for (const [lu, lv] of [
        [18, 6],
        [48, 8],
        [62, -4],
    ] as const) {
        const [px, py] = uvToGrid(lu, lv);
        const pz = (heightAt(px, py) ?? 16) + 1;
        c.box(px, py, pz, 1, 1, 2, mats.graniteDark);
        c.put(px, py, pz + 2, mats.lantern, true);
        c.put(px, py, pz + 3, mats.granite);
        lamps.push([px, py, pz + 2]);
    }

    return lamps;
}

/**
 * Plants towering multi-tier Douglas pines and fiery autumn maple trees across
 * both outer ridges while keeping the central valley sightline clear for CTA copy.
 */
function plantHighlandForest(
    c: VoxelCanvasBuilder,
    heightAt: HeightFn,
    mats: Record<string, number>,
) {
    const pines: Array<[number, number, number]> = [
        [-68, -8, 11],
        [-62, 12, 9],
        [-58, -22, 10],
        [-28, -24, 9],
        [18, -24, 10],
        [52, -20, 12],
        [68, -6, 10],
        [60, 14, 9],
    ];
    for (const [u, v, height] of pines) {
        const [tx, ty] = uvToGrid(u, v);
        const bz = heightAt(tx, ty);
        if (bz === null) continue;
        c.box(tx, ty, bz + 1, 2, 2, height - 3, mats.cedarDark);
        c.cyl(tx, ty, bz + Math.floor(height * 0.45), 5, 2, mats.pine);
        c.cyl(tx, ty, bz + Math.floor(height * 0.68), 4, 2, mats.pineHi);
        c.cyl(tx, ty, bz + Math.floor(height * 0.88), 3, 2, mats.pine);
        c.cyl(tx, ty, bz + height, 1, 2, mats.pineHi);
    }

    const maples: Array<[number, number, number]> = [
        [-24, 18, 4],
        [30, 8, 5],
        [44, -8, 5],
        [54, 4, 4],
        [40, 18, 4],
    ];
    for (const [u, v, radius] of maples) {
        const [tx, ty] = uvToGrid(u, v);
        const bz = heightAt(tx, ty);
        if (bz === null) continue;
        c.box(tx, ty, bz + 1, 2, 2, 6, mats.cedar);
        c.sphere(tx, ty, bz + 8, radius, mats.mapleAmber);
        c.sphere(tx + 1, ty - 1, bz + 9, radius - 1, mats.mapleGold);
        c.sphere(tx - 1, ty + 1, bz + 7, Math.max(2, radius - 2), mats.mapleCrimson);
    }

    // Scattered mossy boulders along bluff rims
    for (const [bu, bv, br] of [
        [-64, 2, 2],
        [-30, 14, 2],
        [22, -16, 2],
        [58, -14, 2],
        [66, 8, 2],
    ] as const) {
        const [bx, by] = uvToGrid(bu, bv);
        const bz = heightAt(bx, by);
        if (bz !== null) c.sphere(bx, by, bz + 1, br, mats.granite);
    }
}

/**
 * Generates the panoramic Cedar Sanctuary 3D voxel island (`144x144x64`),
 * wide along the screen horizon so the sanctuary lodge, aqueduct trestle,
 * valley brook bridge, and autumn maple bluff read cleanly around hero CTAs.
 */
export function buildCedarSanctuary(seedValue = 20261125): VoxelWorld {
    const c = createVoxelCanvas(seedValue);
    const mossTop = c.mat('#4e8455');
    const mossHi = c.mat('#619963');
    const dirt = c.mat('#7d5e3e');
    const granite = c.mat('#8b867c');
    const graniteDark = c.mat('#68635b');

    const mats = {
        granite,
        graniteDark,
        cedar: c.mat('#80583c'),
        cedarDark: c.mat('#543827'),
        slateRoof: c.mat('#354442'),
        pine: c.mat('#2d5f41'),
        pineHi: c.mat('#43845a'),
        mapleAmber: c.mat('#de7e35'),
        mapleGold: c.mat('#eeb355'),
        mapleCrimson: c.mat('#bd4728'),
        water: c.mat('#4e9cb2'),
        waterHi: c.mat('#82cfe0'),
        foam: c.mat('#d6efe8'),
        windowGlow: c.mat('#ffda82', true),
        lantern: c.mat('#ffcf6e', true),
    };

    const heightAt: HeightFn = (x, y) => {
        const [u, v] = gridToUv(x, y);
        const d = Math.hypot(u / RU, v / RV);
        if (d > 1) return null;

        // Twin flanking highland bluffs (left lodge bluff u~-46, right maple bluff u~+46) framing an open central brook valley
        const leftBluff = Math.exp(-((u + 46) ** 2) / 560 - v ** 2 / 480) * 6;
        const rightBluff = Math.exp(-((u - 46) ** 2) / 620 - (v + 4) ** 2 / 500) * 5;
        const crest = Math.cos(u * 0.09) * Math.sin(v * 0.14) * 1.1;
        const bevel = Math.min(1, (1 - d) * 3.4) * 3;
        return Math.round(11 + leftBluff + rightBluff + crest + bevel);
    };

    fillTerrainVolume(c, heightAt, (depth) => {
        if (depth === 0) return c.rnd() < 0.62 ? mossTop : mossHi;
        return depth <= 2 ? dirt : depth <= 5 ? granite : graniteDark;
    });
    buildPanoramicUndercrust(c, graniteDark, granite, mats.cedarDark, mats.pine);

    const { glints, lamps: bridgeLamps } = buildWaterworksAndBridge(c, heightAt, mats);
    const archLamps = buildSanctuaryArchitecture(c, heightAt, mats);
    plantHighlandForest(c, heightAt, mats);
    buildStandardClouds(c, ['#9bb0a7', '#c5d4cb', '#ede8da'], ['#889e95', '#b3c4bb', '#ded9cb']);

    const petals = Array.from({ length: 24 }, () => {
        const u = c.ri(-76, 76);
        const v = c.ri(-28, 28);
        const [px, py] = uvToGrid(u, v);
        return [px, py, c.ri(24, 40)] as [number, number, number];
    });

    const fireflies = Array.from({ length: 18 }, () => {
        const u = c.ri(-68, 68);
        const v = c.ri(-22, 26);
        const [fx, fy] = uvToGrid(u, v);
        return [fx, fy, (heightAt(fx, fy) ?? 15) + c.ri(3, 11)] as [number, number, number];
    });

    const [k1x, k1y] = uvToGrid(-10, 4);
    const [k2x, k2y] = uvToGrid(22, 16);
    const koi: Array<[number, number, number]> = [
        [k1x, k1y, (heightAt(k1x, k1y) ?? 13) - 1],
        [k2x, k2y, (heightAt(k2x, k2y) ?? 13) - 1],
    ];

    return {
        worldId: CEDAR_WORLD_ID,
        solid: c.solid,
        material: c.material,
        emissive: c.emissive,
        palette: c.palette,
        cloudMaterials: c.cloudIds,
        farCloudMaterials: c.farCloudIds,
        petals,
        glints,
        lamps: [...bridgeLamps, ...archLamps],
        fireflies,
        koi,
        voxelCount: c.countVoxels(),
    };
}
