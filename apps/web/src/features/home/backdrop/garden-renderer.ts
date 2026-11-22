import type { AtmospherePhase } from '@llm-market-bench/ui-design-system';
import {
    CEDAR_WORLD_META,
    CX,
    CY,
    type RenderableWorld,
    SX,
    SY,
    type WorldFaces,
    type WorldId,
} from './voxel-world';

export interface IslandVerticalBounds {
    minY: number;
    maxY: number;
}

const LIGHT: [number, number, number] = (() => {
    const v: [number, number, number] = [-0.45, -0.48, 0.75];
    const m = Math.hypot(v[0], v[1], v[2]);
    return [v[0] / m, v[1] / m, v[2] / m];
})();

/** Sunlit top faces get the warm cloud ramp; shaded flanks get the cool one. */
function pickFaceTint(
    palette: AtmospherePalette,
    cloud: 'far' | 'near' | null,
    face: number,
): [number, number, number] {
    if (cloud) return face === 0 ? palette.cloudTopTint : palette.cloudSideTint;
    return face === 0 ? palette.topTint : palette.sideTint;
}

const CEDAR_PARTICLE_COLORS = {
    driftColors: ['#e89648', '#f2c86b', '#d96b34'] as const,
    floaterColors: ['#c6f2bd', '#ffd880'] as const,
    glintHex: '#d6ecea',
    rippleHex: '#cceae4',
};

export interface Petal {
    x: number;
    y: number;
    vy: number;
    sway: number;
    phase: number;
    depth: number;
    size: number;
    tint: string;
}

export interface Firefly {
    x: number;
    y: number;
    ampX: number;
    ampY: number;
    speed: number;
    phase: number;
    size: number;
    tint: string;
}

export interface SkyMote {
    x: number;
    y: number;
    phase: number;
    speed: number;
    size: number;
}

/** Comfortable open-sky band the hero copy owns; drifting clouds never cross it while visible. */
export const CLOUD_CLEAR_CORRIDOR = { minX: 0.33, maxX: 0.67, minY: 0.08, maxY: 0.55 } as const;

/** Drift speed in CSS px/s: distant clouds crawl, near ones visibly travel. */
export const CLOUD_DRIFT_SPEED = { far: 3, near: 7 } as const;

/** Horizontal band one cloud travels, plus which end sits against the copy column. */
export interface CloudLane {
    min: number;
    max: number;
    fadeAt: 'start' | 'end' | null;
}

export interface CloudSprite {
    canvas: HTMLCanvasElement;
    /** Left edge in stage CSS px at `time = 0`. */
    x: number;
    y: number;
    width: number;
    height: number;
    lane: CloudLane;
    /** Travel offset at `time = 0`, so the first frame matches the static composition. */
    phase: number;
    speed: number;
    parallax: number;
}

export interface Scene {
    width: number;
    height: number;
    dpr: number;
    scale: number;
    worldId: WorldId;
    atmosphere: AtmospherePhase;
    sky: HTMLCanvasElement | null;
    foot: HTMLCanvasElement | null;
    lanternSprite: HTMLCanvasElement | null;
    lanternRadius: number;
    island: HTMLCanvasElement | null;
    islandBounds: IslandVerticalBounds;
    cloudsFar: CloudSprite[];
    cloudsNear: CloudSprite[];
    petals: Petal[];
    glints: Array<{ x: number; y: number; phase: number; speed: number; size: number }>;
    lamps: Array<{ x: number; y: number; phase: number }>;
    fireflies: Firefly[];
    koi: Array<{ x: number; y: number; phase: number }>;
    skyMotes: SkyMote[];
}

interface AtmospherePalette {
    skyStops: Array<[number, string]>;
    horizonGlow: [string, string, string];
    topVignette: [string, string, string];
    footFade: string;
    lightScale: number;
    topTint: [number, number, number];
    sideTint: [number, number, number];
    islandFog: [number, number, number];
    cloudHaze: [number, number, number];
    cloudTopTint: [number, number, number];
    cloudSideTint: [number, number, number];
    /** Clouds keep their own exposure so dark phases do not render them as sunlit. */
    cloudLightScale: number;
    lanternAlphaScale: number;
    showStars: boolean;
    showFireflies: boolean;
    showSunMotes: boolean;
}

