import { Button } from '@llm-market-bench/ui-design-system';
import { useCallback, useEffect, useRef, useState } from 'react';
import { buildGarden, CX, CY, type GardenWorld, SX, SY, SZ } from './garden-world';

/**
 * The homepage backdrop: a voxel garden island floating in cloud.
 *
 * Geometry is painted once into two offscreen layers (island, clouds); each frame
 * only composites them at different offsets, so the parallax costs two blits. One
 * rAF, stopped when idle or hidden, and never started for reduced-motion users —
 * they get a single painted frame instead of a blank rectangle.
 */

const LIGHT: [number, number, number] = (() => {
    const v: [number, number, number] = [-0.42, -0.55, 0.72];
    const m = Math.hypot(v[0], v[1], v[2]);
    return [v[0] / m, v[1] / m, v[2] / m];
})();

interface Petal {
    x: number;
    y: number;
    vy: number;
    sway: number;
    phase: number;
    depth: number;
    size: number;
    tint: string;
}

interface Scene {
    width: number;
    height: number;
    dpr: number;
    scale: number;
    originX: number;
    originY: number;
    island: HTMLCanvasElement | null;
    clouds: HTMLCanvasElement | null;
    petals: Petal[];
    glints: Array<{ x: number; y: number; phase: number; speed: number; size: number }>;
    lamps: Array<{ x: number; y: number; phase: number }>;
}

const IDLE_MS = 20_000;

