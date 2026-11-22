import type { AtmospherePhase } from '@llm-market-bench/ui-design-system';
import {
    bakeCloudSprites,
    bakeFootFade,
    bakeLanternSprite,
    bakeSky,
    type CloudSprite,
    cloudAlphaAt,
    cloudDriftAt,
    disposeCanvas,
    drawAtmosphericParticles,
    drawZenithParticles,
    type Firefly,
    type IslandVerticalBounds,
    type Petal,
    paintVoxelLayer,
    pickCedarDriftColor,
    pickCedarFloaterColor,
    type Scene,
    type SkyMote,
} from './garden-renderer';
import {
    CEDAR_WORLD_ID,
    CEDAR_WORLD_META,
    CX,
    CY,
    type RenderableWorld,
    type WorldFaces,
} from './voxel-world';

export const ENTRANCE_DURATION_S = 1.1;

export type EntranceState = { kind: 'animating'; elapsed: number } | { kind: 'settled' };

export interface IslandRevealFrame {
    isSettled: boolean;
    alpha: number;
    settleOffsetY: number;
    columnTopYs: number[];
}

/** Smoothly lowers portrait mobile framing toward `0.82 * H` while leaving landscape at `0.68 * H`. */
export function computeCedarFraming(width: number, height: number) {
    const safeW = Math.max(1, width);
    const safeH = Math.max(1, height);
    const scale = Math.min(safeW / 92, safeH / 46);
    const portraitBlend = Math.max(0, Math.min(1, (1 - safeW / safeH) / 0.3));
    return { scale, originX: safeW * 0.5, originY: safeH * (0.68 + 0.14 * portraitBlend) };
}

const SETTLED_REVEAL_FRAME: IslandRevealFrame = Object.freeze({
    isSettled: true,
    alpha: 1,
    settleOffsetY: 0,
    columnTopYs: [],
}) as IslandRevealFrame;

/** Computes projected island vertical pixel bounds including upward parallax headroom. */
export function computeIslandVerticalBounds(
    faces: WorldFaces['island'],
    project: (x: number, y: number, z: number) => [number, number],
    scale: number,
    canvasHeight: number,
): IslandVerticalBounds {
    if (faces.length === 0) return { minY: 0, maxY: canvasHeight };
    let minY = Number.POSITIVE_INFINITY;
    let maxY = Number.NEGATIVE_INFINITY;
    const padTop = scale * 0.8 + 6;
    const padBottom = scale * 1.1;
    for (const face of faces) {
        const [, x, y, z] = face;
        const [, py] = project(x, y, z);
        if (py - padTop < minY) minY = py - padTop;
        if (py + padBottom > maxY) maxY = py + padBottom;
    }
    return { minY: Math.max(0, Math.floor(minY)), maxY: Math.min(canvasHeight, Math.ceil(maxY)) };
}

/** Advances `EntranceState` only once a sized scene exists, preventing offscreen entrance burn-in. */
export function stepEntranceState(
    entrance: EntranceState,
    hasScene: boolean,
    dt: number,
): EntranceState {
    if (!hasScene || entrance.kind === 'settled') return entrance;
    const nextElapsed = entrance.elapsed + dt;
    return nextElapsed >= ENTRANCE_DURATION_S
        ? { kind: 'settled' }
        : { kind: 'animating', elapsed: nextElapsed };
}

/** Computes normalized entrance progress in `[0, 1]`. */
export function computeEntranceProgress(entrance: EntranceState): number {
    if (entrance.kind === 'settled') return 1;
    return Math.max(0, Math.min(1, entrance.elapsed / ENTRANCE_DURATION_S));
}

/** Fades ambient clouds and atmospheric micro-life smoothly during the entrance reveal. */
export function computeAmbientEntranceAlpha(entrance: EntranceState): number {
    if (entrance.kind === 'settled') return 1;
    const delayed = Math.max(0, Math.min(1, (computeEntranceProgress(entrance) - 0.35) / 0.65));
    return 1 - (1 - delayed) ** 2;
}

/** Computes a quantized bottom-to-top reveal clip on the single painter-sorted island canvas. */
export function computeIslandRevealFrame(
    entrance: EntranceState,
    bounds: IslandVerticalBounds,
    scale: number,
    columnCount = 18,
): IslandRevealFrame {
    if (entrance.kind === 'settled') return SETTLED_REVEAL_FRAME;
    const progress = computeEntranceProgress(entrance);
    const eased = 1 - (1 - progress) ** 3;
    const spanY = Math.max(1, bounds.maxY - bounds.minY);
    const stepPx = Math.max(4, Math.round(scale * 2.2));
    const settleOffsetY = (1 - eased) * Math.max(8, scale * 2.4);
    const alpha = Math.min(1, eased * 1.25);

    const safeCols = Math.max(1, columnCount);
    const columnTopYs: number[] = [];
    for (let i = 0; i < safeCols; i++) {
        const distFromCenter = Math.abs(i / (safeCols - 1 || 1) - 0.5) * 2;
        const colDelay = Math.min(0.24, distFromCenter * 0.14 + ((i * 7 + 3) % 5) * 0.025);
        const colLocal = Math.max(0, Math.min(1, (progress - colDelay) / (1 - colDelay)));
        const colEased = 1 - (1 - colLocal) ** 3;
        const rawTop = bounds.maxY - spanY * colEased;
        const top =
            colLocal <= 0
                ? bounds.maxY
                : colEased >= 0.98
                  ? 0
                  : Math.max(bounds.minY, Math.floor(rawTop / stepPx) * stepPx);
        columnTopYs.push(top);
    }

    return { isSettled: false, alpha, settleOffsetY, columnTopYs };
}