export const ATMOSPHERE_PALETTES: Record<AtmospherePhase, AtmospherePalette> = {
    dawn: {
        skyStops: [
            [0, '#101c1a'],
            [0.24, '#1b2f2b'],
            [0.46, '#2d4d45'],
            [0.66, '#5c7a6e'],
            [0.8, '#9e8d7b'],
            [0.9, '#cfa07a'],
            [1, '#263832'],
        ],
        horizonGlow: [
            'rgba(236, 164, 124, 0.25)',
            'rgba(214, 148, 112, 0.09)',
            'rgba(214, 148, 112, 0)',
        ],
        topVignette: ['rgba(9, 18, 16, 0.58)', 'rgba(9, 18, 16, 0.48)', 'rgba(9, 18, 16, 0.56)'],
        footFade: 'rgba(14, 24, 21, 0.42)',
        lightScale: 0.98,
        topTint: [1.05, 0.99, 0.96],
        sideTint: [0.94, 0.97, 1.04],
        islandFog: [64, 82, 76],
        cloudHaze: [208, 182, 160],
        cloudTopTint: [1.0, 0.96, 0.88],
        cloudSideTint: [0.86, 0.91, 1.04],
        cloudLightScale: 0.95,
        lanternAlphaScale: 0.72,
        showStars: false,
        showFireflies: false,
        showSunMotes: true,
    },
    daylight: {
        skyStops: [
            [0, '#11221e'],
            [0.24, '#1a352f'],
            [0.48, '#285248'],
            [0.68, '#3f7264'],
            [0.82, '#6b9a87'],
            [0.92, '#9abca8'],
            [1, '#233d35'],
        ],
        horizonGlow: [
            'rgba(182, 224, 198, 0.22)',
            'rgba(138, 192, 162, 0.08)',
            'rgba(138, 192, 162, 0)',
        ],
        topVignette: ['rgba(10, 22, 19, 0.60)', 'rgba(10, 22, 19, 0.48)', 'rgba(10, 22, 19, 0.52)'],
        footFade: 'rgba(15, 28, 24, 0.38)',
        lightScale: 1.07,
        topTint: [1.03, 1.04, 0.99],
        sideTint: [0.96, 1.01, 1.02],
        islandFog: [68, 98, 86],
        cloudHaze: [206, 214, 208],
        cloudTopTint: [1.0, 1.0, 0.97],
        cloudSideTint: [0.9, 0.96, 1.04],
        cloudLightScale: 0.96,
        lanternAlphaScale: 0.36,
        showStars: false,
        showFireflies: false,
        showSunMotes: true,
    },
    dusk: {
        skyStops: [
            [0, '#0c1715'],
            [0.24, '#142622'],
            [0.45, '#23413b'],
            [0.64, '#45675f'],
            [0.78, '#819587'],
            [0.88, '#b59a78'],
            [1, '#22332e'],
        ],
        horizonGlow: [
            'rgba(240, 184, 108, 0.22)',
            'rgba(214, 162, 102, 0.08)',
            'rgba(214, 162, 102, 0)',
        ],
        topVignette: ['rgba(8, 16, 14, 0.56)', 'rgba(8, 16, 14, 0.44)', 'rgba(8, 16, 14, 0.50)'],
        footFade: 'rgba(12, 22, 20, 0.42)',
        lightScale: 1.0,
        topTint: [1.04, 1.01, 0.93],
        sideTint: [0.95, 0.99, 1.04],
        islandFog: [52, 74, 70],
        cloudHaze: [186, 162, 140],
        cloudTopTint: [0.98, 0.93, 0.83],
        cloudSideTint: [0.8, 0.85, 1.0],
        cloudLightScale: 0.84,
        lanternAlphaScale: 1.0,
        showStars: true,
        showFireflies: true,
        showSunMotes: false,
    },
    'after-hours': {
        skyStops: [
            [0, '#060c0b'],
            [0.26, '#0b1614'],
            [0.5, '#122420'],
            [0.72, '#1c3530'],
            [0.86, '#294840'],
            [0.94, '#35574d'],
            [1, '#101d1a'],
        ],
        horizonGlow: [
            'rgba(116, 184, 162, 0.16)',
            'rgba(72, 132, 116, 0.06)',
            'rgba(72, 132, 116, 0)',
        ],
        topVignette: ['rgba(4, 9, 8, 0.56)', 'rgba(4, 9, 8, 0.32)', 'rgba(4, 9, 8, 0.22)'],
        footFade: 'rgba(6, 12, 11, 0.52)',
        lightScale: 0.76,
        topTint: [0.86, 0.96, 1.08],
        sideTint: [0.82, 0.92, 1.06],
        islandFog: [24, 42, 38],
        cloudHaze: [58, 80, 80],
        cloudTopTint: [0.62, 0.72, 0.9],
        cloudSideTint: [0.5, 0.6, 0.82],
        cloudLightScale: 0.62,
        lanternAlphaScale: 1.32,
        showStars: true,
        showFireflies: true,
        showSunMotes: false,
    },
};