let worldCache: GardenWorld | null = null;
const getWorld = () => {
    worldCache ??= buildGarden();
    return worldCache;
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
        t0: 0,
        reduced: false,
    });

    const paintFrame = useCallback((time: number, par: number, parY = 0) => {
        const canvas = canvasRef.current;
        const scene = sceneRef.current;
        if (!canvas || !scene) return;
        const ctx = canvas.getContext('2d');
        if (!ctx) return;
        const { width: W, height: H, scale: S } = scene;
        ctx.setTransform(scene.dpr, 0, 0, scene.dpr, 0, 0);
        ctx.clearRect(0, 0, W, H);

        /* sky ------------------------------------------------------------ */
        const sky = ctx.createLinearGradient(0, 0, 0, H);
        sky.addColorStop(0, '#0a1614');
        sky.addColorStop(0.16, '#12251f');
        sky.addColorStop(0.34, '#26463f');
        sky.addColorStop(0.5, '#4b7268');
        sky.addColorStop(0.64, '#7ba095');
        sky.addColorStop(0.78, '#9dbbb0');
        sky.addColorStop(1, '#6d8d84');
        ctx.fillStyle = sky;
        ctx.fillRect(0, 0, W, H);

        const farBanks: Array<[number, number, number, string, number, number]> = [
            [0.3, 0.2, 0.2, '#5d8079', 0.006, 4],
            [0.4, 0.18, 0.34, '#8fb0a6', 0.01, 7],
            [0.5, 0.22, 0.46, '#c3d5cd', 0.016, 11],
            [0.6, 0.18, 0.4, '#e6eee9', 0.024, 16],
            [0.7, 0.16, 0.24, '#c9d8d1', 0.034, 22],
        ];
        for (const [yRel, hRel, alpha, tint, drift, speed] of farBanks) {
            const yBase = H * yRel;
            const h = H * hRel;
            ctx.fillStyle = tint;
            ctx.globalAlpha = alpha;
            const shift = time * speed + par * 240 * drift;
            let bx = -60 - (shift % 320);
            while (bx < W + 60) {
                const bw = 90 + (Math.sin(bx * 0.07) + 1) * 110;
                const bh = h * (0.62 + (Math.sin(bx * 0.11) + 1) * 0.24);
                for (let k = 0; k < 5; k++) {
                    const sw = bw * (1 - k * 0.14);
                    const sx = bx + (bw - sw) * 0.5;
                    ctx.fillRect(sx, yBase - bh * (k / 5), sw, bh / 5 + 2);
                }
                bx += bw * 0.62;
            }
            ctx.globalAlpha = 1;
        }

        for (let layer = 0; layer < 2; layer++) {
            const yb = H * (0.8 + layer * 0.11);
            ctx.fillStyle = layer === 0 ? 'rgba(214,226,220,0.30)' : 'rgba(236,242,238,0.24)';
            let bx = -80 - ((time * (6 + layer * 9) + par * 260 * (0.02 + layer * 0.02)) % 260);
            while (bx < W + 80) {
                const bw = 120 + (Math.cos(bx * 0.05) + 1) * 100;
                const bh = 22 + (Math.sin(bx * 0.09) + 1) * 15;
                for (let k = 0; k < 4; k++) {
                    const sw = bw * (1 - k * 0.16);
                    ctx.fillRect(bx + (bw - sw) * 0.5, yb - bh * (k / 4), sw, bh / 4 + 3);
                }
                bx += bw * 0.7;
            }
        }

        /* the model: clouds and island at different rates ----------------- */
        // Explicit CSS size: the offscreen bitmaps are W*dpr wide and this context
        // is already scaled by dpr, so an implicit drawImage would double-scale.
        if (scene.clouds) {
            ctx.drawImage(scene.clouds, par * 26, Math.sin(time * 0.18) * 2 + parY * 4, W, H);
        }
        if (scene.island) ctx.drawImage(scene.island, par * 9, parY * 6, W, H);

        for (const g of scene.glints) {
            const a = 0.1 + 0.3 * (0.5 + 0.5 * Math.sin(time * g.speed + g.phase));
            ctx.fillStyle = `rgba(206,240,246,${a.toFixed(3)})`;
            ctx.fillRect(g.x + par * 9, g.y, g.size, Math.max(1, g.size * 0.5));
        }

        ctx.globalCompositeOperation = 'lighter';
        for (const l of scene.lamps) {
            const flicker =
                0.72 + 0.28 * Math.sin(time * 3.1 + l.phase) * Math.sin(time * 1.7 + l.phase * 2);
            const r = S * 1.9;
            const g = ctx.createRadialGradient(l.x + par * 9, l.y, 1, l.x + par * 9, l.y, r);
            g.addColorStop(0, `rgba(255,196,110,${(0.075 * flicker).toFixed(3)})`);
            g.addColorStop(1, 'rgba(255,196,110,0)');
            ctx.fillStyle = g;
            ctx.beginPath();
            ctx.arc(l.x + par * 9, l.y, r, 0, 6.2832);
            ctx.fill();
        }
        ctx.globalCompositeOperation = 'source-over';

        for (const p of scene.petals) {
            const y = p.y + ((time * p.vy * 12) % (H + 80)) - 40;
            const x = p.x + Math.sin(time * 0.9 + p.phase) * p.sway + par * 40 * p.depth;
            ctx.fillStyle = p.tint;
            ctx.globalAlpha = 0.55 + 0.35 * Math.sin(time * 1.3 + p.phase);
            ctx.fillRect(x, y, p.size, p.size);
        }
        ctx.globalAlpha = 1;

        /* scrims: the headline needs a dark band, the foot needs quiet ----- */
        const bottom = ctx.createLinearGradient(0, H * 0.52, 0, H);
        bottom.addColorStop(0, 'rgba(11,18,32,0)');
        bottom.addColorStop(1, 'rgba(11,18,32,0.58)');
        ctx.fillStyle = bottom;
        ctx.fillRect(0, H * 0.52, W, H * 0.48);

        const top = ctx.createLinearGradient(0, 0, 0, H * 0.62);
        top.addColorStop(0, 'rgba(8,18,16,0.90)');
        top.addColorStop(0.55, 'rgba(8,18,16,0.62)');
        top.addColorStop(1, 'rgba(8,18,16,0)');
        ctx.fillStyle = top;
        ctx.fillRect(0, 0, W, H * 0.62);
    }, []);

    const buildLayers = useCallback(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const world = getWorld();
        const dpr = Math.min(window.devicePixelRatio || 1, 1.25);
        const W = canvas.clientWidth;
        const H = canvas.clientHeight;
        // A zero-size mount (collapsed split, hidden ancestor) must not bake a
        // viewport-shaped bitmap that only a window resize could correct.
        if (!W || !H) return;
        canvas.width = Math.round(W * dpr);
        canvas.height = Math.round(H * dpr);

        const scale = Math.min(W / 92, H / 52);
        const originX = W * 0.5;
        const originY = H * 0.8;
        const project = (x: number, y: number, z: number): [number, number] => [
            originX + (x - CX - (y - CY)) * scale * 0.5,
            originY + (x - CX + (y - CY)) * scale * 0.28 - (z - 18) * scale * 0.4,
        ];

        const cloudSet = new Set(world.cloudMaterials);
        const isCloud = (id: number) => cloudSet.has(id);

        const faces: { island: number[][]; clouds: number[][] } = { island: [], clouds: [] };
        const solidAt = (x: number, y: number, z: number) =>
            x >= 0 &&
            x < SX &&
            y >= 0 &&
            y < SY &&
            z >= 0 &&
            z < SZ &&
            world.solid[(z * SY + y) * SX + x] === 1;

        for (let z = 0; z < SZ; z++)
            for (let y = 0; y < SY; y++)
                for (let x = 0; x < SX; x++) {
                    const i = (z * SY + y) * SX + x;
                    if (!world.solid[i]) continue;
                    const bucket = isCloud(world.material[i]) ? faces.clouds : faces.island;
                    const key = x + y + z;
                    if (!solidAt(x, y, z + 1)) bucket.push([key, x, y, z, 0, i]);
                    if (!solidAt(x, y + 1, z)) bucket.push([key, x, y, z, 1, i]);
                    if (!solidAt(x + 1, y, z)) bucket.push([key, x, y, z, 2, i]);
                }
        faces.island.sort((a, b) => a[0] - b[0]);
        faces.clouds.sort((a, b) => a[0] - b[0]);

        const occlusion = (x: number, y: number, z: number, face: number) => {
            let n = 0;
            if (face === 0) {
                for (const [dx, dy] of [
                    [1, 0],
                    [-1, 0],
                    [0, 1],
                    [0, -1],
                ])
                    if (solidAt(x + dx, y + dy, z + 1)) n++;
                return 1 - n * 0.055;
            }
            if (face === 1) {
                for (const [dx, dz] of [
                    [0, 1],
                    [0, -1],
                    [-1, 0],
                ])
                    if (solidAt(x + dx, y + 1, z + dz)) n++;
                return 1 - n * 0.075;
            }
            for (const [dy, dz] of [
                [0, 1],
                [0, -1],
                [1, 0],
            ])
                if (solidAt(x + 1, y + dy, z + dz)) n++;
            return 1 - n * 0.075;
        };

        const paint = (list: number[][]) => {
            const off = document.createElement('canvas');
            off.width = Math.round(W * dpr);
            off.height = Math.round(H * dpr);
            const o = off.getContext('2d');
            if (!o) return null;
            o.setTransform(dpr, 0, 0, dpr, 0, 0);
            const depthMax = (SX + SY) * 0.9;
            for (const [, x, y, z, face, i] of list) {
                const m = world.palette[world.material[i] - 1];
                if (!m) continue;
                const cloud = isCloud(world.material[i]);
                let fog = Math.min(0.14, Math.max(0, (x + y) / depthMax - 0.74) * 0.7);
                if (cloud) {
                    const dist = Math.hypot(x - CX, y - CY);
                    fog = Math.min(0.62, Math.max(0, (dist - 26) / 46) * 0.62);
                }
                let k: number;
                if (face === 0) k = 0.72 + 0.55 * LIGHT[2];
                else if (face === 1) k = 0.46 + 0.42 * (-LIGHT[1] + 0.4);
                else k = 0.34 + 0.4 * (LIGHT[0] + 0.5);
                k *= occlusion(x, y, z, face);
                if (m.glow) k = 1.12;
                let r = m.color.r * k;
                let g2 = m.color.g * k;
                let b = m.color.b * k;
                if (m.glow) {
                    r = Math.min(255, r + 12);
                    g2 = Math.min(255, g2 + 6);
                    b = Math.min(255, b * 0.75);
                }
                r += (38 - r) * fog;
                g2 += (52 - g2) * fog;
                b += (74 - b) * fog;

                const [px, py] = project(x, y, z);
                o.fillStyle = `rgb(${r | 0},${g2 | 0},${b | 0})`;
                const HW = scale * 0.5;
                const HH = scale * 0.28;
                const ZH = scale * 0.4;
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
        };

        const petals: Petal[] = world.petals.map(([wx, wy, wz]) => {
            const [x, y] = project(wx, wy, wz);
            return {
                x,
                y,
                vy: scale * (0.5 + Math.random() * 0.9),
                sway: 6 + Math.random() * 16,
                phase: Math.random() * 6.28,
                depth: 0.1 + Math.random() * 0.16,
                size: Math.max(1, Math.round(scale * (0.09 + Math.random() * 0.07))),
                tint: Math.random() < 0.5 ? '#f9c6d9' : '#fde6ee',
            };
        });

        const glints = world.glints.map(([wx, wy, wz]) => {
            const [x, y] = project(wx, wy, wz);
            return {
                x,
                y,
                phase: Math.random() * 6.28,
                speed: 0.7 + Math.random() * 1.6,
                size: scale * (0.12 + Math.random() * 0.16),
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
            originX,
            originY,
            island: paint(faces.island),
            clouds: paint(faces.clouds),
            petals,
            glints,
            lamps,
        };
        paintFrame(performance.now() / 1000, stateRef.current.parX, stateRef.current.parY);
    }, [paintFrame]);

    const stop = useCallback(() => {
        stateRef.current.running = false;
        cancelAnimationFrame(stateRef.current.raf);
    }, []);

    const start = useCallback(() => {
        const s = stateRef.current;
        if (s.reduced || s.running) return;
        s.running = true;
        const tick = (now: number) => {
            const time = (now - s.t0) / 1000;
            s.parX += (s.pointerX - s.parX) * 0.045;
            s.parY += (s.pointerY - s.parY) * 0.045;
            paintFrame(time, s.parX, s.parY);
            s.raf = requestAnimationFrame(tick);
        };
        s.raf = requestAnimationFrame(tick);
    }, [paintFrame]);

    const armIdle = useCallback(() => {
        const s = stateRef.current;
        window.clearTimeout(s.idle);
        s.idle = window.setTimeout(() => {
            stop();
            paintFrame((performance.now() - s.t0) / 1000, s.parX);
        }, IDLE_MS);
    }, [paintFrame, stop]);

    useEffect(() => {
        const query = window.matchMedia('(prefers-reduced-motion: reduce)');
        const s = stateRef.current;
        s.t0 = performance.now();
        s.reduced = query.matches;
        setReduced(query.matches);

        buildLayers();
        if (!query.matches) {
            start();
            armIdle();
        }

        // A dragged window edge fires resize continuously; the rebuild scans the
        // whole voxel grid, so coalesce trailing events instead of running per frame.
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
                paintFrame((performance.now() - s.t0) / 1000, s.parX);
            } else {
                start();
                armIdle();
            }
        };

        window.addEventListener('resize', onResize);
        // container-only changes (scrollbar, dvh, font swap) never fire window resize
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
            stop();
            paintFrame((performance.now() - s.t0) / 1000, s.parX);
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
