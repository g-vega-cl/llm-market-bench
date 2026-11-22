/**
 * Shared 3D Voxel grid, procedural shape primitives, Cedar Sanctuary metadata,
 * and cached face extraction used by the panoramic living-scene backdrop.
 */

export const SX = 144;
export const SY = 144;
export const SZ = 64;
export const CX = SX >> 1;
export const CY = SY >> 1;
export const RU = 84;
export const RV = 42;

export const CEDAR_WORLD_ID = 'cedar-sanctuary' as const;
export type WorldId = typeof CEDAR_WORLD_ID;

export interface CedarWorldMetadata {
    id: WorldId;
    label: string;
    shortLabel: string;
    glowRgb: [number, number, number];
    description: string;
}

export const CEDAR_WORLD_META: CedarWorldMetadata = {
    id: CEDAR_WORLD_ID,
    label: 'Cedar Sanctuary',
    shortLabel: 'Cedar Ridge',
    glowRgb: [248, 198, 112],
    description:
        'Panoramic highland cedar ridge with timber sanctuary lodge, aqueduct trestle, brook bridge, autumn maples, drifting mist, and falling leaves.',
};

/** Converts camera-aligned `(u, v)` offsets into integer grid `[x, y]` coordinates. */
export function uvToGrid(u: number, v: number): [number, number] {
    return [Math.round(CX + (u + v) * 0.5), Math.round(CY + (v - u) * 0.5)];
}

/** Converts integer grid `(x, y)` coordinates into camera-aligned `(u, v)` offsets. */
export function gridToUv(x: number, y: number): [number, number] {
    const dx = x - CX;
    const dy = y - CY;
    return [dx - dy, dx + dy];
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
    /** Material id -> cloud group index, so each cloud can be baked and drifted on its own. */
    cloudGroupOf: Map<number, number>;
    /** Falling autumn cedar & maple leaves. */
    petals: Array<[number, number, number]>;
    /** Reflective brook & waterfall glints. */
    glints: Array<[number, number, number]>;
    /** Glowing sanctuary windows & path lanterns. */
    lamps: Array<[number, number, number]>;
    /** Dusk & night fireflies hovering over the valley. */
    fireflies: Array<[number, number, number]>;
    /** Expanding isometric surface ripple anchors in the brook & cascade pool. */
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
        cloudGroupOf: world.cloudGroupOf,
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
    cloudMat: (hex: string, far?: boolean, group?: number) => number;
    palette: Material[];
    cloudIds: number[];
    farCloudIds: number[];
    cloudGroupOf: Map<number, number>;
    solid: Uint8Array;
    material: Uint8Array;
    emissive: Uint8Array;
    inside: (x: number, y: number, z: number) => boolean;
    filled: (x: number, y: number, z: number) => boolean;
    put: (x: number, y: number, z: number, m: number, glow?: boolean) => void;
    putUV: (u: number, v: number, z: number, m: number, glow?: boolean) => void;
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
    cloudPuff: (
        u: number,
        v: number,
        z0: number,
        halfU: number,
        halfV: number,
        mats: { near: [number, number, number]; far: [number, number, number] },
        plane?: 'far' | 'near',
    ) => void;
    countVoxels: () => number;
}

/**
 * Deterministic value noise in `[-0.5, 0.5]` used to break cloud tier edges into
 * 1–2 voxel steps so no outline run reads as a straight rectangle edge.
 */
function cloudEdgeNoise(x: number, y: number, z: number): number {
    let h = (x * 374761393 + y * 668265263 + z * 2246822519) >>> 0;
    h = Math.imul(h ^ (h >>> 13), 1274126177) >>> 0;
    return ((h ^ (h >>> 16)) >>> 0) / 4294967296 - 0.5;
}

/** Highest lobe field value at a camera-space `(u, v)` sample; `> 0` means solid cloud. */
function cloudLobeField(
    cellU: number,
    cellV: number,
    lobes: Array<[number, number, number]>,
    centerU: number,
    centerV: number,
    radiusU: number,
    radiusV: number,
): number {
    let field = -1;
    for (const [lobeU, lobeV, lobeR] of lobes) {
        const du = (cellU - (centerU + lobeU * radiusU)) / (radiusU * lobeR);
        const dv = (cellV - (centerV + lobeV * radiusV)) / (radiusV * lobeR);
        field = Math.max(field, 1 - du * du - dv * dv);
    }
    return field;
}

/** Grid-space bounding box of a rotated-isometric cloud tier, padded two voxels for ragged edges. */
function cloudTierBounds(centerU: number, centerV: number, radiusU: number, radiusV: number) {
    const corners = [
        uvToGrid(centerU - radiusU - 2, centerV - radiusV - 2),
        uvToGrid(centerU + radiusU + 2, centerV + radiusV + 2),
        uvToGrid(centerU - radiusU - 2, centerV + radiusV + 2),
        uvToGrid(centerU + radiusU + 2, centerV - radiusV - 2),
    ];
    return {
        minX: Math.min(...corners.map((c) => c[0])),
        maxX: Math.max(...corners.map((c) => c[0])),
        minY: Math.min(...corners.map((c) => c[1])),
        maxY: Math.max(...corners.map((c) => c[1])),
    };
}

