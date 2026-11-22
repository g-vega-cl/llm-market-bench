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

function carveBrookAndAqueduct(
    c: VoxelCanvasBuilder,
    heightAt: HeightFn,
    mats: Record<string, number>,
) {
    const glints: Array<[number, number, number]> = [];
    for (let t = -22; t <= 24; t++) {
        const bx = Math.round(CX + t * 0.85);
        const by = Math.round(CY + Math.sin(t * 0.14) * 4 + t * 0.42);
        for (let oy = -2; oy <= 2; oy++) {
            for (let ox = -2; ox <= 2; ox++) {
                const px = bx + ox;
                const py = by + oy;
                const h = heightAt(px, py);
                if (h === null) continue;
                for (let z = h - 2; z <= h + 1; z++) c.put(px, py, z, 0);
                c.put(px, py, h - 2, mats.graniteDark);
                c.put(px, py, h - 1, c.rnd() < 0.65 ? mats.waterHi : mats.water);
                if (c.rnd() < 0.18) glints.push([px, py, h - 1]);
            }
        }
    }
    for (let a = -10; a <= 10; a++) {
        const ax = CX - 6 + a;
        const ay = CY + 4 - Math.floor(a * 0.4);
        const bz = heightAt(ax, ay) ?? 15;
        c.box(ax, ay - 1, bz + 2, 1, 3, 1, mats.cedar);
        c.put(ax, ay, bz + 3, mats.waterHi);
        if (a % 5 === 0) c.box(ax, ay, bz - 1, 1, 1, 4, mats.cedarDark);
    }
    return glints;
}

function buildSanctuaryTreesAndLodge(
    c: VoxelCanvasBuilder,
    heightAt: HeightFn,
    mats: Record<string, number>,
) {
    const px0 = CX - 16;
    const py0 = CY - 14;
    const pz0 = heightAt(px0, py0) ?? 18;
    c.box(px0 - 5, py0 - 5, pz0, 11, 11, 2, mats.granite);
    c.box(px0 - 4, py0 - 4, pz0 + 2, 9, 9, 6, mats.cedar);
    c.box(px0 - 6, py0 - 6, pz0 + 8, 13, 13, 2, mats.cedarDark);
    c.box(px0 - 4, py0 - 4, pz0 + 10, 9, 9, 2, mats.pine);
    c.put(px0, py0 + 5, pz0 + 4, mats.lantern, true);
    c.put(px0 + 5, py0, pz0 + 4, mats.lantern, true);

    const trees: Array<[number, number, boolean]> = [
        [CX - 22, CY + 6, true],
        [CX + 18, CY - 16, false],
        [CX + 22, CY - 4, true],
        [CX + 10, CY + 20, false],
        [CX - 8, CY + 22, true],
    ];
    for (const [tx, ty, isPine] of trees) {
        const bz = heightAt(tx, ty) ?? 15;
        c.box(tx, ty, bz + 1, 2, 2, 6, mats.cedarDark);
        if (isPine) {
            c.cyl(tx, ty, bz + 5, 4, 2, mats.pine);
            c.cyl(tx, ty, bz + 7, 3, 2, mats.pineHi);
            c.cyl(tx, ty, bz + 9, 2, 2, mats.pine);
        } else {
            c.sphere(tx, ty, bz + 8, 4, mats.maple1);
            c.sphere(tx + 1, ty - 1, bz + 9, 3, mats.maple2);
            c.sphere(tx - 1, ty + 1, bz + 7, 2, mats.maple3);
        }
    }

    const extraLampZ = (heightAt(CX + 4, CY + 4) ?? 16) + 3;
    c.put(CX + 4, CY + 4, extraLampZ - 1, mats.cedarDark);
    c.put(CX + 4, CY + 4, extraLampZ, mats.lantern, true);
    return [
        [px0, py0 + 5, pz0 + 4],
        [px0 + 5, py0, pz0 + 4],
        [CX + 4, CY + 4, extraLampZ],
    ] as Array<[number, number, number]>;
}

export function buildCedarSanctuary(seedValue = 20261125): VoxelWorld {
    const c = createVoxelCanvas(seedValue);
    const mossTop = c.mat('#4e8255');
    const moss2 = c.mat('#3f6e47');
    const dirt = c.mat('#7d5e3e');
    const granite = c.mat('#8b867c');
    const graniteDark = c.mat('#68635b');
    const mats = {
        granite,
        graniteDark,
        cedar: c.mat('#785239'),
        cedarDark: c.mat('#543827'),
        pine: c.mat('#2f6142'),
        pineHi: c.mat('#44855b'),
        maple1: c.mat('#d97d36'),
        maple2: c.mat('#ebb054'),
        maple3: c.mat('#c24e2b'),
        water: c.mat('#5da6ba'),
        waterHi: c.mat('#8ad0df'),
        lantern: c.mat('#ffcf6e', true),
    };

    const heightAt: HeightFn = (x, y) => {
        const d = Math.hypot((x - CX) / R, (y - CY) / (R * 0.92));
        if (d > 1) return null;
        const slope = Math.max(0, (CX - x) * 0.08 + (CY - y) * 0.05);
        const ridge = Math.cos(x * 0.14) * Math.sin(y * 0.14) * 1.4;
        return Math.round(14 + slope + ridge + Math.min(1, (1 - d) * 3.1) * 3);
    };

    fillTerrainVolume(c, heightAt, (depth) => {
        if (depth === 0) return c.rnd() < 0.55 ? mossTop : moss2;
        return depth <= 2 ? dirt : depth <= 5 ? granite : graniteDark;
    });
    buildIslandUndercrust(c, graniteDark, granite, mats.cedarDark, mats.pine);

    const glints = carveBrookAndAqueduct(c, heightAt, mats);
    const lamps = buildSanctuaryTreesAndLodge(c, heightAt, mats);
    buildStandardClouds(c, ['#9bb0a7', '#c5d4cb', '#ede8da'], ['#889e95', '#b3c4bb', '#ded9cb']);

    const petals = Array.from(
        { length: 20 },
        () => [CX + c.ri(-26, 26), CY + c.ri(-24, 24), c.ri(22, 36)] as [number, number, number],
    );
    const fireflies = Array.from({ length: 16 }, () => {
        const fx = CX + c.ri(-22, 22);
        const fy = CY + c.ri(-20, 20);
        return [fx, fy, (heightAt(fx, fy) ?? 16) + c.ri(3, 10)] as [number, number, number];
    });
    const koi: Array<[number, number, number]> = [
        [CX - 2, CY - 1, (heightAt(CX - 2, CY - 1) ?? 15) - 1],
        [CX + 10, CY + 6, (heightAt(CX + 10, CY + 6) ?? 15) - 1],
    ];

    return {
        worldId: 'cedar-sanctuary',
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
