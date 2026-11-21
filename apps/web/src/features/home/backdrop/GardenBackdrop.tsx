import { type AtmospherePhase, Button } from '@llm-market-bench/ui-design-system';
import { useCallback, useEffect, useRef, useState } from 'react';
import {
    bakeFootFade,
    bakeLanternSprite,
    bakeSky,
    drawAtmosphericParticles,
    drawZenithParticles,
    type Firefly,
    type Petal,
    paintVoxelLayer,
    type Scene,
    type SkyMote,
} from './garden-renderer';
import {
    buildGarden,
    CX,
    CY,
    extractWorldFaces,
    type GardenWorld,
    type WorldFaces,
} from './garden-world';

/**
 * The homepage backdrop: a multi-layered voxel garden island floating across
 * dynamic Matcha & Cedar market-session atmospheres (dawn, daylight, dusk,
 * after-hours) with 4-plane depth parallax and phase-reactive micro-life.
 */

const IDLE_MS = 20_000;
// Slightly below 33.33ms so 60Hz vsync (16.67ms) ticks cleanly at 30fps without 20fps drops.
const FRAME_INTERVAL_MS = 1000 / 30 - 1.5;

let worldCache: GardenWorld | null = null;
let facesCache: WorldFaces | null = null;
const getWorldAndFaces = () => {
    worldCache ??= buildGarden();
    facesCache ??= extractWorldFaces(worldCache);
    return { world: worldCache, faces: facesCache };
};

export interface GardenBackdropProps {
    className?: string;
    /** Active Matcha & Cedar atmosphere phase. Defaults to 'dusk'. */
    atmosphere?: AtmospherePhase;
    /** Optional externally controlled paused state. */
    paused?: boolean;
    /** Notifies parent when reduced/paused state changes. */
    onPausedChange?: (paused: boolean) => void;
    /**
     * Whether to render the floating Pause/Play button inside GardenBackdrop.
     * Defaults to true for standalone usage; set to false when SceneStage renders
     * HUD controls in its foreground `controls` slot outside `aria-hidden`.
     */
    showControls?: boolean;
}

