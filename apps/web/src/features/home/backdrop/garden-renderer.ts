import type { AtmospherePhase } from '@llm-market-bench/ui-design-system';
import { CX, CY, type GardenWorld, SX, SY, type WorldFaces } from './garden-world';

const LIGHT: [number, number, number] = (() => {
    const v: [number, number, number] = [-0.45, -0.48, 0.75];
    const m = Math.hypot(v[0], v[1], v[2]);
    return [v[0] / m, v[1] / m, v[2] / m];
})();

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

export interface Scene {
    width: number;
    height: number;
    dpr: number;
    scale: number;
    atmosphere: AtmospherePhase;
    sky: HTMLCanvasElement | null;
    foot: HTMLCanvasElement | null;
    lanternSprite: HTMLCanvasElement | null;
    lanternRadius: number;
    island: HTMLCanvasElement | null;
    cloudsFar: HTMLCanvasElement | null;
    cloudsNear: HTMLCanvasElement | null;
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
    topVignette: [string, string];
    footFade: string;
    lightScale: number;
    topTint: [number, number, number];
    sideTint: [number, number, number];
    islandFog: [number, number, number];
    cloudFog: [number, number, number];
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
        topVignette: ['rgba(9, 18, 16, 0.48)', 'rgba(9, 18, 16, 0.20)'],
        footFade: 'rgba(14, 24, 21, 0.42)',
        lightScale: 0.98,
        topTint: [1.05, 0.99, 0.96],
        sideTint: [0.94, 0.97, 1.04],
        islandFog: [64, 82, 76],
        cloudFog: [148, 142, 132],
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
        topVignette: ['rgba(10, 22, 19, 0.54)', 'rgba(10, 22, 19, 0.24)'],
        footFade: 'rgba(15, 28, 24, 0.38)',
        lightScale: 1.07,
        topTint: [1.03, 1.04, 0.99],
        sideTint: [0.96, 1.01, 1.02],
        islandFog: [68, 98, 86],
        cloudFog: [156, 174, 164],
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
        topVignette: ['rgba(8, 16, 14, 0.44)', 'rgba(8, 16, 14, 0.18)'],
        footFade: 'rgba(12, 22, 20, 0.42)',
        lightScale: 1.0,
        topTint: [1.04, 1.01, 0.93],
        sideTint: [0.95, 0.99, 1.04],
        islandFog: [52, 74, 70],
        cloudFog: [132, 138, 124],
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
        topVignette: ['rgba(4, 9, 8, 0.52)', 'rgba(4, 9, 8, 0.20)'],
        footFade: 'rgba(6, 12, 11, 0.52)',
        lightScale: 0.76,
        topTint: [0.86, 0.96, 1.08],
        sideTint: [0.82, 0.92, 1.06],
        islandFog: [24, 42, 38],
        cloudFog: [64, 86, 80],
        lanternAlphaScale: 1.32,
        showStars: true,
        showFireflies: true,
        showSunMotes: false,
    },
};

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

    // Phase-reactive horizon glow centered behind the floating island silhouette
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

    // Phase-tuned top atmospheric vignette so open-sky cream typography reads at AAA contrast
    const topVignette = ctx.createLinearGradient(0, 0, 0, H * 0.44);
    topVignette.addColorStop(0, palette.topVignette[0]);
    topVignette.addColorStop(0.6, palette.topVignette[1]);
    topVignette.addColorStop(1, 'rgba(8, 16, 14, 0)');
    ctx.fillStyle = topVignette;
    ctx.fillRect(0, 0, W, H * 0.44);

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

export function bakeLanternSprite(radius: number, dpr: number): HTMLCanvasElement | null {
    const r = Math.max(4, Math.ceil(radius));
    const size = r * 2;
    const off = document.createElement('canvas');
    off.width = Math.round(size * dpr);
    off.height = Math.round(size * dpr);
    const ctx = off.getContext('2d');
    if (!ctx) return null;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    const g = ctx.createRadialGradient(r, r, 1, r, r, r);
    g.addColorStop(0, 'rgba(248, 192, 98, 0.34)');
    g.addColorStop(0.45, 'rgba(240, 168, 72, 0.14)');
    g.addColorStop(1, 'rgba(240, 168, 72, 0)');
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, size, size);
    return off;
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
    cloud: boolean,
    depthMax: number,
    atmosphere: AtmospherePhase,
): string {
    const palette = ATMOSPHERE_PALETTES[atmosphere];
    let fog = Math.min(0.16, Math.max(0, (x + y) / depthMax - 0.72) * 0.7);
    if (cloud) {
        const dist = Math.hypot(x - CX, y - CY);
        fog = Math.min(0.45, Math.max(0, (dist - 28) / 48) * 0.45);
    }

    let k: number;
    if (face === 0) k = 0.74 + 0.52 * LIGHT[2];
    else if (face === 1) k = 0.48 + 0.38 * (-LIGHT[1] + 0.38);
    else k = 0.36 + 0.38 * (LIGHT[0] + 0.5);
    k *= ao * palette.lightScale;
    if (glow) k = atmosphere === 'after-hours' ? 1.32 : 1.18;

    const tint = face === 0 ? palette.topTint : palette.sideTint;

    let r = rIn * k * tint[0];
    let g2 = gIn * k * tint[1];
    let b = bIn * k * tint[2];

    if (glow) {
        r = Math.min(255, r + 24);
        g2 = Math.min(255, g2 + 12);
        b = Math.min(255, b * 0.72);
    }

    const [fogR, fogG, fogB] = cloud ? palette.cloudFog : palette.islandFog;
    r += (fogR - r) * fog;
    g2 += (fogG - g2) * fog;
    b += (fogB - b) * fog;

    return `rgb(${Math.min(255, r) | 0},${Math.min(255, g2) | 0},${Math.min(255, b) | 0})`;
}

