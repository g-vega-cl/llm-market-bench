import { type AtmospherePhase, Button, cn } from '@llm-market-bench/ui-design-system';
import { useCallback, useEffect, useRef, useState } from 'react';
import { disposeSceneCanvases, type Scene } from './garden-renderer';
import {
    buildCedarScene,
    drawCedarSceneFrame,
    type EntranceState,
    stepEntranceState,
} from './garden-scene';
import { CEDAR_WORLD_ID } from './voxel-world';
import { getCedarWorldAndFaces } from './worlds';

/**
 * Panoramic Cedar Sanctuary diorama canvas: renders the wide floating highland
 * cedar ridge across Matcha & Cedar market-session atmospheres (dawn, daylight,
 * dusk, after-hours) with 4-plane depth parallax, drifting mist, and calm autumn leaves.
 */

const IDLE_MS = 20_000;
const FRAME_INTERVAL_MS = 1000 / 30 - 1.5;

export interface GardenBackdropProps {
    className?: string;
    atmosphere?: AtmospherePhase;
    paused?: boolean;
    onPausedChange?: (paused: boolean) => void;
    showControls?: boolean;
}

type MotionState = 'running' | 'idle' | 'paused';

function subscribeStageEvents(
    canvasEl: HTMLCanvasElement | null,
    query: MediaQueryList | null,
    handlers: {
        onResize: () => void;
        onPointer: (e: PointerEvent) => void;
        onKey: () => void;
        onVisibility: () => void;
        onPreference: (e: MediaQueryListEvent) => void;
    },
) {
    window.addEventListener('resize', handlers.onResize);
    const observer = new ResizeObserver(handlers.onResize);
    if (canvasEl) observer.observe(canvasEl);
    window.addEventListener('pointermove', handlers.onPointer, { passive: true });
    window.addEventListener('keydown', handlers.onKey);
    window.addEventListener('touchstart', handlers.onKey, { passive: true });
    document.addEventListener('visibilitychange', handlers.onVisibility);
    query?.addEventListener('change', handlers.onPreference);

    return () => {
        window.removeEventListener('resize', handlers.onResize);
        observer.disconnect();
        window.removeEventListener('pointermove', handlers.onPointer);
        window.removeEventListener('keydown', handlers.onKey);
        window.removeEventListener('touchstart', handlers.onKey);
        document.removeEventListener('visibilitychange', handlers.onVisibility);
        query?.removeEventListener('change', handlers.onPreference);
    };
}