export function pickCedarDriftColor(index: number): string {
    return CEDAR_PARTICLE_COLORS.driftColors[index % CEDAR_PARTICLE_COLORS.driftColors.length];
}

export function pickCedarFloaterColor(index: number): string {
    return CEDAR_PARTICLE_COLORS.floaterColors[index % CEDAR_PARTICLE_COLORS.floaterColors.length];
}

export function bakeSky(
    W: number,
    H: number,
    dpr: number,
    atmosphere: AtmospherePhase = 'dusk',
): HTMLCanvasElement | null {
    const off = document.createElement('canvas');
    off.width = Math.round(W * dpr);
    off.height = Math.round(H * dpr);
    const ctx = off.getContext('2d');
    if (!ctx) return null;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    const palette = ATMOSPHERE_PALETTES[atmosphere];

    const sky = ctx.createLinearGradient(0, 0, 0, H);
    for (const [stop, color] of palette.skyStops) {
        sky.addColorStop(stop, color);
    }
    ctx.fillStyle = sky;
    ctx.fillRect(0, 0, W, H);

    // Phase-reactive horizon glow centered behind the floating cedar ridge silhouette
    const glow = ctx.createRadialGradient(
        W * 0.5,
        H * 0.84,
        W * 0.04,
        W * 0.5,
        H * 0.84,
        Math.max(W, H) * 0.55,
    );
    glow.addColorStop(0, palette.horizonGlow[0]);
    glow.addColorStop(0.48, palette.horizonGlow[1]);
    glow.addColorStop(1, palette.horizonGlow[2]);
    ctx.fillStyle = glow;
    ctx.fillRect(0, 0, W, H);

    // Horizon haze behind the cloud planes; the planes' own aerial perspective comes from cloudHaze fog.
    const [hazeR, hazeG, hazeB] = palette.cloudHaze;
    const haze = ctx.createLinearGradient(0, H * 0.44, 0, H * 0.96);
    haze.addColorStop(0, `rgba(${hazeR}, ${hazeG}, ${hazeB}, 0)`);
    haze.addColorStop(0.58, `rgba(${hazeR}, ${hazeG}, ${hazeB}, 0.15)`);
    haze.addColorStop(1, `rgba(${hazeR}, ${hazeG}, ${hazeB}, 0)`);
    ctx.fillStyle = haze;
    ctx.fillRect(0, H * 0.44, W, H * 0.52);

    // Phase-tuned extended top atmospheric vignette so open-sky cream copy and CTAs maintain AAA contrast
    const topVignette = ctx.createLinearGradient(0, 0, 0, H * 0.86);
    topVignette.addColorStop(0, palette.topVignette[0]);
    topVignette.addColorStop(0.52, palette.topVignette[1]);
    topVignette.addColorStop(0.76, palette.topVignette[2]);
    topVignette.addColorStop(1, 'rgba(8, 16, 14, 0)');
    ctx.fillStyle = topVignette;
    ctx.fillRect(0, 0, W, H * 0.86);

    return off;
}

export function bakeFootFade(
    W: number,
    H: number,
    dpr: number,
    atmosphere: AtmospherePhase = 'dusk',
): HTMLCanvasElement | null {
    const bandH = Math.max(1, Math.round(H * 0.16));
    const off = document.createElement('canvas');
    off.width = Math.round(W * dpr);
    off.height = Math.round(bandH * dpr);
    const ctx = off.getContext('2d');
    if (!ctx) return null;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    const palette = ATMOSPHERE_PALETTES[atmosphere];
    const foot = ctx.createLinearGradient(0, 0, 0, bandH);
    foot.addColorStop(0, 'rgba(12, 22, 20, 0)');
    foot.addColorStop(1, palette.footFade);
    ctx.fillStyle = foot;
    ctx.fillRect(0, 0, W, bandH);
    return off;
}

