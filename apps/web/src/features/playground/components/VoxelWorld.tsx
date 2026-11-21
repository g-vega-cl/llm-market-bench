import { Button } from '@llm-market-bench/ui-design-system';
import type { JSX } from 'react';
import { useEffect, useRef, useState } from 'react';
import {
    disposeWorld,
    drawWorld,
    initWorld,
    resolveWorldPalette,
    type WorldState,
    type WorldTone,
} from '../lib/world-gl';

export type WorldContextFactory = (canvas: HTMLCanvasElement) => WebGL2RenderingContext | null;

export interface VoxelWorldProps {
    tone: WorldTone;
    /** Injectable WebGL2 factory; tests pass a stub because jsdom has no WebGL. */
    createContext?: WorldContextFactory;
}

export type WorldFallbackReason = 'no-context' | 'shader' | 'program' | 'throw' | 'context-lost';

const IDLE_STOP_MS = 60_000;
const DEFAULT_CONTEXT: WorldContextFactory = (canvas) => canvas.getContext('webgl2');
const CANVAS_CLASS = 'pointer-events-none absolute inset-0 h-full w-full';
const FALLBACK_HEIGHTS =
    'h-[42%] h-[18%] h-[66%] h-[30%] h-[90%] h-[54%] h-[74%] h-[26%] h-[58%] h-[98%] h-[38%] h-[82%] h-[14%] h-[50%] h-[70%] h-[34%] h-[86%] h-[22%] h-[62%] h-[46%] h-[94%] h-[10%] h-[78%] h-[100%]'.split(
        ' ',
    );

const TONE_FILL: Record<WorldTone, string> = {
    bullish: 'bg-success',
    bearish: 'bg-danger',
    neutral: 'bg-voxel-muted',
};

function mediaMatches(query: string): boolean {
    return typeof window.matchMedia === 'function' && window.matchMedia(query).matches;
}

function scheduleIdle(callback: () => void): () => void {
    const request = window.requestIdleCallback;
    if (typeof request !== 'function') {
        const handle = window.setTimeout(callback, 1);
        return () => window.clearTimeout(handle);
    }
    const handle = request(callback, { timeout: 1500 });
    return () => window.cancelIdleCallback?.(handle);
}

function sizeCanvas(canvas: HTMLCanvasElement, gl: WebGL2RenderingContext): void {
    const rect = canvas.getBoundingClientRect();
    const base = Math.min(Math.max(window.devicePixelRatio || 1, 1), 1.5);
    // One scale for both axes: clamping them independently would change the
    // drawing-buffer aspect ratio, which the shader uses for its projection.
    const widest = Math.max(rect.width, rect.height, 1);
    const dpr = Math.min(base, 1600 / widest);
    canvas.width = Math.max(Math.round(rect.width * dpr), 1);
    canvas.height = Math.max(Math.round(rect.height * dpr), 1);
    gl.viewport(0, 0, canvas.width, canvas.height);
}

type Creation =
    | { ok: true; gl: WebGL2RenderingContext; state: WorldState }
    | { ok: false; reason: WorldFallbackReason };

function createWorld(
    canvas: HTMLCanvasElement,
    tone: WorldTone,
    factory: WorldContextFactory,
): Creation {
    try {
        const gl = factory(canvas);
        if (!gl) return { ok: false, reason: 'no-context' };
        const result = initWorld(gl, resolveWorldPalette(tone));
        return result.ok
            ? { ok: true, gl, state: result.state }
            : { ok: false, reason: result.reason };
    } catch {
        return { ok: false, reason: 'throw' };
    }
}

interface SessionOptions {
    canvas: HTMLCanvasElement;
    tone: WorldTone;
    gl: WebGL2RenderingContext;
    state: WorldState;
    reducedMotion: boolean;
    isPaused: () => boolean;
    onStatus: (reason: WorldFallbackReason | null) => void;
}

