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

function buildMirrorPool(c: VoxelCanvasBuilder, heightAt: HeightFn, mats: Record<string, number>) {
    const pool = { x: CX + 13, y: CY + 11, rx: 11, ry: 9 };
    const glints: Array<[number, number, number]> = [];
    for (let y = pool.y - pool.ry; y <= pool.y + pool.ry; y++) {
        for (let x = pool.x - pool.rx; x <= pool.x + pool.rx; x++) {
            if (((x - pool.x) / pool.rx) ** 2 + ((y - pool.y) / pool.ry) ** 2 > 1) continue;
            const h = heightAt(x, y);
            if (h === null) continue;
            for (let z = h - 2; z <= h + 1; z++) c.put(x, y, z, 0);
            c.put(x, y, h - 2, mats.slateTrim);
            c.put(x, y, h - 1, c.rnd() < 0.65 ? mats.mirrorGlint : mats.mirrorWater);
            if (c.rnd() < 0.16) glints.push([x, y, h - 1]);
        }
    }
    return { pool, glints };
}

function buildObservatoryDome(
    c: VoxelCanvasBuilder,
    heightAt: HeightFn,
    mats: Record<string, number>,
) {
    const tx = CX - 8;
    const ty = CY - 8;
    const tz = heightAt(tx, ty) ?? 18;
    c.cyl(tx, ty, tz, 9, 2, mats.marble2);
    c.cyl(tx, ty, tz + 2, 7, 10, mats.marble);
    c.cyl(tx, ty, tz + 12, 8, 1, mats.brass);
    for (let k = 0; k < 6; k++) {
        const dr = Math.max(2, Math.round(7 - k * 0.9));
        c.cyl(tx, ty, tz + 13 + k, dr, 1, k % 2 === 0 ? mats.slateTrim : mats.brass);
    }
    for (let step = 0; step < 9; step++) {
        c.box(tx + 3 + step, ty + 2 + Math.floor(step * 0.6), tz + 15 + step, 2, 2, 2, mats.brass);
    }
    c.box(tx + 12, ty + 7, tz + 24, 2, 2, 2, mats.lens, true);
    return { tx, ty, tz };
}

export function buildSkyObservatory(seedValue = 20261124): VoxelWorld {
    const c = createVoxelCanvas(seedValue);
    const marble = c.mat('#ded7c8');
    const marble2 = c.mat('#bdb4a2');
    const slateTrim = c.mat('#6c7a89');
    const cedar = c.mat('#6b4a3a');
    const brass = c.mat('#d9b252');
    const courtyardGrass = c.mat('#68ae6d');
    const mats = {
        marble,
        marble2,
        slateTrim,
        cedar,
        brass,
        gold: c.mat('#f5d77a', true),
        lens: c.mat('#99ecff', true),
        mirrorWater: c.mat('#4f8fa6'),
        mirrorGlint: c.mat('#8ed2e0'),
    };

    const heightAt: HeightFn = (x, y) => {
        const d = Math.hypot((x - CX) / R, (y - CY) / (R * 0.92));
        if (d > 1) return null;
        const terrace = d < 0.48 ? 2 : d < 0.78 ? 1 : 0;
        return Math.round(14 + terrace * 2 + Math.min(1, (1 - d) * 3.0) * 2);
    };

    for (let y = 0; y < 104; y++) {
        for (let x = 0; x < 104; x++) {
            const h = heightAt(x, y);
            if (h === null) continue;
            for (let z = 6; z <= h; z++) {
                const depth = h - z;
                const top = (x + y) % 5 === 0 ? courtyardGrass : marble;
                c.put(x, y, z, depth === 0 ? top : depth <= 2 ? marble2 : slateTrim);
            }
        }
    }
    // Note: keep helper imports referenced cleanly while preserving checkerboard terrace grass.
    void fillTerrainVolume;
    buildIslandUndercrust(c, slateTrim, marble2, cedar, brass);

    const { pool, glints } = buildMirrorPool(c, heightAt, mats);
    const { tx, ty, tz } = buildObservatoryDome(c, heightAt, mats);

    const lamps: Array<[number, number, number]> = [[tx + 12, ty + 7, tz + 24]];
    for (const [bx, by] of [
        [CX - 22, CY + 8],
        [CX + 18, CY - 16],
        [CX - 4, CY + 22],
        [CX + 4, CY - 24],
    ] as const) {
        const bz = heightAt(bx, by) ?? 15;
        c.box(bx - 1, by - 1, bz + 1, 3, 3, 4, marble2);
        c.put(bx, by, bz + 5, brass);
        c.put(bx, by, bz + 6, mats.gold, true);
        lamps.push([bx, by, bz + 6]);
    }

    buildStandardClouds(c, ['#b8c4c9', '#dce4e8', '#f7f3eb'], ['#a6b4ba', '#cad4d9', '#ebe5da']);

    const petals = Array.from(
        { length: 18 },
        () => [CX + c.ri(-28, 28), CY + c.ri(-26, 26), c.ri(26, 40)] as [number, number, number],
    );
    const fireflies = Array.from({ length: 16 }, (_, i) => {
        const angle = (i / 16) * Math.PI * 2;
        const rad = 11 + (i % 3) * 4;
        return [
            Math.round(tx + Math.cos(angle) * rad),
            Math.round(ty + Math.sin(angle) * rad),
            tz + 14 + (i % 5) * 2,
        ] as [number, number, number];
    });
    const koi: Array<[number, number, number]> = [
        [pool.x - 3, pool.y - 2, (heightAt(pool.x - 3, pool.y - 2) ?? 15) - 1],
        [pool.x + 3, pool.y + 2, (heightAt(pool.x + 3, pool.y + 2) ?? 15) - 1],
    ];

    return {
        worldId: 'sky-observatory',
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