export function bakeLanternSprite(
    radius: number,
    dpr: number,
    glowRgb: [number, number, number] = CEDAR_WORLD_META.glowRgb,
): HTMLCanvasElement | null {
    const r = Math.max(4, Math.ceil(radius));
    const size = r * 2;
    const off = document.createElement('canvas');
    off.width = Math.round(size * dpr);
    off.height = Math.round(size * dpr);
    const ctx = off.getContext('2d');
    if (!ctx) return null;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    const [gr, gg, gb] = glowRgb;
    const g = ctx.createRadialGradient(r, r, 1, r, r, r);
    g.addColorStop(0, `rgba(${gr}, ${gg}, ${gb}, 0.36)`);
    g.addColorStop(0.45, `rgba(${gr}, ${Math.max(0, gg - 24)}, ${Math.max(0, gb - 20)}, 0.14)`);
    g.addColorStop(1, `rgba(${gr}, ${gg}, ${gb}, 0)`);
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, size, size);
    return off;
}

/** Distance haze: islands darken by depth, clouds bleach toward the horizon by altitude plane. */
function cloudFogAmount(cloud: 'far' | 'near' | null, x: number, y: number, depthRatio: number) {
    if (!cloud) return Math.min(0.16, Math.max(0, depthRatio - 0.72) * 0.7);
    const cap = cloud === 'far' ? 0.2 : 0.1;
    const dist = Math.hypot(x - CX, y - CY);
    return cap * Math.min(1, Math.max(0, (dist - 24) / 90));
}

/** Key light per face, with cloud-specific bounce: bright warm tops, cool shaded flanks. */
const CLOUD_FACE_K = [1, 0.93, 0.86] as const;

function faceLightK(face: number, cloud: 'far' | 'near' | null): number {
    // Clouds are lit flat and bright; the hard terrain ramp would turn them to rock.
    if (cloud) return CLOUD_FACE_K[Math.min(face, 2)];
    if (face === 0) return 0.74 + 0.52 * LIGHT[2];
    if (face === 1) return 0.48 + 0.38 * (-LIGHT[1] + 0.38);
    return 0.36 + 0.38 * (LIGHT[0] + 0.5);
}

function shadeFaceRgb(
    rIn: number,
    gIn: number,
    bIn: number,
    glow: boolean,
    x: number,
    y: number,
    face: number,
    ao: number,
    cloud: 'far' | 'near' | null,
    depthMax: number,
    atmosphere: AtmospherePhase,
): string {
    const palette = ATMOSPHERE_PALETTES[atmosphere];
    const fog = cloudFogAmount(cloud, x, y, (x + y) / depthMax);

    let k =
        faceLightK(face, cloud) * ao * palette.lightScale * (cloud ? palette.cloudLightScale : 1);
    if (glow) k = atmosphere === 'after-hours' ? 1.32 : 1.18;

    const tint = pickFaceTint(palette, cloud, face);

    let r = rIn * k * tint[0];
    let g2 = gIn * k * tint[1];
    let b = bIn * k * tint[2];

    if (glow) {
        r = Math.min(255, r + 18);
        g2 = Math.min(255, g2 + 16);
        b = Math.min(255, b + 14);
    }

    const [fogR, fogG, fogB] = cloud ? palette.cloudHaze : palette.islandFog;
    r += (fogR - r) * fog;
    g2 += (fogG - g2) * fog;
    b += (fogB - b) * fog;

    return `rgb(${Math.min(255, r) | 0},${Math.min(255, g2) | 0},${Math.min(255, b) | 0})`;
}

/** Traces one isometric voxel face at projected `(px, py)`; shared by layer and sprite bakes. */
function traceVoxelFace(
    ctx: CanvasRenderingContext2D,
    px: number,
    py: number,
    face: number,
    HW: number,
    HH: number,
    ZH: number,
) {
    ctx.beginPath();
    if (face === 0) {
        ctx.moveTo(px, py - HH * 2);
        ctx.lineTo(px + HW, py - HH);
        ctx.lineTo(px, py);
        ctx.lineTo(px - HW, py - HH);
    } else {
        const sx = face === 1 ? -HW : HW;
        ctx.moveTo(px + sx, py - HH);
        ctx.lineTo(px, py);
        ctx.lineTo(px, py + ZH * 2);
        ctx.lineTo(px + sx, py - HH + ZH * 2);
    }
    ctx.closePath();
    ctx.fill();
}