/** Builds the lobe cluster shared by every tier of one cloud, so the steps nest. */
function cloudLobes(
    rnd: () => number,
    ri: (a: number, b: number) => number,
): Array<[number, number, number]> {
    const lobes: Array<[number, number, number]> = [];
    const lobeCount = ri(2, 3);
    for (let i = 0; i < lobeCount; i++) {
        const angle = rnd() * Math.PI * 2;
        // Lobe centre (<=0.30R) plus lobe radius (<=0.72R) keeps the union within ~1.02R.
        const spread = i === 0 ? 0 : 0.16 + rnd() * 0.14;
        lobes.push([Math.cos(angle) * spread, Math.sin(angle) * spread, 0.5 + rnd() * 0.22]);
    }
    return lobes;
}

/** Rasterizes one flat cloud tier of the given height from the lobe field. */
function paintCloudTier(args: {
    put: (x: number, y: number, z: number, m: number) => void;
    rnd: () => number;
    u: number;
    v: number;
    halfU: number;
    halfV: number;
    lobes: Array<[number, number, number]>;
    z0: number;
    tier: { scale: number; height: number; mat: number; jitter: number; flatBase?: boolean };
}) {
    const { put, rnd, u, v, halfU, halfV, lobes, z0, tier } = args;
    // `u` and `v` only exist on cells of equal parity, so snapping the centre to
    // that lattice guarantees every tier keeps a solid core instead of falling between samples.
    const centerU = Math.round(u + (rnd() - 0.5) * tier.jitter);
    const centerV = Math.round(v + (rnd() - 0.5) * tier.jitter);
    const parityFix = (centerU - centerV) & 1;
    const cv = centerV + parityFix;
    const radiusU = halfU * tier.scale;
    const radiusV = halfV * tier.scale;
    const bounds = cloudTierBounds(centerU, cv, radiusU, radiusV);

    for (let y = bounds.minY; y <= bounds.maxY; y++) {
        for (let x = bounds.minX; x <= bounds.maxX; x++) {
            const [cellU, cellV] = gridToUv(x, y);
            const field = cloudLobeField(cellU, cellV, lobes, centerU, cv, radiusU, radiusV);
            for (let k = 0; k < tier.height; k++) {
                // Per-layer noise jitters each course by a voxel, so tiers never stack as flat
                // plates; the bottom course stays on the pure field so the underside is flat.
                const erode = tier.flatBase && k === 0 ? 0 : 0.28;
                if (field + cloudEdgeNoise(x >> 1, y >> 1, z0 + k) * erode <= 0) continue;
                put(x, y, z0 + k, tier.mat);
            }
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
    const cloudGroupOf = new Map<number, number>();
    const cloudMat = (hex: string, far = false, group = 0) => {
        const id = mat(hex);
        cloudIds.push(id);
        cloudGroupOf.set(id, group);
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

    function putUV(u: number, v: number, z: number, m: number, glow = false) {
        const [gx, gy] = uvToGrid(u, v);
        put(gx, gy, z, m, glow);
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

    /**
     * Carves one flat-bottomed cloud as a cluster of 3–4 overlapping puffs, each with
     * its own two-step dome at a different height, so the skyline is a series of humps
     * rather than one terraced plateau.
     */
    function cloudPuff(
        u: number,
        v: number,
        z0: number,
        halfU: number,
        halfV: number,
        mats: { near: [number, number, number]; far: [number, number, number] },
        plane: 'far' | 'near' = 'near',
    ) {
        const [underMat, midMat, topMat] = plane === 'far' ? mats.far : mats.near;
        if (!(halfU > 0) || !(halfV > 0) || !Number.isFinite(z0)) return;
        // Every column drops to the base plate on the under→mid ramp (never the cell's own
        // material, or a capped column would flood itself bright), and never displaces terrain.
        const putColumn = (x: number, y: number, z: number, m: number) => {
            for (let zz = z0; zz <= z; zz++) {
                if (filled(x, y, zz)) continue;
                put(x, y, zz, zz === z ? m : zz === z0 ? underMat : midMat);
            }
        };

        const puffCount = ri(3, 4);
        for (let i = 0; i < puffCount; i++) {
            const along = (i / (puffCount - 1)) * 2 - 1;
            const pu = u + along * halfU * 0.62 + (rnd() - 0.5) * 1.2;
            const pv = v + (rnd() - 0.5) * halfV * 0.5;
            const radiusU = halfU * (0.42 + rnd() * 0.2);
            const radiusV = halfV * (0.55 + rnd() * 0.25);
            const lift = i === 0 ? 0 : ri(0, 1);
            const lobes = cloudLobes(rnd, ri);
            const courses = [
                { scale: 1, height: 2, mat: midMat, jitter: 0, flatBase: lift === 0 },
                { scale: 0.72, height: 1, mat: topMat, jitter: 0.8 },
            ];
            let z = z0 + lift;
            for (const tier of courses) {
                paintCloudTier({
                    put: putColumn,
                    rnd,
                    u: pu,
                    v: pv,
                    halfU: radiusU,
                    halfV: radiusV,
                    lobes,
                    z0: z,
                    tier,
                });
                z += tier.height;
            }
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
        cloudGroupOf,
        solid,
        material,
        emissive,
        inside,
        filled,
        put,
        putUV,
        box,
        cyl,
        sphere,
        cloudPuff,
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
