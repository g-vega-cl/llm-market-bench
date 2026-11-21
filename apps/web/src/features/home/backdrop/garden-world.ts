/**
 * The garden island, as voxel data.
 *
 * Pure and deterministic: same seed, same world, every load and every test.
 * Nothing here touches the DOM — the renderer in GardenBackdrop.tsx turns this
 * into two painted layers, and the tests can assert on it directly.
 */

export const SX = 104;
export const SY = 104;
export const SZ = 72;
export const CX = SX >> 1;
export const CY = SY >> 1;
export const R = 36;

export const POND = { x: CX + 15, y: CY + 12, rx: 14, ry: 10 };

export interface Rgb {
    r: number;
    g: number;
    b: number;
}

export interface Material {
    color: Rgb;
    glow: boolean;
}

export interface GardenWorld {
    /** 1 where a voxel exists. */
    solid: Uint8Array;
    /** 1-based index into `palette`; 0 for air. */
    material: Uint8Array;
    emissive: Uint8Array;
    palette: Material[];
    /** Material ids the renderer must draw in the cloud layer. */
    cloudMaterials: number[];
    /** World-space anchors the renderer animates against. */
    petals: Array<[number, number, number]>;
    glints: Array<[number, number, number]>;
    lamps: Array<[number, number, number]>;
    voxelCount: number;
}

const hexToRgb = (hex: string): Rgb => {
    const n = Number.parseInt(hex.slice(1), 16);
    return { r: (n >> 16) & 255, g: (n >> 8) & 255, b: n & 255 };
};