export function paintVoxelLayer(
    list: WorldFaces['island'],
    world: RenderableWorld,
    W: number,
    H: number,
    dpr: number,
    scale: number,
    project: (x: number, y: number, z: number) => [number, number],
    atmosphere: AtmospherePhase = 'dusk',
): HTMLCanvasElement | null {
    const off = document.createElement('canvas');
    off.width = Math.round(W * dpr);
    off.height = Math.round(H * dpr);
    const o = off.getContext('2d');
    if (!o) return null;
    o.setTransform(dpr, 0, 0, dpr, 0, 0);
    const depthMax = (SX + SY) * 0.9;
    const HW = scale * 0.5;
    const HH = scale * 0.34;
    const ZH = scale * 0.46;

    for (const [, x, y, z, face, i, ao] of list) {
        const m = world.palette[world.material[i] - 1];
        if (!m) continue;
        const [px, py] = project(x, y, z);
        o.fillStyle = shadeFaceRgb(
            m.color.r,
            m.color.g,
            m.color.b,
            m.glow,
            x,
            y,
            face,
            ao,
            null,
            depthMax,
            atmosphere,
        );
        traceVoxelFace(o, px, py, face, HW, HH, ZH);
    }
    return off;
}

/** Screen-space bounding box of a face list, used to crop a cloud sprite. */
function measureBounds(
    faces: WorldFaces['island'],
    project: (x: number, y: number, z: number) => [number, number],
    HW: number,
    HH: number,
    ZH: number,
) {
    let minX = Number.POSITIVE_INFINITY;
    let minY = Number.POSITIVE_INFINITY;
    let maxX = Number.NEGATIVE_INFINITY;
    let maxY = Number.NEGATIVE_INFINITY;
    for (const [, x, y, z, face] of faces) {
        const [px, py] = project(x, y, z);
        for (const [qx, qy] of faceCorners(px, py, face, HW, HH, ZH)) {
            if (qx < minX) minX = qx;
            if (qx > maxX) maxX = qx;
            if (qy < minY) minY = qy;
            if (qy > maxY) maxY = qy;
        }
    }
    return { minX, minY, maxX, maxY };
}

/** Corner points of one projected voxel face, used for cropping a cloud sprite. */
function faceCorners(
    px: number,
    py: number,
    face: number,
    HW: number,
    HH: number,
    ZH: number,
): Array<[number, number]> {
    if (face === 0) {
        return [
            [px, py - HH * 2],
            [px + HW, py - HH],
            [px, py],
            [px - HW, py - HH],
        ];
    }
    const sx = face === 1 ? -HW : HW;
    return [
        [px + sx, py - HH],
        [px, py],
        [px, py + ZH * 2],
        [px + sx, py - HH + ZH * 2],
    ];
}

/**
 * Clouds drift outward from the hero copy: a cloud that shares the copy's rows gets the flank it
 * already sits on and dissolves against the copy edge, so it can leave and return without ever
 * sitting behind the headline. Clouds whose rows clear the copy (all of them on portrait) drift
 * the full stage instead.
 */
export function computeCloudLane(
    x: number,
    y: number,
    width: number,
    height: number,
    stageWidth: number,
    stageHeight: number,
): CloudLane {
    const sharesCopyRows =
        y < stageHeight * CLOUD_CLEAR_CORRIDOR.maxY &&
        y + height > stageHeight * CLOUD_CLEAR_CORRIDOR.minY;
    if (!sharesCopyRows) return { min: -width, max: stageWidth, fadeAt: null };

    const gutter = 8;
    const isLeft = x + width / 2 < stageWidth / 2;
    return isLeft
        ? {
              min: -width,
              max: stageWidth * CLOUD_CLEAR_CORRIDOR.minX - width - gutter,
              fadeAt: 'end',
          }
        : {
              min: stageWidth * CLOUD_CLEAR_CORRIDOR.maxX + gutter,
              max: stageWidth,
              fadeAt: 'start',
          };
}

/** Position of a cloud at `time`; the signed speed decides which way it travels. */
export function cloudDriftAt(
    lane: CloudLane,
    speed: number,
    phase: number,
    time: number,
): { x: number } {
    const span = Math.max(1, lane.max - lane.min);
    const travel = (((time * speed + phase) % span) + span) % span;
    return { x: lane.min + travel };
}