export function GardenBackdrop({
    className,
    atmosphere = 'dusk',
    paused,
    onPausedChange,
    showControls = true,
}: GardenBackdropProps) {
    const canvasRef = useRef<HTMLCanvasElement | null>(null);
    const [reduced, setReduced] = useState(false);
    const sceneRef = useRef<Scene | null>(null);
    const atmosphereRef = useRef<AtmospherePhase>(atmosphere);
    atmosphereRef.current = atmosphere;
    const onPausedChangeRef = useRef(onPausedChange);
    onPausedChangeRef.current = onPausedChange;

    const stateRef = useRef({
        raf: 0,
        running: false,
        idle: 0,
        pointerX: 0,
        pointerY: 0,
        parX: 0,
        parY: 0,
        elapsed: 0,
        lastTick: 0,
        lastPaint: 0,
        reduced: false,
    });

    const paintFrame = useCallback((time: number, par: number, parY = 0) => {
        const canvas = canvasRef.current;
        const scene = sceneRef.current;
        if (!canvas || !scene) return;
        const ctx = canvas.getContext('2d');
        if (!ctx) return;
        const { width: W, height: H } = scene;
        ctx.setTransform(scene.dpr, 0, 0, scene.dpr, 0, 0);
        ctx.clearRect(0, 0, W, H);

        // Plane 1: Atmospheric sky gradient + zenith stars / sun-motes
        if (scene.sky) ctx.drawImage(scene.sky, 0, 0, W, H);
        drawZenithParticles(ctx, scene, time, par);

        // Plane 2: Far high-altitude 3D voxel cloud slabs (slow breeze drift + subtle parallax)
        const farCloudParX = Math.sin(time * 0.08) * 12 + par * 5;
        const farCloudParY = Math.sin(time * 0.12) * 1.2 + parY * 1.4;
        if (scene.cloudsFar) ctx.drawImage(scene.cloudsFar, farCloudParX, farCloudParY, W, H);

        // Plane 3: Floating voxel island with gentle vertical levitation + island micro-life
        const islandParX = par * 3;
        const islandParY = Math.sin(time * 0.45) * 1.8 + parY * 2;
        if (scene.island) ctx.drawImage(scene.island, islandParX, islandParY, W, H);

        drawAtmosphericParticles(ctx, scene, time, par, islandParX, islandParY);

        // Plane 4: Near perimeter 3D voxel cloud slabs (faster breeze drift + deeper parallax)
        const nearCloudParX = Math.sin(time * 0.11 + 1.4) * 18 + par * 9;
        const nearCloudParY = Math.cos(time * 0.15) * 1.6 + parY * 2.6;
        if (scene.cloudsNear) ctx.drawImage(scene.cloudsNear, nearCloudParX, nearCloudParY, W, H);

        if (scene.foot) ctx.drawImage(scene.foot, 0, H * 0.84, W, H * 0.16);
    }, []);

    const buildLayers = useCallback(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const { world, faces } = getWorldAndFaces();
        const activeAtmosphere = atmosphereRef.current;
        const dpr = Math.min(window.devicePixelRatio || 1, 1.25);
        const W = canvas.clientWidth;
        const H = canvas.clientHeight;
        if (!W || !H) return;
        canvas.width = Math.round(W * dpr);
        canvas.height = Math.round(H * dpr);

        const scale = Math.min(W / 96, H / 56);
        const originX = W * 0.5;
        const originY = H * 0.8;
        const project = (x: number, y: number, z: number): [number, number] => [
            originX + (x - CX - (y - CY)) * scale * 0.5,
            originY + (x - CX + (y - CY)) * scale * 0.28 - (z - 18) * scale * 0.4,
        ];

        const cloudSet = new Set(world.cloudMaterials);

        const lanternRadius = Math.max(8, scale * 2.4);
        const petals: Petal[] = world.petals.map(([wx, wy, wz], idx) => {
            const [x, y] = project(wx, wy, wz);
            return {
                x,
                y,
                vy: scale * (0.4 + ((idx * 37) % 100) * 0.0065),
                sway: 4 + ((idx * 53) % 10),
                phase: (idx * 1.17) % 6.28,
                depth: 0.1 + ((idx * 29) % 15) * 0.01,
                size: Math.max(1, Math.round(scale * (0.09 + ((idx * 17) % 6) * 0.01))),
                tint: idx % 2 === 0 ? '#f7cad8' : '#f8e6dc',
            };
        });

        const glints = world.glints.map(([wx, wy, wz], idx) => {
            const [x, y] = project(wx, wy, wz);
            return {
                x,
                y,
                phase: (idx * 0.83) % 6.28,
                speed: 0.5 + ((idx * 41) % 110) * 0.01,
                size: scale * (0.12 + ((idx * 23) % 14) * 0.01),
            };
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
                tint: idx % 3 === 0 ? '#9ef0c0' : '#ffe38e',
            };
        });

        const koi = world.koi.map(([wx, wy, wz], idx) => {
            const [x, y] = project(wx, wy, wz);
            return { x, y, phase: idx * 0.5 };
        });

        const skyMotes: SkyMote[] = Array.from({ length: 26 }, (_, idx) => ({
            x: W * (0.06 + ((idx * 37) % 88) * 0.01),
            y: H * (0.05 + ((idx * 53) % 44) * 0.01),
            phase: (idx * 1.13) % 6.28,
            speed: 0.8 + (idx % 5) * 0.32,
            size: idx % 4 === 0 ? 2 : 1.5,
        }));

        sceneRef.current = {
            width: W,
            height: H,
            dpr,
            scale,
            atmosphere: activeAtmosphere,
            sky: bakeSky(W, H, dpr, activeAtmosphere),
            foot: bakeFootFade(W, H, dpr, activeAtmosphere),
            lanternSprite: bakeLanternSprite(lanternRadius, dpr),
            lanternRadius,
            island: paintVoxelLayer(
                faces.island,
                world,
                cloudSet,
                W,
                H,
                dpr,
                scale,
                project,
                activeAtmosphere,
            ),
            cloudsFar: paintVoxelLayer(
                faces.cloudsFar,
                world,
                cloudSet,
                W,
                H,
                dpr,
                scale,
                project,
                activeAtmosphere,
            ),
            cloudsNear: paintVoxelLayer(
                faces.cloudsNear,
                world,
                cloudSet,
                W,
                H,
                dpr,
                scale,
                project,
                activeAtmosphere,
            ),
            petals,
            glints,
            lamps,
            fireflies,
            koi,
            skyMotes,
        };
        paintFrame(stateRef.current.elapsed, stateRef.current.parX, stateRef.current.parY);
    }, [paintFrame]);

    const stop = useCallback(() => {
        stateRef.current.running = false;
        cancelAnimationFrame(stateRef.current.raf);
    }, []);

    const start = useCallback(() => {
        const s = stateRef.current;
        if (s.reduced || s.running) return;
        s.running = true;
        s.lastTick = performance.now();
        s.lastPaint = 0;
        const tick = (now: number) => {
            if (!s.running) return;
            if (now - s.lastPaint >= FRAME_INTERVAL_MS) {
                const dt = Math.min(0.1, Math.max(0, (now - s.lastTick) / 1000));
                s.lastTick = now;
                s.lastPaint = now;
                s.elapsed += dt;
                s.parX += (s.pointerX - s.parX) * 0.035;
                s.parY += (s.pointerY - s.parY) * 0.035;
                paintFrame(s.elapsed, s.parX, s.parY);
            }
            s.raf = requestAnimationFrame(tick);
        };
        s.raf = requestAnimationFrame(tick);
    }, [paintFrame]);

    const armIdle = useCallback(() => {
        const s = stateRef.current;
        window.clearTimeout(s.idle);
        if (s.reduced) return;
        s.idle = window.setTimeout(() => {
            stop();
            paintFrame(s.elapsed, s.parX, s.parY);
        }, IDLE_MS);
    }, [paintFrame, stop]);

    useEffect(() => {
        const query = window.matchMedia('(prefers-reduced-motion: reduce)');
        const s = stateRef.current;
        s.reduced = query.matches;
        setReduced(query.matches);
        onPausedChangeRef.current?.(query.matches);

        buildLayers();
        if (!query.matches) {
            start();
            armIdle();
        }

        let resizeTimer = 0;
        const onResize = () => {
            window.clearTimeout(resizeTimer);
            resizeTimer = window.setTimeout(() => {
                buildLayers();
                armIdle();
            }, 140);
        };
        const onPointer = (e: PointerEvent) => {
            s.pointerX = (e.clientX / window.innerWidth - 0.5) * 2;
            s.pointerY = (e.clientY / window.innerHeight - 0.5) * 2;
            armIdle();
            if (!s.reduced) start();
        };
        const onKey = () => {
            armIdle();
            if (!s.reduced) start();
        };
        const onVisibility = () => {
            if (document.hidden) stop();
            else if (!s.reduced) {
                start();
                armIdle();
            }
        };
        const onPreference = (e: MediaQueryListEvent) => {
            s.reduced = e.matches;
            setReduced(e.matches);
            onPausedChangeRef.current?.(e.matches);
            if (e.matches) {
                stop();
                paintFrame(s.elapsed, s.parX, s.parY);
            } else {
                start();
                armIdle();
            }
        };

        window.addEventListener('resize', onResize);
        const observer = new ResizeObserver(onResize);
        const canvasEl = canvasRef.current;
        if (canvasEl) observer.observe(canvasEl);
        window.addEventListener('pointermove', onPointer, { passive: true });
        window.addEventListener('keydown', onKey);
        window.addEventListener('touchstart', onKey, { passive: true });
        document.addEventListener('visibilitychange', onVisibility);
        query.addEventListener('change', onPreference);

        return () => {
            window.removeEventListener('resize', onResize);
            window.clearTimeout(resizeTimer);
            observer.disconnect();
            window.removeEventListener('pointermove', onPointer);
            window.removeEventListener('keydown', onKey);
            window.removeEventListener('touchstart', onKey);
            document.removeEventListener('visibilitychange', onVisibility);
            query.removeEventListener('change', onPreference);
            window.clearTimeout(s.idle);
            stop();
        };
    }, [armIdle, buildLayers, paintFrame, start, stop]);

    // Rebuild sky & voxel lighting layers whenever the active atmosphere phase changes
    useEffect(() => {
        if (sceneRef.current && sceneRef.current.atmosphere !== atmosphere) {
            buildLayers();
        }
    }, [atmosphere, buildLayers]);

    // Sync optional externally controlled paused prop (when parent hosts HUD controls)
    useEffect(() => {
        if (paused === undefined) return;
        const s = stateRef.current;
        if (s.reduced === paused) return;
        s.reduced = paused;
        setReduced(paused);
        if (paused) {
            window.clearTimeout(s.idle);
            stop();
            paintFrame(s.elapsed, s.parX, s.parY);
        } else {
            start();
            armIdle();
        }
    }, [armIdle, paintFrame, paused, start, stop]);

    const toggle = useCallback(() => {
        const s = stateRef.current;
        const next = !s.reduced;
        s.reduced = next;
        setReduced(next);
        onPausedChangeRef.current?.(next);
        if (next) {
            window.clearTimeout(s.idle);
            stop();
            paintFrame(s.elapsed, s.parX, s.parY);
        } else {
            start();
            armIdle();
        }
    }, [armIdle, paintFrame, start, stop]);

    return (
        <>
            <canvas
                ref={canvasRef}
                className={className}
                data-testid="garden-backdrop"
                data-atmosphere={atmosphere}
            />
            {showControls ? (
                <div className="pointer-events-auto absolute right-3 bottom-3 z-20">
                    <Button
                        type="button"
                        onClick={toggle}
                        variant="outline"
                        colorScheme="neutral"
                        size="sm"
                    >
                        {reduced ? 'Play motion' : 'Pause motion'}
                    </Button>
                </div>
            ) : null}
        </>
    );
}
