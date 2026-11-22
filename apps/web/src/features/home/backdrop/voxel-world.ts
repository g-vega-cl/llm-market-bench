/**
 * Shared 3D Voxel grid, procedural shape primitives, world metadata, and
 * cached face extraction used by all living-scene diorama worlds.
 */

export const SX = 104;
export const SY = 104;
export const SZ = 72;
export const CX = SX >> 1;
export const CY = SY >> 1;
export const R = 36;

export const WORLD_IDS = [
    'sakura-garden',
    'magma-forge',
    'bioluminescent-reef',
    'sky-observatory',
    'cedar-sanctuary',
] as const;

export type WorldId = (typeof WORLD_IDS)[number];

export const PARTICLE_MODES = ['sakura', 'embers', 'spores', 'star-runes', 'cedar-mist'] as const;

export type ParticleMode = (typeof PARTICLE_MODES)[number];

export interface WorldMetadata {
    id: WorldId;
    label: string;
    shortLabel: string;
    particleMode: ParticleMode;
    glowRgb: [number, number, number];
    description: string;
}

export const WORLD_METADATA: Record<WorldId, WorldMetadata> = {
    'sakura-garden': {
        id: 'sakura-garden',
        label: 'Zen Sakura Garden',
        shortLabel: 'Sakura Garden',
        particleMode: 'sakura',
        glowRgb: [248, 192, 98],
        description:
            'Levitating matcha garden with sakura blossoms, koi pond ripples, and dusk fireflies.',
    },
    'magma-forge': {
        id: 'magma-forge',
        label: 'Magma Forge',
        shortLabel: 'Magma Forge',
        particleMode: 'embers',
        glowRgb: [255, 118, 42],
        description:
            'Volcanic basalt anvil island with molten lava cascades, rising embers, and furnace sparks.',
    },
    'bioluminescent-reef': {
        id: 'bioluminescent-reef',
        label: 'Bioluminescent Reef',
        shortLabel: 'Bio Reef',
        particleMode: 'spores',
        glowRgb: [96, 244, 210],
        description:
            'Midnight coral & amethyst spire basin with rising bioluminescent spores and tide rings.',
    },
    'sky-observatory': {
        id: 'sky-observatory',
        label: 'Sky Observatory',
        shortLabel: 'Observatory',
        particleMode: 'star-runes',
        glowRgb: [248, 224, 152],
        description:
            'Terraced marble citadel with brass armillary dome, mirror pool, and orbiting star-runes.',
    },
    'cedar-sanctuary': {
        id: 'cedar-sanctuary',
        label: 'Cedar Sanctuary',
        shortLabel: 'Cedar Ridge',
        particleMode: 'cedar-mist',
        glowRgb: [248, 198, 112],
        description:
            'Highland cypress ridge with timber aqueduct, autumn maples, drifting valley mist, and falling leaves.',
    },
};

export function isValidWorldId(value: unknown): value is WorldId {
    return typeof value === 'string' && (WORLD_IDS as readonly string[]).includes(value);
}

export interface Rgb {
    r: number;
    g: number;
    b: number;
}

export interface Material {
    color: Rgb;
    glow: boolean;
}

export interface WorldFaces {
    /** Visible island faces sorted back-to-front: [sortKey, x, y, z, face, idx, ao]. */
    island: Array<[number, number, number, number, number, number, number]>;
    /** High-altitude 3D cloud slab faces (far parallax plane). */
    cloudsFar: Array<[number, number, number, number, number, number, number]>;
    /** Mid/lower-altitude perimeter 3D cloud slab faces (near parallax plane). */
    cloudsNear: Array<[number, number, number, number, number, number, number]>;
}

/** Light render payload kept in cache after releasing raw `solid`/`emissive` buffers. */
export interface RenderableWorld {
    worldId: WorldId;
    material: Uint8Array;
    palette: Material[];
    cloudMaterials: number[];
    farCloudMaterials: number[];
    /** Falling petals / sparks / drifting spores / falling autumn leaves. */
    petals: Array<[number, number, number]>;
    /** Reflective water, magma, or mirror-pool surface glints. */
    glints: Array<[number, number, number]>;
    /** Glowing beacons, lanterns, furnace hearts, or crystal tips. */
    lamps: Array<[number, number, number]>;
    /** Hovering/orbiting secondary particles (fireflies, spores, runes, wisps). */
    fireflies: Array<[number, number, number]>;
    /** Expanding isometric surface ripple anchors (koi, caldera, tide, prism, brook). */
    koi: Array<[number, number, number]>;
    voxelCount: number;
}

export interface VoxelWorld extends RenderableWorld {
    solid: Uint8Array;
    emissive: Uint8Array;
}

export function stripWorldBuffers(world: VoxelWorld): RenderableWorld {
    return {
        worldId: world.worldId,
        material: world.material,
        palette: world.palette,
        cloudMaterials: world.cloudMaterials,
        farCloudMaterials: world.farCloudMaterials,
        petals: world.petals,
        glints: world.glints,
        lamps: world.lamps,
        fireflies: world.fireflies,
        koi: world.koi,
        voxelCount: world.voxelCount,
    };
}