/** Opacity of a cloud: dissolves over the last stretch before the copy column, opaque elsewhere. */
export function cloudAlphaAt(sprite: { width: number }, lane: CloudLane, x: number): number {
    if (lane.fadeAt === null) return 1;
    const fadePx = Math.max(24, Math.min(48, sprite.width * 0.12));
    const remaining = lane.fadeAt === 'end' ? lane.max - x : x - lane.min;
    return Math.max(0, Math.min(1, remaining / fadePx));
}

/** Bakes a single cloud's faces into a cropped canvas anchored at its stage position. */
function bakeOneCloud(
    entry: { plane: 'far' | 'near'; faces: WorldFaces['island'] },
    world: RenderableWorld,
    dims: { width: number; height: number; dpr: number; scale: number },
    project: (x: number, y: number, z: number) => [number, number],
    atmosphere: AtmospherePhase,
): CloudSprite | null {
    const { width, height, dpr, scale } = dims;
    const HW = scale * 0.5;
    const HH = scale * 0.34;
    const ZH = scale * 0.46;
    const { minX, minY, maxX, maxY } = measureBounds(entry.faces, project, HW, HH, ZH);
    const pad = 2;
    const spriteWidth = Math.ceil(maxX - minX) + pad * 2;
    const spriteHeight = Math.ceil(maxY - minY) + pad * 2;
    if (spriteWidth <= 0 || spriteHeight <= 0) return null;

    const canvas = document.createElement('canvas');
    canvas.width = Math.round(spriteWidth * dpr);
    canvas.height = Math.round(spriteHeight * dpr);
    const ctx = canvas.getContext('2d');
    if (!ctx) return null;

    const originX = minX - pad;
    const originY = minY - pad;
    ctx.setTransform(dpr, 0, 0, dpr, -originX * dpr, -originY * dpr);

    for (const [, x, y, z, face, i, ao] of entry.faces) {
        const material = world.palette[world.material[i] - 1];
        if (!material) continue;
        const [px, py] = project(x, y, z);
        ctx.fillStyle = shadeFaceRgb(
            material.color.r,
            material.color.g,
            material.color.b,
            material.glow,
            x,
            y,
            face,
            ao,
            entry.plane,
            (SX + SY) * 0.9,
            atmosphere,
        );
        traceVoxelFace(ctx, px, py, face, HW, HH, ZH);
    }

    const lane = computeCloudLane(originX, originY, spriteWidth, spriteHeight, width, height);
    const span = Math.max(1, lane.max - lane.min);
    const baseSpeed = entry.plane === 'far' ? CLOUD_DRIFT_SPEED.far : CLOUD_DRIFT_SPEED.near;
    return {
        canvas,
        x: originX,
        y: originY,
        width: spriteWidth,
        height: spriteHeight,
        lane,
        phase: Math.min(span, Math.max(0, originX - lane.min)),
        // Flank clouds drift outward from the copy, so their lane end is the entry point.
        speed: lane.fadeAt === 'end' ? -baseSpeed : baseSpeed,
        parallax: entry.plane === 'far' ? 1.4 : 2.6,
    };
}

/**
 * Bakes every cloud into its own cropped canvas so it can be drifted and faded on its own
 * instead of sharing one full-stage layer with five neighbours.
 */
export function bakeCloudSprites(
    faces: WorldFaces,
    world: RenderableWorld,
    dims: { width: number; height: number; dpr: number; scale: number },
    project: (x: number, y: number, z: number) => [number, number],
    atmosphere: AtmospherePhase,
): { far: CloudSprite[]; near: CloudSprite[] } {
    const groups = new Map<number, { plane: 'far' | 'near'; faces: WorldFaces['island'] }>();
    const collect = (list: WorldFaces['island'], plane: 'far' | 'near') => {
        for (const face of list) {
            const group = world.cloudGroupOf.get(world.material[face[5]]);
            if (group === undefined) continue;
            const entry = groups.get(group) ?? { plane, faces: [] };
            entry.faces.push(face);
            groups.set(group, entry);
        }
    };
    collect(faces.cloudsFar, 'far');
    collect(faces.cloudsNear, 'near');

    const far: CloudSprite[] = [];
    const near: CloudSprite[] = [];
    for (const group of [...groups.keys()].sort((a, b) => a - b)) {
        const entry = groups.get(group);
        if (!entry || entry.faces.length === 0) continue;

        const sprite = bakeOneCloud(entry, world, dims, project, atmosphere);
        if (!sprite) continue;
        (entry.plane === 'far' ? far : near).push(sprite);
    }

    return { far, near };
}