function drawSteppedIslandReveal(
    ctx: CanvasRenderingContext2D,
    scene: Scene,
    entrance: EntranceState,
    islandParX: number,
    islandParY: number,
) {
    if (!scene.island) return;
    const { width: W, height: H, islandBounds, scale } = scene;
    const reveal = computeIslandRevealFrame(entrance, islandBounds, scale);
    if (reveal.isSettled) {
        ctx.drawImage(scene.island, islandParX, islandParY, W, H);
        return;
    }
    if (reveal.alpha <= 0) return;

    ctx.save();
    ctx.beginPath();
    const colW = W / reveal.columnTopYs.length;
    for (let i = 0; i < reveal.columnTopYs.length; i++) {
        const topY = reveal.columnTopYs[i];
        if (topY < H) ctx.rect(i * colW, topY, Math.ceil(colW) + 1, H - topY);
    }
    ctx.clip();
    ctx.globalAlpha = reveal.alpha;
    ctx.drawImage(scene.island, islandParX, islandParY + reveal.settleOffsetY, W, H);
    ctx.restore();
    ctx.globalAlpha = 1;
}

/** Draws one cloud plane; each sprite drifts in its own lane and fades out of the copy column. */
function drawCloudSprites(
    ctx: CanvasRenderingContext2D,
    sprites: CloudSprite[],
    time: number,
    parX: number,
    parY: number,
    alphaScale: number,
    W: number,
    H: number,
) {
    if (alphaScale <= 0) return;
    for (const sprite of sprites) {
        const { x } = cloudDriftAt(sprite.lane, sprite.speed, sprite.phase, time);
        const alpha = cloudAlphaAt(sprite, sprite.lane, x);
        const finalAlpha = alpha * alphaScale;
        if (finalAlpha <= 0.002) continue;
        ctx.globalAlpha = finalAlpha;
        ctx.drawImage(
            sprite.canvas,
            x + parX * sprite.parallax * 1.8,
            sprite.y + parY * sprite.parallax,
            sprite.width,
            sprite.height,
        );
    }
    ctx.globalAlpha = 1;
}

/** Composites one complete diorama frame with single-island stepped entrance reveal and parallax. */
export function drawCedarSceneFrame(
    ctx: CanvasRenderingContext2D,
    scene: Scene,
    time: number,
    parX: number,
    parY: number,
    entrance: EntranceState,
) {
    const { width: W, height: H } = scene;
    ctx.setTransform(scene.dpr, 0, 0, scene.dpr, 0, 0);
    ctx.clearRect(0, 0, W, H);

    if (scene.sky) ctx.drawImage(scene.sky, 0, 0, W, H);
    drawZenithParticles(ctx, scene, time, parX);

    const ambientAlpha = computeAmbientEntranceAlpha(entrance);
    drawCloudSprites(ctx, scene.cloudsFar, time, parX, parY, ambientAlpha, W, H);

    const islandParX = parX * 3;
    const islandParY = Math.sin(time * 0.45) * 1.8 + parY * 2;
    drawSteppedIslandReveal(ctx, scene, entrance, islandParX, islandParY);
    drawAtmosphericParticles(ctx, scene, time, parX, islandParX, islandParY, ambientAlpha);

    drawCloudSprites(ctx, scene.cloudsNear, time, parX, parY, ambientAlpha, W, H);

    if (scene.foot) ctx.drawImage(scene.foot, 0, H * 0.84, W, H * 0.16);
}

