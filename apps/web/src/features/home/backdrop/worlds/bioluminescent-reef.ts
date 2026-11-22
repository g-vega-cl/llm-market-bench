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

function buildLagoonPool(c: VoxelCanvasBuilder, heightAt: HeightFn, mats: Record<string, number>) {
    const lagoon = { x: CX + 4, y: CY + 4, rx: 17, ry: 12 };
    const glints: Array<[number, number, number]> = [];
    for (let y = lagoon.y - lagoon.ry - 2; y <= lagoon.y + lagoon.ry + 2; y++) {
        for (let x = lagoon.x - lagoon.rx - 2; x <= lagoon.x + lagoon.rx + 2; x++) {
            if (((x - lagoon.x) / lagoon.rx) ** 2 + ((y - lagoon.y) / lagoon.ry) ** 2 > 1) continue;
            const h = heightAt(x, y);
            if (h === null) continue;
            for (let z = h - 3; z <= h + 1; z++) c.put(x, y, z, 0);
            c.put(x, y, h - 3, mats.deepWater);
            c.put(x, y, h - 2, mats.water);
            const surface = c.rnd() < 0.28 ? mats.bioWater : mats.water;
            c.put(x, y, h - 1, surface, surface === mats.bioWater);
            if (c.rnd() < 0.14) glints.push([x, y, h - 1]);
        }
    }
    return { lagoon, glints };
}

function buildCrystalSpires(
    c: VoxelCanvasBuilder,
    heightAt: HeightFn,
    mats: Record<string, number>,
) {
    const sites: Array<[number, number, number, number]> = [
        [CX - 18, CY - 14, 15, 3],
        [CX - 11, CY - 20, 12, 2],
        [CX - 23, CY - 5, 11, 2],
        [CX + 20, CY - 16, 13, 3],
        [CX - 16, CY + 16, 9, 2],
    ];
    const lamps: Array<[number, number, number]> = [];
    for (const [sx0, sy0, sh, sr] of sites) {
        const bz = heightAt(sx0, sy0) ?? 15;
        for (let k = 0; k < sh; k++) {
            const rCur = k > sh * 0.65 ? Math.max(1, sr - 1) : sr;
            const m =
                k >= sh - 3 ? mats.crystalGlow : k % 3 === 0 ? mats.amethystHi : mats.amethyst;
            c.cyl(sx0, sy0, bz + k, rCur, 1, m, m === mats.crystalGlow);
        }
        lamps.push([sx0, sy0, bz + sh - 1]);
    }
    return { sites, lamps };
}

export function buildBioluminescentReef(seedValue = 20261123): VoxelWorld {
    const c = createVoxelCanvas(seedValue);
    const slate = c.mat('#2e3d4c');
    const slate2 = c.mat('#3d5266');
    const reefStone = c.mat('#4e687a');
    const mats = {
        deepWater: c.mat('#19414f'),
        water: c.mat('#276a7d'),
        bioWater: c.mat('#46b8b0', true),
        amethyst: c.mat('#6c58c4'),
        amethystHi: c.mat('#8f7ef0'),
        crystalGlow: c.mat('#6df2d6', true),
        coralPink: c.mat('#e36d8d'),
        coralPeach: c.mat('#f09d97'),
        kelp: c.mat('#34806d'),
    };

    const heightAt: HeightFn = (x, y) => {
        const d = Math.hypot((x - CX) / R, (y - CY) / (R * 0.92));
        if (d > 1) return null;
        const wave = Math.sin(x * 0.19) * Math.cos(y * 0.19) * 1.8;
        return Math.round(14 + wave + Math.min(1, (1 - d) * 3.0) * 3);
    };

    fillTerrainVolume(c, heightAt, (depth) => {
        if (depth === 0) return c.rnd() < 0.55 ? reefStone : slate2;
        return depth <= 2 ? slate2 : slate;
    });
    buildIslandUndercrust(c, slate, slate2, mats.amethyst, mats.crystalGlow);

    const { lagoon, glints } = buildLagoonPool(c, heightAt, mats);
    const { sites, lamps } = buildCrystalSpires(c, heightAt, mats);

    for (let i = 0; i < 22; i++) {
        const a = (i / 22) * Math.PI * 2;
        const rx = Math.round(lagoon.x + Math.cos(a) * (lagoon.rx + 2));
        const ry = Math.round(lagoon.y + Math.sin(a) * (lagoon.ry + 2));
        const h = heightAt(rx, ry);
        if (h === null) continue;
        const coralMat =
            i % 3 === 0 ? mats.crystalGlow : i % 2 === 0 ? mats.coralPink : mats.coralPeach;
        const height = c.ri(2, 4);
        for (let k = 1; k <= height; k++) {
            c.put(rx, ry, h + k, k === 1 ? mats.kelp : coralMat, coralMat === mats.crystalGlow);
        }
    }

    buildStandardClouds(c, ['#486673', '#68919e', '#9ac4cc'], ['#3c5661', '#597d8a', '#85adb5']);

    const petals = Array.from(
        { length: 20 },
        () =>
            [lagoon.x + c.ri(-18, 18), lagoon.y + c.ri(-14, 14), c.ri(14, 24)] as [
                number,
                number,
                number,
            ],
    );
    const fireflies = Array.from({ length: 16 }, (_, i) => {
        const site = sites[i % sites.length];
        return [site[0] + c.ri(-6, 6), site[1] + c.ri(-6, 6), c.ri(22, 34)] as [
            number,
            number,
            number,
        ];
    });
    const koi: Array<[number, number, number]> = [
        [lagoon.x - 5, lagoon.y - 2, (heightAt(lagoon.x - 5, lagoon.y - 2) ?? 14) - 1],
        [lagoon.x + 5, lagoon.y + 3, (heightAt(lagoon.x + 5, lagoon.y + 3) ?? 14) - 1],
    ];

    return {
        worldId: 'bioluminescent-reef',
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