export function drawZenithParticles(
    ctx: CanvasRenderingContext2D,
    scene: Scene,
    time: number,
    par: number,
) {
    const palette = ATMOSPHERE_PALETTES[scene.atmosphere];
    if (palette.showStars) {
        const baseAlpha = scene.atmosphere === 'after-hours' ? 0.55 : 0.24;
        ctx.fillStyle = '#f2ead3';
        for (const s of scene.skyMotes) {
            const twinkle = 0.45 + 0.55 * Math.sin(time * s.speed + s.phase);
            ctx.globalAlpha = baseAlpha * twinkle;
            ctx.fillRect(s.x + par * 2, s.y, s.size, s.size);
        }
        ctx.globalAlpha = 1;
        return;
    }

    if (palette.showSunMotes) {
        ctx.fillStyle = scene.atmosphere === 'dawn' ? '#f6cfa6' : '#d8f0df';
        for (const s of scene.skyMotes) {
            const driftX = s.x + Math.sin(time * 0.4 + s.phase) * 8 + par * 3.5;
            const driftY = s.y + Math.cos(time * 0.35 + s.phase) * 5;
            ctx.globalAlpha = 0.14 + 0.16 * (0.5 + 0.5 * Math.sin(time * s.speed + s.phase));
            ctx.fillRect(driftX, driftY, s.size, s.size);
        }
        ctx.globalAlpha = 1;
    }
}

function drawSurfaceGlints(
    ctx: CanvasRenderingContext2D,
    scene: Scene,
    time: number,
    islandParX: number,
    islandParY: number,
    alphaScale: number,
) {
    ctx.fillStyle = CEDAR_PARTICLE_COLORS.glintHex;
    for (const g of scene.glints) {
        ctx.globalAlpha =
            (0.09 + 0.26 * (0.5 + 0.5 * Math.sin(time * g.speed + g.phase))) * alphaScale;
        ctx.fillRect(g.x + islandParX, g.y + islandParY, g.size, Math.max(1, g.size * 0.45));
    }
    ctx.globalAlpha = 1;
}

function drawSurfaceRipples(
    ctx: CanvasRenderingContext2D,
    scene: Scene,
    time: number,
    islandParX: number,
    islandParY: number,
    alphaScale: number,
) {
    if (scene.koi.length === 0) return;
    ctx.strokeStyle = CEDAR_PARTICLE_COLORS.rippleHex;
    ctx.lineWidth = 1;
    for (const k of scene.koi) {
        const cycle = (time * 0.58 + k.phase) % 1;
        const rx = (2 + cycle * 6.5) * (scene.scale * 0.12);
        const ry = rx * 0.56;
        const cx = k.x + islandParX + Math.sin(time * 0.6 + k.phase) * 2.5;
        const cy = k.y + islandParY + Math.cos(time * 0.6 + k.phase) * 1.4;
        ctx.globalAlpha = (1 - cycle) * 0.55 * alphaScale;
        ctx.beginPath();
        ctx.moveTo(cx, cy - ry);
        ctx.lineTo(cx + rx, cy);
        ctx.lineTo(cx, cy + ry);
        ctx.lineTo(cx - rx, cy);
        ctx.closePath();
        ctx.stroke();
    }
    ctx.globalAlpha = 1;
}

function drawBeaconHalos(
    ctx: CanvasRenderingContext2D,
    scene: Scene,
    lanternAlphaScale: number,
    time: number,
    islandParX: number,
    islandParY: number,
    alphaScale: number,
) {
    if (!scene.lanternSprite) return;
    const r = scene.lanternRadius;
    ctx.globalCompositeOperation = 'lighter';
    for (const l of scene.lamps) {
        const flicker =
            0.78 + 0.22 * Math.sin(time * 2.4 + l.phase) * Math.sin(time * 1.3 + l.phase * 2);
        ctx.globalAlpha = Math.min(1, flicker * lanternAlphaScale) * alphaScale;
        ctx.drawImage(
            scene.lanternSprite,
            l.x + islandParX - r,
            l.y + islandParY - r,
            r * 2,
            r * 2,
        );
    }
    ctx.globalAlpha = 1;
    ctx.globalCompositeOperation = 'source-over';
}

