import {
    CX,
    CY,
    createVoxelCanvas,
    R,
    type VoxelCanvasBuilder,
    type VoxelWorld,
} from '../voxel-world';
import {
    buildIslandUndercrust,
    buildStandardClouds,
    fillTerrainVolume,
    type HeightFn,
} from './shared-terrain';

function buildForgeHearth(c: VoxelCanvasBuilder, heightAt: HeightFn, mats: Record<string, number>) {
    const fx = CX - 13;
    const fy = CY - 12;
    const fz = heightAt(fx, fy) ?? 17;
    c.cyl(fx, fy, fz, 10, 4, mats.obsidianHi);
    c.cyl(fx, fy, fz + 4, 8, 5, mats.basalt);
    c.box(fx - 5, fy - 4, fz + 9, 10, 8, 9, mats.obsidian);
    c.box(fx - 3, fy - 3, fz + 18, 6, 6, 11, mats.basalt2);
    c.box(fx - 2, fy - 2, fz + 29, 4, 4, 3, mats.ash);
    c.box(fx - 1, fy - 1, fz + 10, 3, 4, 4, mats.lava, true);
    c.box(fx, fy, fz + 11, 2, 3, 2, mats.lavaCore, true);
    c.box(fx + 7, fy + 2, fz + 9, 4, 2, 2, mats.anvil);
    c.box(fx + 6, fy + 1, fz + 11, 6, 4, 2, mats.anvilHi);
    c.box(fx + 6, fy - 5, fz + 9, 4, 3, 2, mats.copper);
    c.box(fx + 7, fy - 4, fz + 11, 2, 2, 1, mats.copper2);
    return { fx, fy, fz };
}

function carveMagmaChannel(
    c: VoxelCanvasBuilder,
    heightAt: HeightFn,
    fx: number,
    fy: number,
    mats: Record<string, number>,
) {
    const glints: Array<[number, number, number]> = [];
    const calderaCenters: Array<[number, number]> = [];
    for (let t = 0; t <= 44; t++) {
        const rx = Math.round(fx + 2 + t * 0.72);
        const ry = Math.round(fy + 5 + Math.sin(t * 0.16) * 5 + t * 0.52);
        if (heightAt(rx, ry) === null) continue;
        const w = t > 18 && t < 32 ? 4 : 3;
        carveChannelDisc(c, heightAt, rx, ry, w, mats, glints);
        if (t === 24 || t === 33) calderaCenters.push([rx, ry]);
    }
    const fallX = CX + 20;
    const fallY = CY + 22;
    const fallTop = heightAt(fallX, fallY) ?? 15;
    for (let z = 3; z <= fallTop; z++) {
        c.put(fallX, fallY, z, mats.lava, true);
        c.put(fallX + 1, fallY, z, z % 2 === 0 ? mats.lavaCore : mats.lava, true);
    }
    return { glints, calderaCenters };
}

function carveChannelDisc(
    c: VoxelCanvasBuilder,
    heightAt: HeightFn,
    rx: number,
    ry: number,
    w: number,
    mats: Record<string, number>,
    glints: Array<[number, number, number]>,
) {
    for (let oy = -w; oy <= w; oy++) {
        for (let ox = -w; ox <= w; ox++) {
            if (ox * ox + oy * oy > w * w) continue;
            const px = rx + ox;
            const py = ry + oy;
            const ph = heightAt(px, py);
            if (ph === null) continue;
            for (let z = ph - 1; z <= ph + 1; z++) c.put(px, py, z, 0);
            const matId =
                Math.abs(ox) + Math.abs(oy) <= 1
                    ? mats.lavaCore
                    : c.rnd() < 0.6
                      ? mats.lava
                      : mats.lavaDeep;
            c.put(px, py, ph - 2, matId, true);
            if (c.rnd() < 0.22) glints.push([px, py, ph - 1]);
        }
    }
}

export function buildMagmaForge(seedValue = 20261122): VoxelWorld {
    const c = createVoxelCanvas(seedValue);
    const basalt = c.mat('#3d3638');
    const basalt2 = c.mat('#4f4648');
    const obsidian = c.mat('#241e29');
    const obsidianHi = c.mat('#382f42');
    const ash = c.mat('#5c5354');
    const mats = {
        basalt,
        basalt2,
        obsidian,
        obsidianHi,
        ash,
        copper: c.mat('#b8683c'),
        copper2: c.mat('#d6844b'),
        anvil: c.mat('#626873'),
        anvilHi: c.mat('#8c94a3'),
        lavaDeep: c.mat('#d93b14', true),
        lava: c.mat('#ff621c', true),
        lavaCore: c.mat('#ffbe3d', true),
        emberStone: c.mat('#7d3222', true),
    };

    const heightAt: HeightFn = (x, y) => {
        const d = Math.hypot((x - CX) / R, (y - CY) / (R * 0.92));
        if (d > 1) return null;
        const ridge = Math.max(0, Math.sin((x - CX) * 0.14) * 3.4 - (y - CY) * 0.08);
        return Math.round(13 + ridge + Math.min(1, (1 - d) * 3.1) * 3);
    };

    fillTerrainVolume(c, heightAt, (depth) => {
        if (depth === 0) return c.rnd() < 0.55 ? basalt : c.rnd() < 0.6 ? basalt2 : ash;
        return depth <= 2 ? (c.rnd() < 0.45 ? obsidianHi : basalt) : obsidian;
    });
    buildIslandUndercrust(c, obsidian, obsidianHi, mats.emberStone, mats.lavaDeep);

    const { fx, fy, fz } = buildForgeHearth(c, heightAt, mats);
    const { glints, calderaCenters } = carveMagmaChannel(c, heightAt, fx, fy, mats);

    const lamps: Array<[number, number, number]> = [
        [fx + 1, fy + 1, fz + 12],
        [fx, fy, fz + 31],
    ];
    for (const [px, py, ph] of [
        [CX + 18, CY - 14, 12],
        [CX - 22, CY + 12, 10],
        [CX + 6, CY - 24, 9],
    ] as const) {
        const bz = heightAt(px, py) ?? 15;
        c.cyl(px, py, bz, 3, ph, obsidian);
        c.put(px + 1, py + 1, bz + Math.floor(ph * 0.6), mats.lavaCore, true);
        lamps.push([px + 1, py + 1, bz + Math.floor(ph * 0.6)]);
    }

    buildStandardClouds(c, ['#4a3e40', '#705e5d', '#a6887c'], ['#42383a', '#635352', '#8f756b']);

    const petals = Array.from(
        { length: 20 },
        () => [fx + c.ri(-10, 32), fy + c.ri(-6, 30), c.ri(14, 24)] as [number, number, number],
    );
    const fireflies = Array.from({ length: 16 }, () => {
        const bx = fx + c.ri(0, 26);
        const by = fy + c.ri(0, 24);
        return [bx, by, (heightAt(bx, by) ?? 16) + c.ri(3, 12)] as [number, number, number];
    });
    const koi = calderaCenters.map(
        ([kx, ky]) => [kx, ky, (heightAt(kx, ky) ?? 15) - 1] as [number, number, number],
    );

    return {
        worldId: 'magma-forge',
        solid: c.solid,
        material: c.material,
        emissive: c.emissive,
        palette: c.palette,
        cloudMaterials: c.cloudIds,
        farCloudMaterials: c.farCloudIds,
        petals,
        glints: glints.slice(0, 40),
        lamps,
        fireflies,
        koi,
        voxelCount: c.countVoxels(),
    };
}