export function paintVoxelLayer(
    list: WorldFaces['island'],
    world: GardenWorld,
    cloudSet: Set<number>,
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
    const HH = scale * 0.28;
    const ZH = scale * 0.4;

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
            cloudSet.has(world.material[i]),
            depthMax,
            atmosphere,
        );
        o.beginPath();
        if (face === 0) {
            o.moveTo(px, py - HH * 2);
            o.lineTo(px + HW, py - HH);
            o.lineTo(px, py);
            o.lineTo(px - HW, py - HH);
        } else {
            const sx = face === 1 ? -HW : HW;
            o.moveTo(px + sx, py - HH);
            o.lineTo(px, py);
            o.lineTo(px, py + ZH * 2);
            o.lineTo(px + sx, py - HH + ZH * 2);
        }
        o.closePath();
        o.fill();
    }
    return off;
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

export function drawAtmosphericParticles(
    ctx: CanvasRenderingContext2D,
    scene: Scene,
    time: number,
    par: number,
    islandParX: number,
    islandParY: number,
) {
    const H = scene.height;
    const palette = ATMOSPHERE_PALETTES[scene.atmosphere];

    // 1. Pond water glints
    for (const g of scene.glints) {
        const a = 0.08 + 0.24 * (0.5 + 0.5 * Math.sin(time * g.speed + g.phase));
        ctx.fillStyle = `rgba(226, 238, 232, ${a.toFixed(3)})`;
        ctx.fillRect(g.x + islandParX, g.y + islandParY, g.size, Math.max(1, g.size * 0.45));
    }

    // 2. Koi swimming water ripple diamonds
    if (scene.koi.length > 0) {
        ctx.strokeStyle = 'rgba(218, 240, 232, 0.32)';
        ctx.lineWidth = 1;
        for (const k of scene.koi) {
            const cycle = (time * 0.45 + k.phase) % 1;
            const rx = (2 + cycle * 6.5) * (scene.scale * 0.12);
            const ry = rx * 0.56;
            const cx = k.x + islandParX + Math.sin(time * 0.6 + k.phase) * 2.5;
            const cy = k.y + islandParY + Math.cos(time * 0.6 + k.phase) * 1.4;
            ctx.globalAlpha = (1 - cycle) * 0.55;
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

    // 3. Stone & torii lantern glow halos
    if (scene.lanternSprite) {
        const r = scene.lanternRadius;
        ctx.globalCompositeOperation = 'lighter';
        for (const l of scene.lamps) {
            const flicker =
                0.78 + 0.22 * Math.sin(time * 2.4 + l.phase) * Math.sin(time * 1.3 + l.phase * 2);
            ctx.globalAlpha = Math.min(1, flicker * palette.lanternAlphaScale);
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

    // 4. Phase-reactive rising fireflies (Dusk & After-Hours)
    if (palette.showFireflies && scene.fireflies.length > 0) {
        const fireflyBoost = scene.atmosphere === 'after-hours' ? 1 : 0.72;
        for (const f of scene.fireflies) {
            const fx = f.x + islandParX + Math.sin(time * f.speed + f.phase) * f.ampX;
            const fy = f.y + islandParY + Math.cos(time * (f.speed * 0.85) + f.phase) * f.ampY;
            const pulse = 0.25 + 0.75 * (0.5 + 0.5 * Math.sin(time * 2.1 + f.phase));
            ctx.fillStyle = f.tint;
            ctx.globalAlpha = pulse * fireflyBoost;
            ctx.fillRect(fx, fy, f.size, f.size);
        }
        ctx.globalAlpha = 1;
    }

    // 5. Drifting cherry blossom petals
    for (const p of scene.petals) {
        const y = p.y + ((time * p.vy * 6.5) % (H + 80)) - 40;
        const x = p.x + Math.sin(time * 0.65 + p.phase) * p.sway + par * 12 * p.depth;
        ctx.fillStyle = p.tint;
        ctx.globalAlpha = 0.45 + 0.28 * Math.sin(time * 0.9 + p.phase);
        ctx.fillRect(x, y, p.size, p.size);
    }
    ctx.globalAlpha = 1;
}