function projectSceneParticles(
    world: RenderableWorld,
    scale: number,
    width: number,
    height: number,
    project: (x: number, y: number, z: number) => [number, number],
    prevSkyMotes: SkyMote[] | null,
) {
    const petals: Petal[] = world.petals.map(([wx, wy, wz], idx) => {
        const [x, y] = project(wx, wy, wz);
        const vy = scale * (0.36 + ((idx * 37) % 100) * 0.0055);
        const size = Math.max(1.5, Math.round(scale * (0.09 + ((idx * 17) % 6) * 0.01)));
        const sway = 4 + ((idx * 53) % 10);
        const phase = (idx * 1.17) % 6.28;
        const depth = 0.1 + ((idx * 29) % 15) * 0.01;
        return { x, y, vy, sway, phase, depth, size, tint: pickCedarDriftColor(idx) };
    });
    const glints = world.glints.map(([wx, wy, wz], idx) => {
        const [x, y] = project(wx, wy, wz);
        const phase = (idx * 0.83) % 6.28;
        const speed = 0.5 + ((idx * 41) % 110) * 0.01;
        const size = scale * (0.12 + ((idx * 23) % 14) * 0.01);
        return { x, y, phase, speed, size };
    });
    const lamps = world.lamps.map(([wx, wy, wz], idx) => {
        const [x, y] = project(wx, wy, wz);
        return { x, y, phase: (idx * 1.41) % 6.28 };
    });
    const fireflies: Firefly[] = world.fireflies.map(([wx, wy, wz], idx) => {
        const [x, y] = project(wx, wy, wz);
        return {
            x,
            y,
            ampX: 3 + (idx % 5) * 1.4,
            ampY: 2.5 + (idx % 4) * 1.2,
            speed: 0.7 + (idx % 6) * 0.18,
            phase: (idx * 0.97) % 6.28,
            size: Math.max(1.5, Math.round(scale * 0.13)),
            tint: pickCedarFloaterColor(idx),
        };
    });
    const koi = world.koi.map(([wx, wy, wz], idx) => {
        const [x, y] = project(wx, wy, wz);
        return { x, y, phase: idx * 0.5 };
    });
    const skyMotes: SkyMote[] =
        prevSkyMotes ??
        Array.from({ length: 26 }, (_, idx) => ({
            x: width * (0.06 + ((idx * 37) % 88) * 0.01),
            y: height * (0.05 + ((idx * 53) % 44) * 0.01),
            phase: (idx * 1.13) % 6.28,
            speed: 0.8 + (idx % 5) * 0.32,
            size: idx % 4 === 0 ? 2 : 1.5,
        }));
    return { petals, glints, lamps, fireflies, koi, skyMotes };
}

function disposeAtmoLayers(prev: Scene) {
    disposeCanvas(prev.sky);
    disposeCanvas(prev.foot);
    disposeCanvas(prev.island);
    for (const sprite of [...prev.cloudsFar, ...prev.cloudsNear]) disposeCanvas(sprite.canvas);
}

function resolveAtmoLayers(
    world: RenderableWorld,
    faces: WorldFaces,
    dims: { width: number; height: number; dpr: number; scale: number },
    atmosphere: AtmospherePhase,
    project: (x: number, y: number, z: number) => [number, number],
    prev: Scene | null,
    atmoSame: boolean,
) {
    if (atmoSame && prev) {
        return {
            sky: prev.sky,
            foot: prev.foot,
            island: prev.island,
            cloudsFar: prev.cloudsFar,
            cloudsNear: prev.cloudsNear,
        };
    }
    if (prev) disposeAtmoLayers(prev);
    const { width, height, dpr, scale } = dims;
    const cloudSprites = bakeCloudSprites(faces, world, dims, project, atmosphere);
    return {
        sky: bakeSky(width, height, dpr, atmosphere),
        foot: bakeFootFade(width, height, dpr, atmosphere),
        island: paintVoxelLayer(
            faces.island,
            world,
            width,
            height,
            dpr,
            scale,
            project,
            atmosphere,
        ),
        cloudsFar: cloudSprites.far,
        cloudsNear: cloudSprites.near,
    };
}

/** Builds offscreen canvas layers and projected anchors, freeing stale buffers before allocation. */
export function buildCedarScene(
    world: RenderableWorld,
    faces: WorldFaces,
    width: number,
    height: number,
    dpr: number,
    atmosphere: AtmospherePhase,
    prev: Scene | null,
): Scene {
    const sizeSame =
        prev !== null && prev.width === width && prev.height === height && prev.dpr === dpr;
    const atmoSame = sizeSame && prev.atmosphere === atmosphere;
    const { scale, originX, originY } = computeCedarFraming(width, height);
    const project = (x: number, y: number, z: number): [number, number] => [
        originX + (x - CX - (y - CY)) * scale * 0.5,
        originY + (x - CX + (y - CY)) * scale * 0.34 - (z - 16) * scale * 0.46,
    ];
    const lanternRadius = Math.max(8, scale * 2.4);
    const islandBounds =
        sizeSame && prev
            ? prev.islandBounds
            : computeIslandVerticalBounds(faces.island, project, scale, height);
    const particles = projectSceneParticles(
        world,
        scale,
        width,
        height,
        project,
        sizeSame && prev ? prev.skyMotes : null,
    );
    let lanternSprite = sizeSame && prev ? prev.lanternSprite : null;
    if (!sizeSame) {
        if (prev) disposeCanvas(prev.lanternSprite);
        lanternSprite = bakeLanternSprite(lanternRadius, dpr, CEDAR_WORLD_META.glowRgb);
    }
    const atmoLayers = resolveAtmoLayers(
        world,
        faces,
        { width, height, dpr, scale },
        atmosphere,
        project,
        prev,
        atmoSame,
    );

    return {
        width,
        height,
        dpr,
        scale,
        worldId: CEDAR_WORLD_ID,
        atmosphere,
        lanternSprite,
        lanternRadius,
        islandBounds,
        ...atmoLayers,
        ...particles,
    };
}