export const hexToRgb = (hex: string): Rgb => {
    const n = Number.parseInt(hex.slice(1), 16);
    return { r: (n >> 16) & 255, g: (n >> 8) & 255, b: n & 255 };
};

export interface VoxelCanvasBuilder {
    rnd: () => number;
    ri: (a: number, b: number) => number;
    mat: (hex: string, glow?: boolean) => number;
    cloudMat: (hex: string, far?: boolean) => number;
    palette: Material[];
    cloudIds: number[];
    farCloudIds: number[];
    solid: Uint8Array;
    material: Uint8Array;
    emissive: Uint8Array;
    inside: (x: number, y: number, z: number) => boolean;
    filled: (x: number, y: number, z: number) => boolean;
    put: (x: number, y: number, z: number, m: number, glow?: boolean) => void;
    box: (
        x: number,
        y: number,
        z: number,
        w: number,
        d: number,
        h: number,
        m: number,
        glow?: boolean,
    ) => void;
    cyl: (
        cx: number,
        cy: number,
        z0: number,
        r: number,
        h: number,
        m: number,
        glow?: boolean,
    ) => void;
    sphere: (cx: number, cy: number, cz: number, r: number, m: number, glow?: boolean) => void;
    cloudSlab: (
        x0: number,
        y0: number,
        z0: number,
        w: number,
        d: number,
        h: number,
        mats: { near: [number, number, number]; far: [number, number, number] },
        crown?: { dx: number; dy: number; w: number; d: number },
        plane?: 'far' | 'near',
    ) => void;
    countVoxels: () => number;
}

function paintCloudRegion(
    filled: (x: number, y: number, z: number) => boolean,
    put: (x: number, y: number, z: number, m: number) => void,
    x0: number,
    y0: number,
    z0: number,
    w: number,
    d: number,
    matId: number,
) {
    for (let j = 0; j < d; j++) {
        for (let i = 0; i < w; i++) {
            if (!filled(x0 + i, y0 + j, z0)) put(x0 + i, y0 + j, z0, matId);
        }
    }
}

