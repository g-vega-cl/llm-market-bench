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

export interface Scene {
    width: number;
    height: number;
    dpr: number;
    scale: number;
    sky: HTMLCanvasElement | null;
    foot: HTMLCanvasElement | null;
    lanternSprite: HTMLCanvasElement | null;
    lanternRadius: number;
    island: HTMLCanvasElement | null;
    clouds: HTMLCanvasElement | null;
    petals: Petal[];
    glints: Array<{ x: number; y: number; phase: number; speed: number; size: number }>;
    lamps: Array<{ x: number; y: number; phase: number }>;
}

export function bakeSky(W: number, H: number, dpr: number): HTMLCanvasElement | null {
    const off = document.createElement('canvas');
    off.width = Math.round(W * dpr);
    off.height = Math.round(H * dpr);
    const ctx = off.getContext('2d');
    if (!ctx) return null;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    // Atmospheric twilight / golden-hour Matcha dusk sky
    const sky = ctx.createLinearGradient(0, 0, 0, H);
    sky.addColorStop(0, '#0c1715');
    sky.addColorStop(0.24, '#142622');
    sky.addColorStop(0.45, '#23413b');
    sky.addColorStop(0.64, '#45675f');
    sky.addColorStop(0.78, '#819587');
    sky.addColorStop(0.88, '#b59a78');
    sky.addColorStop(1, '#22332e');
    ctx.fillStyle = sky;
    ctx.fillRect(0, 0, W, H);

    // Subtle warm golden-hour horizon glow centered behind the island silhouette
    const glow = ctx.createRadialGradient(
        W * 0.5,
        H * 0.84,
        W * 0.04,
        W * 0.5,
        H * 0.84,
        Math.max(W, H) * 0.55,
    );
    glow.addColorStop(0, 'rgba(240, 184, 108, 0.22)');
    glow.addColorStop(0.48, 'rgba(214, 162, 102, 0.08)');
    glow.addColorStop(1, 'rgba(214, 162, 102, 0)');
    ctx.fillStyle = glow;
    ctx.fillRect(0, 0, W, H);

    // Gentle top atmospheric vignette so open-sky cream typography reads cleanly
    const topVignette = ctx.createLinearGradient(0, 0, 0, H * 0.44);
    topVignette.addColorStop(0, 'rgba(8, 16, 14, 0.44)');
    topVignette.addColorStop(0.6, 'rgba(8, 16, 14, 0.18)');
    topVignette.addColorStop(1, 'rgba(8, 16, 14, 0)');
    ctx.fillStyle = topVignette;
    ctx.fillRect(0, 0, W, H * 0.44);

    return off;
}

export function bakeFootFade(W: number, H: number, dpr: number): HTMLCanvasElement | null {
    const bandH = Math.max(1, Math.round(H * 0.16));
    const off = document.createElement('canvas');
    off.width = Math.round(W * dpr);
    off.height = Math.round(bandH * dpr);
    const ctx = off.getContext('2d');
    if (!ctx) return null;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    const foot = ctx.createLinearGradient(0, 0, 0, bandH);
    foot.addColorStop(0, 'rgba(12, 22, 20, 0)');
    foot.addColorStop(1, 'rgba(12, 22, 20, 0.42)');
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
): string {
    let fog = Math.min(0.16, Math.max(0, (x + y) / depthMax - 0.72) * 0.7);
    if (cloud) {
        const dist = Math.hypot(x - CX, y - CY);
        fog = Math.min(0.45, Math.max(0, (dist - 28) / 48) * 0.45);
    }

    let k: number;
    if (face === 0) k = 0.74 + 0.52 * LIGHT[2];
    else if (face === 1) k = 0.48 + 0.38 * (-LIGHT[1] + 0.38);
    else k = 0.36 + 0.38 * (LIGHT[0] + 0.5);
    k *= ao;
    if (glow) k = 1.18;

    const warmR = face === 0 ? 1.04 : 0.95;
    const warmG = face === 0 ? 1.01 : 0.99;
    const warmB = face === 0 ? 0.93 : 1.04;

    let r = rIn * k * warmR;
    let g2 = gIn * k * warmG;
    let b = bIn * k * warmB;

    if (glow) {
        r = Math.min(255, r + 20);
        g2 = Math.min(255, g2 + 10);
        b = Math.min(255, b * 0.72);
    }

    const fogR = cloud ? 132 : 52;
    const fogG = cloud ? 138 : 74;
    const fogB = cloud ? 124 : 70;
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

export function drawAtmosphericParticles(
    ctx: CanvasRenderingContext2D,
    scene: Scene,
    time: number,
    par: number,
    islandParX: number,
    islandParY: number,
) {
    const H = scene.height;
    for (const g of scene.glints) {
        const a = 0.08 + 0.24 * (0.5 + 0.5 * Math.sin(time * g.speed + g.phase));
        ctx.fillStyle = `rgba(226, 238, 232, ${a.toFixed(3)})`;
        ctx.fillRect(g.x + islandParX, g.y + islandParY, g.size, Math.max(1, g.size * 0.45));
    }

    if (scene.lanternSprite) {
        const r = scene.lanternRadius;
        ctx.globalCompositeOperation = 'lighter';
        for (const l of scene.lamps) {
            const flicker =
                0.78 + 0.22 * Math.sin(time * 2.4 + l.phase) * Math.sin(time * 1.3 + l.phase * 2);
            ctx.globalAlpha = flicker;
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

    for (const p of scene.petals) {
        const y = p.y + ((time * p.vy * 6.5) % (H + 80)) - 40;
        const x = p.x + Math.sin(time * 0.65 + p.phase) * p.sway + par * 12 * p.depth;
        ctx.fillStyle = p.tint;
        ctx.globalAlpha = 0.45 + 0.28 * Math.sin(time * 0.9 + p.phase);
        ctx.fillRect(x, y, p.size, p.size);
    }
    ctx.globalAlpha = 1;
}