function drawFireflies(
    ctx: CanvasRenderingContext2D,
    scene: Scene,
    showFireflies: boolean,
    time: number,
    islandParX: number,
    islandParY: number,
    alphaScale: number,
) {
    if (!showFireflies || scene.fireflies.length === 0) return;
    const boost = (scene.atmosphere === 'after-hours' ? 1 : 0.72) * alphaScale;
    for (const f of scene.fireflies) {
        const fx = f.x + islandParX + Math.sin(time * f.speed + f.phase) * f.ampX;
        const fy = f.y + islandParY + Math.cos(time * (f.speed * 0.85) + f.phase) * f.ampY;
        const pulse = 0.25 + 0.75 * (0.5 + 0.5 * Math.sin(time * 2.1 + f.phase));
        ctx.fillStyle = f.tint;
        ctx.globalAlpha = pulse * boost;
        ctx.fillRect(fx, fy, f.size, f.size);
    }
    ctx.globalAlpha = 1;
}

function drawCedarMistAndLeaves(
    ctx: CanvasRenderingContext2D,
    scene: Scene,
    time: number,
    par: number,
    alphaScale: number,
) {
    // Soft drifting haze wisps instead of hard-edged bands, so the horizon reads as air.
    ctx.globalAlpha = alphaScale;
    const wispRadius = Math.max(24, scene.scale * 9);
    for (let i = 0; i < 3; i++) {
        const wispY = scene.height * (0.58 + i * 0.08);
        const wispX =
            ((time * (6 + i * 2.5) + i * 220) % (scene.width + wispRadius * 2)) -
            wispRadius +
            par * 8;
        const wisp = ctx.createRadialGradient(wispX, wispY, 0, wispX, wispY, wispRadius);
        wisp.addColorStop(0, 'rgba(218, 232, 224, 0.10)');
        wisp.addColorStop(0.55, 'rgba(218, 232, 224, 0.045)');
        wisp.addColorStop(1, 'rgba(218, 232, 224, 0)');
        ctx.fillStyle = wisp;
        ctx.fillRect(wispX - wispRadius, wispY - wispRadius, wispRadius * 2, wispRadius * 2);
    }

    const H = scene.height;
    for (const p of scene.petals) {
        const y = p.y + ((time * p.vy * 6.5) % (H + 80)) - 40;
        const x = p.x + Math.sin(time * 0.92 + p.phase) * (p.sway * 1.4) + par * 12 * p.depth;
        ctx.fillStyle = p.tint;
        ctx.globalAlpha = (0.45 + 0.28 * Math.sin(time * 0.9 + p.phase)) * alphaScale;
        ctx.fillRect(x, y, p.size, p.size);
    }
    ctx.globalAlpha = 1;
}

export function drawAtmosphericParticles(
    ctx: CanvasRenderingContext2D,
    scene: Scene,
    time: number,
    par: number,
    islandParX: number,
    islandParY: number,
    alphaScale = 1,
) {
    if (alphaScale <= 0) return;
    const palette = ATMOSPHERE_PALETTES[scene.atmosphere];

    drawSurfaceGlints(ctx, scene, time, islandParX, islandParY, alphaScale);
    drawSurfaceRipples(ctx, scene, time, islandParX, islandParY, alphaScale);
    drawBeaconHalos(
        ctx,
        scene,
        palette.lanternAlphaScale,
        time,
        islandParX,
        islandParY,
        alphaScale,
    );
    drawFireflies(ctx, scene, palette.showFireflies, time, islandParX, islandParY, alphaScale);
    drawCedarMistAndLeaves(ctx, scene, time, par, alphaScale);
}

/** Releases GPU backing storage for an offscreen canvas safely. */
export function disposeCanvas(canvas: HTMLCanvasElement | null | undefined) {
    if (!canvas) return;
    canvas.width = 0;
    canvas.height = 0;
}

/** Releases all offscreen layer canvases owned by a Scene before GC or rebuild. */
export function disposeSceneCanvases(scene: Scene | null) {
    if (!scene) return;
    disposeCanvas(scene.sky);
    disposeCanvas(scene.foot);
    disposeCanvas(scene.lanternSprite);
    disposeCanvas(scene.island);
    for (const sprite of [...scene.cloudsFar, ...scene.cloudsNear]) {
        disposeCanvas(sprite.canvas);
    }
}
