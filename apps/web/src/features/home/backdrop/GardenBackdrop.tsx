import { Button } from '@llm-market-bench/ui-design-system';
import { useCallback, useEffect, useRef, useState } from 'react';
import {
    bakeFootFade,
    bakeLanternSprite,
    bakeSky,
    drawAtmosphericParticles,
    type Petal,
    paintVoxelLayer,
    type Scene,
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
 * The homepage backdrop: a voxel garden island floating in golden-hour Matcha
 * dusk with 3D Minecraft-style voxel cloud slabs.
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
}

export function GardenBackdrop({ className }: GardenBackdropProps) {
    const canvasRef = useRef<HTMLCanvasElement | null>(null);
    const [reduced, setReduced] = useState(false);
    const sceneRef = useRef<Scene | null>(null);
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

        if (scene.sky) ctx.drawImage(scene.sky, 0, 0, W, H);

        const cloudParX = par * 8;
        const cloudParY = Math.sin(time * 0.14) * 1.5 + parY * 2;
        const islandParX = par * 3;
        const islandParY = parY * 2;

        if (scene.clouds) ctx.drawImage(scene.clouds, cloudParX, cloudParY, W, H);
        if (scene.island) ctx.drawImage(scene.island, islandParX, islandParY, W, H);

        drawAtmosphericParticles(ctx, scene, time, par, islandParX, islandParY);

        if (scene.foot) ctx.drawImage(scene.foot, 0, H * 0.84, W, H * 0.16);
    }, []);

    const buildLayers = useCallback(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const { world, faces } = getWorldAndFaces();
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
        const petals: Petal[] = world.petals.map(([wx, wy, wz]) => {
            const [x, y] = project(wx, wy, wz);
            return {
                x,
                y,
                vy: scale * (0.4 + Math.random() * 0.65),
                sway: 4 + Math.random() * 10,
                phase: Math.random() * 6.28,
                depth: 0.1 + Math.random() * 0.15,
                size: Math.max(1, Math.round(scale * (0.09 + Math.random() * 0.06))),
                tint: Math.random() < 0.5 ? '#f7cad8' : '#f8e6dc',
            };
        });

        const glints = world.glints.map(([wx, wy, wz]) => {
            const [x, y] = project(wx, wy, wz);
            return {
                x,
                y,
                phase: Math.random() * 6.28,
                speed: 0.5 + Math.random() * 1.1,
                size: scale * (0.12 + Math.random() * 0.14),
            };
        });

        const lamps = world.lamps.map(([wx, wy, wz]) => {
            const [x, y] = project(wx, wy, wz);
            return { x, y, phase: Math.random() * 6.28 };
        });

        sceneRef.current = {
            width: W,
            height: H,
            dpr,
            scale,
            sky: bakeSky(W, H, dpr),
            foot: bakeFootFade(W, H, dpr),
            lanternSprite: bakeLanternSprite(lanternRadius, dpr),
            lanternRadius,
            island: paintVoxelLayer(faces.island, world, cloudSet, W, H, dpr, scale, project),
            clouds: paintVoxelLayer(faces.clouds, world, cloudSet, W, H, dpr, scale, project),
            petals,
            glints,
            lamps,
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

    const toggle = useCallback(() => {
        const s = stateRef.current;
        s.reduced = !s.reduced;
        setReduced(s.reduced);
        if (s.reduced) {
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
            <canvas ref={canvasRef} className={className} data-testid="garden-backdrop" />
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
        </>
    );
}