export function GardenBackdrop({
    className,
    atmosphere = 'dusk',
    paused,
    onPausedChange,
    showControls = true,
}: GardenBackdropProps) {
    const canvasRef = useRef<HTMLCanvasElement | null>(null);
    const [pausedUi, setPausedUi] = useState(false);
    const [canvasReady, setCanvasReady] = useState(false);
    const sceneRef = useRef<Scene | null>(null);
    const atmosphereRef = useRef<AtmospherePhase>(atmosphere);
    atmosphereRef.current = atmosphere;
    const pausedPropRef = useRef<boolean | undefined>(paused);
    const onPausedChangeRef = useRef(onPausedChange);
    onPausedChangeRef.current = onPausedChange;

    const stateRef = useRef({
        raf: 0,
        motion: 'idle' as MotionState,
        idle: 0,
        pointerX: 0,
        pointerY: 0,
        parX: 0,
        parY: 0,
        elapsed: 0,
        entrance: { kind: 'settled' } as EntranceState,
        lastTick: 0,
        lastPaint: 0,
    });

    const paintFrame = useCallback((time: number, par: number, parY = 0) => {
        const canvas = canvasRef.current;
        const scene = sceneRef.current;
        if (!canvas || !scene) return;
        const ctx = canvas.getContext('2d');
        if (!ctx) return;
        drawCedarSceneFrame(ctx, scene, time, par, parY, stateRef.current.entrance);
    }, []);

    const buildLayers = useCallback(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const dpr = Math.min(window.devicePixelRatio || 1, 1.25);
        const W = canvas.clientWidth;
        const H = canvas.clientHeight;
        if (!W || !H) return;
        const backingW = Math.round(W * dpr);
        const backingH = Math.round(H * dpr);
        const prev = sceneRef.current;
        if (
            prev !== null &&
            prev.width === W &&
            prev.height === H &&
            prev.dpr === dpr &&
            prev.atmosphere === atmosphereRef.current &&
            canvas.width === backingW &&
            canvas.height === backingH
        ) {
            return;
        }
        canvas.width = backingW;
        canvas.height = backingH;

        const { world, faces } = getCedarWorldAndFaces();
        sceneRef.current = buildCedarScene(world, faces, W, H, dpr, atmosphereRef.current, prev);
        paintFrame(stateRef.current.elapsed, stateRef.current.parX, stateRef.current.parY);
        setCanvasReady(true);
    }, [paintFrame]);

    const stopToIdle = useCallback(() => {
        const s = stateRef.current;
        cancelAnimationFrame(s.raf);
        if (s.motion === 'running') s.motion = 'idle';
    }, []);

    const start = useCallback(() => {
        const s = stateRef.current;
        if (s.motion === 'paused' || s.motion === 'running') return;
        s.motion = 'running';
        s.lastTick = performance.now();
        s.lastPaint = 0;
        const tick = (now: number) => {
            if (s.motion !== 'running') return;
            if (now - s.lastPaint >= FRAME_INTERVAL_MS) {
                const dt = Math.min(0.1, Math.max(0, (now - s.lastTick) / 1000));
                s.lastTick = now;
                s.lastPaint = now;
                s.elapsed += dt;
                s.entrance = stepEntranceState(s.entrance, sceneRef.current !== null, dt);
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
        if (s.motion === 'paused' || document.hidden) return;
        s.idle = window.setTimeout(() => {
            stopToIdle();
            paintFrame(s.elapsed, s.parX, s.parY);
        }, IDLE_MS);
    }, [paintFrame, stopToIdle]);

    const settleAndPause = useCallback(() => {
        const s = stateRef.current;
        window.clearTimeout(s.idle);
        cancelAnimationFrame(s.raf);
        s.motion = 'paused';
        s.entrance = { kind: 'settled' };
        paintFrame(s.elapsed, s.parX, s.parY);
    }, [paintFrame]);

    const resumeMotion = useCallback(() => {
        const s = stateRef.current;
        if (s.motion === 'paused') s.motion = 'idle';
        if (!document.hidden) {
            start();
            armIdle();
        }
    }, [armIdle, start]);

    useEffect(() => {
        const query =
            typeof window.matchMedia === 'function'
                ? window.matchMedia('(prefers-reduced-motion: reduce)')
                : null;
        const s = stateRef.current;
        // System reduced-motion always wins over an un-toggled initial parent `paused={false}`
        const initialPaused = (query?.matches ?? false) || pausedPropRef.current === true;
        s.motion = initialPaused ? 'paused' : 'idle';
        s.entrance = initialPaused ? { kind: 'settled' } : { kind: 'animating', elapsed: 0 };
        setPausedUi(initialPaused);
        if (initialPaused && pausedPropRef.current === false) {
            onPausedChangeRef.current?.(true);
        }

        buildLayers();
        if (!initialPaused && !document.hidden) {
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
            start();
        };
        const onKey = () => {
            armIdle();
            start();
        };
        const onVisibility = () => {
            if (document.hidden) {
                window.clearTimeout(s.idle);
                stopToIdle();
            } else {
                start();
                armIdle();
            }
        };
        const onPreference = (e: MediaQueryListEvent) => {
            setPausedUi(e.matches);
            onPausedChangeRef.current?.(e.matches);
            if (e.matches) settleAndPause();
            else resumeMotion();
        };

        const unsubscribe = subscribeStageEvents(canvasRef.current, query, {
            onResize,
            onPointer,
            onKey,
            onVisibility,
            onPreference,
        });

        return () => {
            unsubscribe();
            window.clearTimeout(resizeTimer);
            window.clearTimeout(s.idle);
            cancelAnimationFrame(s.raf);
            disposeSceneCanvases(sceneRef.current);
            sceneRef.current = null;
        };
    }, [armIdle, buildLayers, resumeMotion, settleAndPause, start, stopToIdle]);

    useEffect(() => {
        if (sceneRef.current && sceneRef.current.atmosphere !== atmosphere) {
            buildLayers();
        }
    }, [atmosphere, buildLayers]);

    // Sync only explicit parent `paused` transitions after mount so initial reduced-motion state never races
    useEffect(() => {
        if (paused === undefined) {
            pausedPropRef.current = undefined;
            return;
        }
        const prevProp = pausedPropRef.current;
        pausedPropRef.current = paused;
        if (prevProp === paused) return;

        const isCurrentlyPaused = stateRef.current.motion === 'paused';
        if (isCurrentlyPaused === paused) return;
        setPausedUi(paused);
        if (paused) settleAndPause();
        else resumeMotion();
    }, [paused, resumeMotion, settleAndPause]);

    const toggle = useCallback(() => {
        const next = stateRef.current.motion !== 'paused';
        setPausedUi(next);
        onPausedChangeRef.current?.(next);
        if (next) settleAndPause();
        else resumeMotion();
    }, [resumeMotion, settleAndPause]);

    return (
        <>
            <canvas
                ref={canvasRef}
                className={cn(
                    'transition-opacity duration-200',
                    canvasReady ? 'opacity-100' : 'opacity-0',
                    className,
                )}
                data-testid="garden-backdrop"
                data-world={CEDAR_WORLD_ID}
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
                        {pausedUi ? 'Play motion' : 'Pause motion'}
                    </Button>
                </div>
            ) : null}
        </>
    );
}