function createSession(options: SessionOptions): {
    start: () => void;
    stop: () => void;
    dispose: () => void;
} {
    const { canvas, tone, gl, reducedMotion, isPaused, onStatus } = options;
    const finePointer = mediaMatches('(pointer: fine)');
    let state = options.state;
    let raf = 0;
    let resizeRaf = 0;
    let pointerX = 0;
    let lost = false;
    let disposed = false;
    const startedAt = performance.now();
    let lastActivity = startedAt;

    const draw = (now: number) =>
        drawWorld(gl, state, { time: (now - startedAt) / 1000, pointerX });

    const stop = () => {
        window.cancelAnimationFrame(raf);
        raf = 0;
    };

    const frame = (now: number) => {
        raf = 0;
        if (disposed || lost || isPaused()) return;
        if (document.visibilityState === 'hidden') return;
        if (now - lastActivity > IDLE_STOP_MS) return;
        draw(now);
        raf = window.requestAnimationFrame(frame);
    };

    const start = () => {
        if (disposed || lost || raf !== 0 || reducedMotion || isPaused()) return;
        if (document.visibilityState === 'hidden') return;
        lastActivity = performance.now();
        raf = window.requestAnimationFrame(frame);
    };

    const onPointerMove = (event: PointerEvent) => {
        if (disposed) return;
        // Activity restarts the loop on every device; only the uniform is fine-pointer.
        lastActivity = performance.now();
        start();
        if (!finePointer) return;
        if (document.body.dataset.dragging === 'true') return;
        const width = window.innerWidth || 1;
        pointerX = Math.max(-1, Math.min(1, (event.clientX / width) * 2 - 1));
        start();
    };

    const onActivity = () => {
        lastActivity = performance.now();
        start();
    };

    const onVisibility = () => {
        if (document.visibilityState === 'hidden') stop();
        else start();
    };

    const onResize = () => {
        if (disposed || resizeRaf !== 0) return;
        resizeRaf = window.requestAnimationFrame(() => {
            resizeRaf = 0;
            if (disposed || lost) return;
            sizeCanvas(canvas, gl);
            draw(performance.now());
        });
    };

    const onLost = (event: Event) => {
        event.preventDefault();
        lost = true;
        stop();
        onStatus('context-lost');
    };

    const onRestored = () => {
        try {
            const result = initWorld(gl, resolveWorldPalette(tone));
            if (!result.ok) {
                onStatus(result.reason);
                return;
            }
            state = result.state;
            lost = false;
            sizeCanvas(canvas, gl);
            onStatus(null);
            if (reducedMotion) draw(performance.now());
            else start();
        } catch {
            onStatus('throw');
        }
    };

    const dispose = () => {
        disposed = true;
        stop();
        window.cancelAnimationFrame(resizeRaf);
        window.removeEventListener('pointermove', onPointerMove);
        window.removeEventListener('keydown', onActivity);
        window.removeEventListener('resize', onResize);
        document.removeEventListener('visibilitychange', onVisibility);
        canvas.removeEventListener('webglcontextlost', onLost);
        canvas.removeEventListener('webglcontextrestored', onRestored);
        try {
            disposeWorld(gl, state);
        } catch {
            /* the context can already be gone during teardown */
        }
    };

    sizeCanvas(canvas, gl);
    window.addEventListener('pointermove', onPointerMove, { passive: true });
    window.addEventListener('keydown', onActivity, { passive: true });
    window.addEventListener('resize', onResize);
    document.addEventListener('visibilitychange', onVisibility);
    canvas.addEventListener('webglcontextlost', onLost);
    canvas.addEventListener('webglcontextrestored', onRestored);
    // Always paint one frame: a background or prerendered tab must still show the
    // world, and the rAF loop is what waits for visibility.
    draw(performance.now());
    // Only claim success once the first frame left the GPU clean.
    const glError = gl.getError();
    const broken = (typeof glError === 'number' && glError !== 0) || gl.isContextLost() === true;
    if (broken) onStatus('throw');
    else onStatus(null);
    if (!reducedMotion) start();

    return { start, stop, dispose };
}

export function VoxelWorld({
    tone,
    createContext = DEFAULT_CONTEXT,
}: VoxelWorldProps): JSX.Element | null {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const sessionRef = useRef<ReturnType<typeof createSession> | null>(null);
    const warnedRef = useRef(false);
    const pausedRef = useRef(false);
    const [paused, setPaused] = useState(false);
    const [fallback, setFallback] = useState<WorldFallbackReason | null>(null);

    useEffect(() => {
        pausedRef.current = paused;
        if (paused) sessionRef.current?.stop();
        else sessionRef.current?.start();
    }, [paused]);

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        let cancelled = false;
        const reducedMotion = mediaMatches('(prefers-reduced-motion: reduce)');
        const onStatus = (reason: WorldFallbackReason | null) => {
            if (cancelled) return;
            if (reason && !warnedRef.current) {
                warnedRef.current = true;
                console.warn('[world] fallback', reason);
            }
            setFallback(reason);
        };
        const cancelIdle = scheduleIdle(() => {
            if (cancelled) return;
            const creation = createWorld(canvas, tone, createContext);
            if (!creation.ok) {
                onStatus(creation.reason);
                return;
            }
            sessionRef.current = createSession({
                canvas,
                tone,
                gl: creation.gl,
                state: creation.state,
                reducedMotion,
                isPaused: () => pausedRef.current,
                onStatus,
            });
        });
        return () => {
            cancelled = true;
            cancelIdle();
            sessionRef.current?.dispose();
            sessionRef.current = null;
        };
    }, [tone, createContext]);

    return (
        <div className="flex w-full flex-col gap-2">
            <div className="relative aspect-[16/9] w-full overflow-hidden rounded-none border border-voxel-bevel-hi bg-voxel-surface">
                {/* The band is the page's floor, not a crash suit: the canvas paints
                    the lit version over it when GL works, and a silent GL failure
                    still leaves a terrain instead of an empty box. It must come
                    FIRST in the DOM: both layers are absolute, so a later sibling
                    would cover the canvas. */}
                <div
                    data-testid={fallback ? 'world-fallback' : undefined}
                    data-reason={fallback ?? undefined}
                    aria-hidden="true"
                    className="voxel-trough pointer-events-none absolute inset-0 flex items-end gap-px overflow-hidden p-2"
                >
                    {FALLBACK_HEIGHTS.map((height) => (
                        <div
                            key={height}
                            className={`flex-1 rounded-none border border-voxel-bevel-hi ${TONE_FILL[tone]} ${fallback ? 'opacity-70' : 'opacity-25'} ${height}`}
                        />
                    ))}
                </div>
                <div aria-hidden="true" className="absolute inset-0">
                    <canvas ref={canvasRef} data-testid="voxel-world" className={CANVAS_CLASS} />
                </div>
            </div>
            <div className="voxel-trough flex justify-end p-2">
                <Button
                    size="sm"
                    variant="outline"
                    colorScheme="neutral"
                    aria-pressed={paused}
                    onClick={() => setPaused((current) => !current)}
                >
                    {paused ? 'Resume the world' : 'Pause the world'}
                </Button>
            </div>
        </div>
    );
}