export function buildGarden(seedValue = 20261121): GardenWorld {
    let seed = seedValue >>> 0;
    // mulberry32: 2^32 period, so 100k draws never repeat the way the old LCG did.
    const rnd = () => {
        seed = (seed + 0x6d2b79f5) >>> 0;
        let t = seed;
        t = Math.imul(t ^ (t >>> 15), t | 1);
        t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
        return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
    const ri = (a: number, b: number) => a + Math.floor(rnd() * (b - a + 1));

    /* materials ---------------------------------------------------------- */
    const palette: Material[] = [];
    const mat = (hex: string, glow = false) => {
        palette.push({ color: hexToRgb(hex), glow });
        return palette.length;
    };

    const GRASS = mat('#7cc47f');
    const GRASS2 = mat('#68ae6d');
    const GRASS3 = mat('#54975c');
    const MOSS = mat('#5f8f52');
    const FLOWER1 = mat('#f6d365');
    const FLOWER2 = mat('#f4978e');
    const FLOWER3 = mat('#c9a7eb');
    const DIRT = mat('#8a6a45');
    const DIRT2 = mat('#6f5436');
    const ROOT = mat('#5a4530');
    const STONE = mat('#b3ab98');
    const STONE2 = mat('#948d7c');
    const STONE3 = mat('#8b867c');
    const STONE4 = mat('#6e6a62');
    const SAND = mat('#c3b795');
    const RED = mat('#c8452f');
    const RED2 = mat('#a33524');
    const RED3 = mat('#7d2718');
    const WOOD = mat('#8a6247');
    const WOOD2 = mat('#6b4a3a');
    const WOOD3 = mat('#4d3628');
    const TRUNK = mat('#6b4a3a');
    const TRUNK2 = mat('#54382c');
    const BLOSSOM = mat('#f9c6d9');
    const BLOSSOM2 = mat('#f2a0bf');
    const BLOSSOM3 = mat('#fde6ee');
    const BLOSSOM4 = mat('#e07fa6');
    const LEAF2 = mat('#4fa86a');
    const LEAF3 = mat('#2f7048');
    const BAMBOO = mat('#6fae5c');
    const BAMBOO2 = mat('#8ec974');
    const BAMBOO3 = mat('#4d8340');
    const WATER = mat('#6bb0c4');
    const WATER2 = mat('#8ed2e0');
    const WATER3 = mat('#4f8ea3');
    const PATH = mat('#a49d8b');
    const PATH2 = mat('#8b8574');
    const LANTERN = mat('#ffcf6e', true);
    const Koi = mat('#e8734a');
    const Koi2 = mat('#f7f2e4');
    const cloudIds: number[] = [];
    const cloudMat = (hex: string) => {
        const id = mat(hex);
        cloudIds.push(id);
        return id;
    };
    const CLOUD = cloudMat('#cfdcd6');
    const CLOUD2 = cloudMat('#b6c9c2');
    const CLOUD3 = cloudMat('#edf3ef');
    const SPROUT = mat('#5c9b57');

    /* grid --------------------------------------------------------------- */
    const solid = new Uint8Array(SX * SY * SZ);
    const material = new Uint8Array(SX * SY * SZ);
    const emissive = new Uint8Array(SX * SY * SZ);
    const at = (x: number, y: number, z: number) => (z * SY + y) * SX + x;
    const inside = (x: number, y: number, z: number) =>
        x >= 0 && x < SX && y >= 0 && y < SY && z >= 0 && z < SZ;

    function put(x: number, y: number, z: number, m: number, glow = false) {
        const px = Math.round(x);
        const py = Math.round(y);
        const pz = Math.round(z);
        if (!inside(px, py, pz)) return;
        const i = at(px, py, pz);
        if (m === 0) {
            solid[i] = 0;
            material[i] = 0;
            emissive[i] = 0;
            return;
        }
        solid[i] = 1;
        material[i] = m;
        emissive[i] = glow ? 1 : 0;
    }
    const filled = (x: number, y: number, z: number) => inside(x, y, z) && solid[at(x, y, z)] === 1;

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
        for (let k = 0; k < h; k++)
            for (let j = 0; j < d; j++)
                for (let i = 0; i < w; i++) put(x + i, y + j, z + k, m, glow);
    }
    function cyl(cx: number, cy: number, z0: number, r: number, h: number, m: number) {
        for (let k = 0; k < h; k++)
            for (let y = -r; y <= r; y++)
                for (let x = -r; x <= r; x++)
                    if (x * x + y * y <= r * r + r * 0.6) put(cx + x, cy + y, z0 + k, m);
    }
    function sphere(cx: number, cy: number, cz: number, r: number, m: number) {
        const R2 = Math.ceil(r);
        for (let z = -R2; z <= R2; z++)
            for (let y = -R2; y <= R2; y++)
                for (let x = -R2; x <= R2; x++)
                    if (x * x + y * y + z * z <= r * r + r * 0.8) put(cx + x, cy + y, cz + z, m);
    }

    const heightAt = (x: number, y: number): number | null => {
        const dx = (x - CX) / R;
        const dy = (y - CY) / (R * 0.92);
        const d = Math.sqrt(dx * dx + dy * dy);
        if (d > 1) return null;
        const edge = Math.min(1, (1 - d) * 3.2);
        const n = Math.sin(x * 0.21) * Math.cos(y * 0.17) * 1.6 + Math.sin((x + y) * 0.11) * 1.2;
        return Math.round(14 + n + edge * 3);
    };

    /* 1. island ---------------------------------------------------------- */
    for (let y = 0; y < SY; y++)
        for (let x = 0; x < SX; x++) {
            const h = heightAt(x, y);
            if (h === null) continue;
            const slope = (heightAt(x + 1, y) ?? -99) - h;
            for (let z = 6; z <= h; z++) {
                const depth = h - z;
                let m: number;
                if (depth === 0) m = slope > 1 ? GRASS3 : rnd() < 0.5 ? GRASS : GRASS2;
                else if (depth <= 2) m = rnd() < 0.5 ? DIRT : DIRT2;
                else if (depth <= 5) m = rnd() < 0.5 ? STONE2 : STONE3;
                else m = rnd() < 0.5 ? STONE3 : STONE4;
                put(x, y, z, m);
            }
        }
    for (let z = 0; z < 7; z++) {
        const r = Math.round(R * (0.92 - z * 0.11));
        for (let y = CY - r; y <= CY + r; y++)
            for (let x = CX - r; x <= CX + r; x++) {
                const d = Math.hypot((x - CX) / r, (y - CY) / r);
                if (d <= 1 - rnd() * 0.16) put(x, y, z, rnd() < 0.5 ? STONE4 : STONE3);
            }
    }
    for (let i = 0; i < 28; i++) {
        const a = rnd() * Math.PI * 2;
        const r = R * (0.55 + rnd() * 0.42);
        const x = Math.round(CX + Math.cos(a) * r);
        const y = Math.round(CY + Math.sin(a) * r * 0.92);
        const len = ri(2, 4);
        for (let k = 0; k < len; k++) put(x, y, 5 - k, k < 2 ? ROOT : LEAF3);
    }

    /* 2. pond, path, bridge ---------------------------------------------- */
    const inPond = (x: number, y: number, scale = 1) => {
        const dx = (x - POND.x) / (POND.rx * scale);
        const dy = (y - POND.y) / (POND.ry * scale);
        return dx * dx + dy * dy <= 1;
    };
    for (let y = POND.y - POND.ry - 3; y <= POND.y + POND.ry + 3; y++)
        for (let x = POND.x - POND.rx - 3; x <= POND.x + POND.rx + 3; x++) {
            const h = heightAt(x, y);
            if (h === null) continue;
            if (inPond(x, y)) {
                for (let z = h - 3; z <= h + 2; z++) put(x, y, z, 0);
                put(x, y, h - 3, WATER3);
                put(x, y, h - 2, WATER);
                put(x, y, h - 1, rnd() < 0.72 ? WATER2 : WATER);
                if (rnd() < 0.08) put(x, y, h - 1, BLOSSOM3);
            } else if (inPond(x, y, 1.1)) {
                put(x, y, h, rnd() < 0.7 ? SAND : STONE2);
                if (rnd() < 0.13) put(x, y, h + 1, rnd() < 0.5 ? SPROUT : STONE4);
            }
        }
    for (let i = 0; i < 26; i++) {
        const a = rnd() * Math.PI * 2;
        const r = Math.sqrt(rnd()) * 0.82;
        const x = Math.round(POND.x + Math.cos(a) * POND.rx * r);
        const y = Math.round(POND.y + Math.sin(a) * POND.ry * r);
        const h = heightAt(x, y) ?? 14;
        if (rnd() < 0.55) put(x, y, h - 1, LEAF2);
        else if (rnd() < 0.4) put(x, y, h - 1, BLOSSOM);
    }
    for (const [kx, ky, m] of [
        [POND.x - 4, POND.y - 2, Koi],
        [POND.x + 3, POND.y + 3, Koi2],
    ] as const) {
        const h = heightAt(kx, ky) ?? 14;
        put(kx, ky, h - 1, m);
        put(kx + 1, ky, h - 1, m);
        put(kx, ky + 1, h - 1, m);
    }
    for (let t = 0; t <= 30; t++) {
        const x = Math.round(CX + 2 + Math.sin(t * 0.19) * 7);
        const y = Math.round(CY + 34 - t * 1.05);
        for (let dx = -1; dx <= 1; dx++)
            for (let dy = -1; dy <= 1; dy++) {
                const h = heightAt(x + dx, y + dy);
                if (h !== null && !inPond(x + dx, y + dy, 1.1))
                    put(x + dx, y + dy, h, (dx + dy + t) % 3 === 0 ? PATH2 : PATH);
            }
    }
    for (let t = -9; t <= 9; t++) {
        const x = POND.x - 14 + t;
        const y = Math.round(POND.y - Math.abs(t) * 0.12);
        // follow the local water surface instead of an absolute height, or the
        // deck sinks in the middle of the pond and re-emerges at the bank
        const surface = heightAt(x, y) ?? 15;
        const z = surface + 1 + Math.round(Math.cos((t / 9) * Math.PI * 0.5) * 1.2);
        for (let dx = 0; dx <= 2; dx++) put(x, y + dx, z, dx === 1 ? WOOD : WOOD2);
        if (Math.abs(t) % 3 === 0) {
            put(x, y - 1, z + 1, WOOD3);
            put(x, y + 3, z + 1, WOOD3);
        }
        if (Math.abs(t) < 9) {
            put(x, y - 1, z + 2, RED2);
            put(x, y + 3, z + 2, RED2);
        }
    }

    /* 3. the clearing ---------------------------------------------------- */
    const PX = CX - 6;
    const PY = CY - 4;
    const groundZ = heightAt(PX, PY) ?? 14;
    for (let y = PY - 10; y <= PY + 10; y++)
        for (let x = PX - 10; x <= PX + 10; x++) {
            if (Math.hypot(x - PX, y - PY) > 10.5) continue;
            const h = heightAt(x, y);
            if (h === null) continue;
            put(x, y, h + 1, Math.abs(x - PX) % 2 === 0 ? PATH : PATH2);
        }
    for (let y = PY - 3; y <= PY + 3; y++)
        for (let x = PX - 3; x <= PX + 3; x++)
            if ((x - PX) ** 2 + (y - PY) ** 2 <= 10) put(x, y, groundZ + 2, STONE3);

    /* 4. torii ----------------------------------------------------------- */
    const TX = CX + 3;
    const TY = CY + 26;
    const TZ = heightAt(TX, TY) ?? 14;
    box(TX - 6, TY, TZ, 2, 2, 11, RED);
    box(TX + 5, TY, TZ, 2, 2, 11, RED);
    box(TX - 9, TY, TZ + 10, 18, 2, 2, RED2);
    box(TX - 11, TY - 1, TZ + 12, 22, 4, 1, RED3);
    box(TX - 12, TY - 1, TZ + 13, 3, 4, 1, STONE3);
    box(TX + 10, TY - 1, TZ + 13, 3, 4, 1, STONE3);
    box(TX - 7, TY, TZ + 8, 14, 2, 1, RED3);
    put(TX, TY, TZ + 9, LANTERN, true);

    /* 5. trees, bamboo, rocks, lanterns, flowers ------------------------- */
    function cherry(cx: number, cy: number, scale: number) {
        const g = heightAt(cx, cy);
        if (g === null) return;
        const th = Math.round(11 * scale);
        for (let k = 0; k < th; k++) {
            const lean = Math.round(Math.sin((k / th) * 1.8) * 1.4);
            cyl(
                cx + lean,
                cy + Math.round(lean * 0.5),
                g + k,
                Math.max(1, Math.round(scale * 1.2)),
                1,
                k < 2 ? TRUNK2 : TRUNK,
            );
        }
        const top = g + th;
        for (const [bx, by, bz] of [
            [-4, 0, 1],
            [4, 1, 1],
            [0, -4, 1],
            [1, 4, 1],
        ]) {
            for (let k = 1; k <= 4; k++)
                put(
                    cx + Math.round((bx * k) / 4),
                    cy + Math.round((by * k) / 4),
                    top + Math.round((bz * k) / 4),
                    TRUNK,
                );
        }
        const blobs: Array<[number, number, number, number]> = [
            [0, 0, 4, 5],
            [-4, 1, 3, 3.7],
            [4, -1, 3, 3.9],
            [1, 4, 3, 3.5],
            [-3, -4, 3, 3.3],
            [0, 0, 7, 3],
        ];
        for (const [bx, by, bz, br] of blobs) {
            const r2 = Math.round(br * scale);
            for (let z = -r2; z <= r2; z++)
                for (let y = -r2; y <= r2; y++)
                    for (let x = -r2; x <= r2; x++) {
                        const d = x * x + y * y + z * z * 1.5;
                        if (d > r2 * r2) continue;
                        if (rnd() < 0.14) continue;
                        const px = cx + bx + x;
                        const py = cy + by + y;
                        const pz = top + bz + z;
                        if (filled(px, py, pz)) continue;
                        const t = rnd();
                        const m =
                            d > r2 * r2 * 0.66
                                ? t < 0.5
                                    ? BLOSSOM4
                                    : BLOSSOM2
                                : t < 0.42
                                  ? BLOSSOM
                                  : t < 0.72
                                    ? BLOSSOM2
                                    : t < 0.9
                                      ? BLOSSOM3
                                      : BLOSSOM4;
                        put(px, py, pz, m);
                    }
        }
        for (let i = 0; i < 90; i++) {
            const a = rnd() * Math.PI * 2;
            const r = Math.sqrt(rnd()) * 9 * scale;
            const px = Math.round(cx + Math.cos(a) * r);
            const py = Math.round(cy + Math.sin(a) * r);
            const h = heightAt(px, py);
            if (h === null) continue;
            if (!filled(px, py, h + 1)) put(px, py, h + 1, rnd() < 0.6 ? BLOSSOM : BLOSSOM3);
        }
    }
    cherry(CX - 22, CY - 16, 1.35);
    cherry(CX + 20, CY - 20, 1.15);
    cherry(CX - 27, CY + 10, 1.0);
    cherry(CX + 26, CY + 20, 0.95);
    cherry(CX - 10, CY - 26, 1.25);
    cherry(CX + 12, CY - 30, 0.85);
    cherry(PX, PY, 2.0);

    for (let i = 0; i < 26; i++) {
        const bx = CX - 34 + ri(0, 9);
        const by = CY - 4 + ri(0, 12);
        const g = heightAt(bx, by);
        if (g === null) continue;
        const h = ri(11, 20);
        for (let k = 0; k < h; k++)
            put(bx, by, g + k, k % 4 === 0 ? BAMBOO3 : k % 4 === 2 ? BAMBOO2 : BAMBOO);
        for (let k = 3; k < h; k += 4) {
            put(bx + 1, by, g + k, BAMBOO3);
            put(bx - 1, by, g + k, BAMBOO2);
            put(bx, by + 1, g + k, BAMBOO2);
        }
        if (rnd() < 0.5) for (let k = 0; k < 3; k++) put(bx, by, g + h + k, LEAF2);
    }

    for (const [rx, ry, rs] of [
        [CX + 30, CY - 8, 3],
        [CX - 18, CY + 24, 2],
        [CX + 8, CY + 30, 3],
        [CX - 30, CY - 24, 2],
        [CX + 32, CY + 6, 2],
    ] as const) {
        const g = heightAt(rx, ry);
        if (g === null) continue;
        sphere(rx, ry, g + 1, rs, STONE3);
        for (let i = 0; i < rs * 6; i++)
            put(rx + ri(-rs, rs), ry + ri(-rs, rs), g + rs, rnd() < 0.5 ? MOSS : LEAF3);
    }

    const lamps: Array<[number, number, number]> = [];
    for (const [lx, ly] of [
        [CX + 12, CY + 22],
        [CX - 8, CY + 16],
        [CX + 16, CY - 2],
        [CX - 14, CY + 30],
    ] as const) {
        const g = heightAt(lx, ly);
        if (g === null) continue;
        box(lx - 1, ly - 1, g + 1, 3, 3, 1, STONE2);
        box(lx, ly, g + 2, 1, 1, 3, STONE);
        box(lx - 1, ly - 1, g + 5, 3, 3, 2, LANTERN, true);
        box(lx - 2, ly - 2, g + 7, 5, 5, 1, STONE3);
        put(lx, ly, g + 8, STONE4);
        lamps.push([lx, ly, g + 6]);
    }
    lamps.push([TX, TY, TZ + 9]);

    for (let i = 0; i < 700; i++) {
        const x = CX + ri(-40, 40);
        const y = CY + ri(-38, 38);
        const h = heightAt(x, y);
        if (h === null) continue;
        if (inPond(x, y, 1.12)) continue;
        if (filled(x, y, h + 1)) continue;
        const t = rnd();
        put(x, y, h + 1, t < 0.5 ? FLOWER1 : t < 0.8 ? FLOWER2 : FLOWER3);
    }

    /* 6. clouds ---------------------------------------------------------- */
    function cloudBlob(cx: number, cy: number, cz: number, rx: number, ry: number, rz: number) {
        for (let z = -Math.ceil(rz); z <= Math.ceil(rz); z++)
            for (let y = -Math.ceil(ry); y <= Math.ceil(ry); y++)
                for (let x = -Math.ceil(rx); x <= Math.ceil(rx); x++) {
                    const d = (x * x) / (rx * rx) + (y * y) / (ry * ry) + (z * z) / (rz * rz);
                    if (d > 1) continue;
                    put(cx + x, cy + y, cz + z, z > 0 ? (d < 0.45 ? CLOUD3 : CLOUD) : CLOUD2);
                }
    }
    const cloudSpots: Array<[number, number, number, number, number, number]> = [
        [4, 6, 66, 9, 7, 2],
        [26, 2, 68, 8, 6, 2],
        [52, 4, 70, 9, 7, 2],
        [78, 8, 66, 8, 6, 2],
        [100, 18, 68, 9, 7, 2],
        [2, 34, 70, 8, 6, 2],
        [98, 44, 66, 9, 7, 2],
        [6, 62, 68, 8, 6, 2],
        [96, 70, 70, 9, 7, 2],
        [20, 96, 66, 8, 6, 2],
        [52, 100, 68, 9, 7, 2],
        [82, 98, 70, 8, 6, 2],
    ];
    for (const [cx, cy, cz, rx, ry, rz] of cloudSpots) {
        // inset so the whole blob fits the grid: a clipped cloud reads as a cut
        const bx = Math.min(Math.max(cx, Math.ceil(rx) + 1), SX - Math.ceil(rx) - 2);
        const by = Math.min(Math.max(cy, Math.ceil(ry) + 1), SY - Math.ceil(ry) - 2);
        const bz = Math.min(cz, SZ - Math.ceil(rz) - 3);
        cloudBlob(bx, by, bz, rx, ry, rz);
        cloudBlob(
            Math.min(
                Math.max(bx + ri(-8, 8), Math.ceil(rx * 0.5) + 1),
                SX - Math.ceil(rx * 0.5) - 2,
            ),
            Math.min(
                Math.max(by + ri(-5, 5), Math.ceil(ry * 0.5) + 1),
                SY - Math.ceil(ry * 0.5) - 2,
            ),
            Math.min(bz + 1, SZ - Math.ceil(rz) - 2),
            rx * 0.5,
            ry * 0.5,
            rz + 1,
        );
    }

    /* anchors ------------------------------------------------------------ */
    const petals: Array<[number, number, number]> = [];
    const petalSrc: Array<[number, number]> = [
        [CX - 22, CY - 16],
        [CX + 20, CY - 20],
        [CX - 27, CY + 10],
        [CX - 10, CY - 26],
        [PX, PY],
    ];
    for (let i = 0; i < 70; i++) {
        const s = petalSrc[i % petalSrc.length];
        petals.push([s[0] + ri(-7, 7), s[1] + ri(-6, 6), ri(22, 40)]);
    }

    const glints: Array<[number, number, number]> = [];
    for (let i = 0; i < 46; i++) {
        const gx = Math.round(POND.x + (rnd() * 2 - 1) * POND.rx * 0.8);
        const gy = Math.round(POND.y + (rnd() * 2 - 1) * POND.ry * 0.8);
        const h = heightAt(gx, gy);
        if (h === null) continue;
        glints.push([gx, gy, h - 1]);
    }

    let voxelCount = 0;
    for (let i = 0; i < solid.length; i++) if (solid[i]) voxelCount++;

    return {
        solid,
        material,
        emissive,
        palette,
        cloudMaterials: cloudIds,
        petals,
        glints,
        lamps,
        voxelCount,
    };
}