export function createVoxelCanvas(seedValue: number): VoxelCanvasBuilder {
    let seed = seedValue >>> 0;
    const rnd = () => {
        seed = (seed + 0x6d2b79f5) >>> 0;
        let t = seed;
        t = Math.imul(t ^ (t >>> 15), t | 1);
        t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
        return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
    const ri = (a: number, b: number) => a + Math.floor(rnd() * (b - a + 1));

    const palette: Material[] = [];
    const cloudIds: number[] = [];
    const farCloudIds: number[] = [];
    const mat = (hex: string, glow = false) => {
        palette.push({ color: hexToRgb(hex), glow });
        return palette.length;
    };
    const cloudMat = (hex: string, far = false) => {
        const id = mat(hex);
        cloudIds.push(id);
        if (far) farCloudIds.push(id);
        return id;
    };

    const solid = new Uint8Array(SX * SY * SZ);
    const material = new Uint8Array(SX * SY * SZ);
    const emissive = new Uint8Array(SX * SY * SZ);
    const at = (x: number, y: number, z: number) => (z * SY + y) * SX + x;
    const inside = (x: number, y: number, z: number) =>
        x >= 0 && x < SX && y >= 0 && y < SY && z >= 0 && z < SZ;
    const filled = (x: number, y: number, z: number) => inside(x, y, z) && solid[at(x, y, z)] === 1;

    function put(x: number, y: number, z: number, m: number, glow = false) {
        const px = Math.round(x);
        const py = Math.round(y);
        const pz = Math.round(z);
        if (!inside(px, py, pz)) return;
        const i = at(px, py, pz);
        solid[i] = m === 0 ? 0 : 1;
        material[i] = m;
        emissive[i] = m !== 0 && glow ? 1 : 0;
    }

    function box(
        x: number,
        y: number,
        z: number,
        w: number,
        d: number,
        h: number,
        m: number,
        glow = false,
    ) {
        for (let k = 0; k < h; k++) {
            for (let j = 0; j < d; j++) {
                for (let i = 0; i < w; i++) put(x + i, y + j, z + k, m, glow);
            }
        }
    }

    function cyl(
        cx: number,
        cy: number,
        z0: number,
        r: number,
        h: number,
        m: number,
        glow = false,
    ) {
        for (let k = 0; k < h; k++) {
            for (let y = -r; y <= r; y++) {
                for (let x = -r; x <= r; x++) {
                    if (x * x + y * y <= r * r + r * 0.6) put(cx + x, cy + y, z0 + k, m, glow);
                }
            }
        }
    }

    function sphere(cx: number, cy: number, cz: number, r: number, m: number, glow = false) {
        const R2 = Math.ceil(r);
        for (let z = -R2; z <= R2; z++) {
            for (let y = -R2; y <= R2; y++) {
                for (let x = -R2; x <= R2; x++) {
                    if (x * x + y * y + z * z <= r * r + r * 0.8)
                        put(cx + x, cy + y, cz + z, m, glow);
                }
            }
        }
    }

    function cloudSlab(
        x0: number,
        y0: number,
        z0: number,
        w: number,
        d: number,
        h: number,
        mats: { near: [number, number, number]; far: [number, number, number] },
        crown?: { dx: number; dy: number; w: number; d: number },
        plane: 'far' | 'near' = 'near',
    ) {
        const bx = Math.min(Math.max(x0, 2), SX - w - 3);
        const by = Math.min(Math.max(y0, 2), SY - d - 3);
        const bz = Math.min(Math.max(z0, 2), SZ - h - (crown ? 4 : 3));
        const [undersideMat, midMat, topMat] = plane === 'far' ? mats.far : mats.near;

        for (let k = 0; k < h; k++) {
            const matId = k === 0 ? undersideMat : k === h - 1 ? topMat : midMat;
            paintCloudRegion(filled, put, bx, by, bz + k, w, d, matId);
        }
        if (crown) {
            paintCloudRegion(
                filled,
                put,
                bx + crown.dx,
                by + crown.dy,
                bz + h,
                crown.w,
                crown.d,
                topMat,
            );
        }
    }

    const countVoxels = () => {
        let count = 0;
        for (let i = 0; i < solid.length; i++) if (solid[i]) count++;
        return count;
    };

    return {
        rnd,
        ri,
        mat,
        cloudMat,
        palette,
        cloudIds,
        farCloudIds,
        solid,
        material,
        emissive,
        inside,
        filled,
        put,
        box,
        cyl,
        sphere,
        cloudSlab,
        countVoxels,
    };
}

function solidAtGrid(solid: Uint8Array, x: number, y: number, z: number): boolean {
    if (x < 0 || x >= SX || y < 0 || y >= SY || z < 0 || z >= SZ) return false;
    return solid[(z * SY + y) * SX + x] === 1;
}

function computeFaceOcclusion(
    solid: Uint8Array,
    x: number,
    y: number,
    z: number,
    face: number,
): number {
    let n = 0;
    if (face === 0) {
        if (solidAtGrid(solid, x + 1, y, z + 1)) n++;
        if (solidAtGrid(solid, x - 1, y, z + 1)) n++;
        if (solidAtGrid(solid, x, y + 1, z + 1)) n++;
        if (solidAtGrid(solid, x, y - 1, z + 1)) n++;
        return 1 - n * 0.055;
    }
    if (face === 1) {
        if (solidAtGrid(solid, x, y + 1, z + 1)) n++;
        if (solidAtGrid(solid, x, y + 1, z - 1)) n++;
        if (solidAtGrid(solid, x - 1, y + 1, z)) n++;
        return 1 - n * 0.075;
    }
    if (solidAtGrid(solid, x + 1, y, z + 1)) n++;
    if (solidAtGrid(solid, x + 1, y, z - 1)) n++;
    if (solidAtGrid(solid, x + 1, y + 1, z)) n++;
    return 1 - n * 0.075;
}

function collectVoxelFaces(
    solid: Uint8Array,
    x: number,
    y: number,
    z: number,
    idx: number,
    bucket: WorldFaces['island'],
) {
    const key = x + y + z;
    if (!solidAtGrid(solid, x, y, z + 1)) {
        bucket.push([key, x, y, z, 0, idx, computeFaceOcclusion(solid, x, y, z, 0)]);
    }
    if (!solidAtGrid(solid, x, y + 1, z)) {
        bucket.push([key, x, y, z, 1, idx, computeFaceOcclusion(solid, x, y, z, 1)]);
    }
    if (!solidAtGrid(solid, x + 1, y, z)) {
        bucket.push([key, x, y, z, 2, idx, computeFaceOcclusion(solid, x, y, z, 2)]);
    }
}

export function extractWorldFaces(world: VoxelWorld): WorldFaces {
    const cloudSet = new Set(world.cloudMaterials);
    const farCloudSet = new Set(world.farCloudMaterials);
    const island: WorldFaces['island'] = [];
    const cloudsFar: WorldFaces['cloudsFar'] = [];
    const cloudsNear: WorldFaces['cloudsNear'] = [];

    for (let z = 0; z < SZ; z++) {
        for (let y = 0; y < SY; y++) {
            for (let x = 0; x < SX; x++) {
                const i = (z * SY + y) * SX + x;
                if (!world.solid[i]) continue;
                const matId = world.material[i];
                const bucket = !cloudSet.has(matId)
                    ? island
                    : farCloudSet.has(matId)
                      ? cloudsFar
                      : cloudsNear;
                collectVoxelFaces(world.solid, x, y, z, i, bucket);
            }
        }
    }

    island.sort((a, b) => a[0] - b[0]);
    cloudsFar.sort((a, b) => a[0] - b[0]);
    cloudsNear.sort((a, b) => a[0] - b[0]);

    return { island, cloudsFar, cloudsNear };
}
