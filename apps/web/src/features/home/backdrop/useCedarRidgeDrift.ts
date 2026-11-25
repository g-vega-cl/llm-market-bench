import { useEffect, useRef } from 'react';

/** Pointer travel, in px, at depth 1. Layers scale this by their own depth. */
const POINTER_PX = 56;
/** Extra downward drift contributed by page scroll, in px, at depth 1. */
const SCROLL_PX = 18;
/** Scroll distance over which the scroll term reaches full strength. */
const SCROLL_RANGE_PX = 400;

/**
 * Writes drift into two CSS custom properties on the Cedar Ridge root so every
 * plane reads the same values through `--cr-depth` and no per-layer JS runs.
 *
 * The offset is **derived, never accumulated**: `pointerX`/`pointerY` hold the
 * last pointer sample, and `write()` recomputes both custom properties from
 * that sample *plus* the current `scrollY`. That makes the hook idempotent —
 * replaying a scroll event at an unchanged `scrollY` yields the same number.
 * An `y -= scrollTerm()` accumulator does not: each scroll event subtracts
 * again, and on touch devices no pointermove ever arrives to re-derive it, so
 * the scene walks off the stage.
 *
 * Nothing moves while paused, while the document is hidden, or under
 * `prefers-reduced-motion`; every one of those settles to 0.
 *
 * Returns the ref to attach to the backdrop root.
 */
export function useCedarRidgeDrift(paused: boolean) {
    const ref = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const el = ref.current;
        if (!el) return;

        const reduce =
            typeof window.matchMedia === 'function'
                ? window.matchMedia('(prefers-reduced-motion: reduce)')
                : null;
        let frame = 0;
        let pointerX = 0;
        let pointerY = 0;

        const frozen = () => paused || (reduce?.matches ?? false) || document.hidden;

        const scrollTerm = () => Math.min(1, window.scrollY / SCROLL_RANGE_PX) * SCROLL_PX;

        const write = () => {
            frame = 0;
            const x = frozen() ? 0 : pointerX;
            const y = frozen() ? 0 : pointerY - scrollTerm();
            el.style.setProperty('--cr-px', x.toFixed(2));
            el.style.setProperty('--cr-py', y.toFixed(2));
        };

        const schedule = () => {
            if (frame === 0) frame = requestAnimationFrame(write);
        };

        const onPointer = (event: PointerEvent) => {
            if (frozen()) return;
            pointerX = -(event.clientX / window.innerWidth - 0.5) * POINTER_PX;
            pointerY = -(event.clientY / window.innerHeight - 0.5) * POINTER_PX * 0.5;
            schedule();
        };

        // Scroll contributes only to the derived term, so the pending write
        // recomputes it; nothing is added to a running total.
        const onScroll = () => {
            if (frozen()) return;
            schedule();
        };

        // A backgrounded tab keeps its last offset; hide/unhide both settle.
        const onVisibility = () => {
            schedule();
        };

        const onPreference = () => {
            schedule();
        };

        schedule();
        window.addEventListener('pointermove', onPointer, { passive: true });
        window.addEventListener('scroll', onScroll, { passive: true });
        document.addEventListener('visibilitychange', onVisibility);
        reduce?.addEventListener('change', onPreference);

        return () => {
            window.removeEventListener('pointermove', onPointer);
            window.removeEventListener('scroll', onScroll);
            document.removeEventListener('visibilitychange', onVisibility);
            reduce?.removeEventListener('change', onPreference);
            if (frame !== 0) cancelAnimationFrame(frame);
        };
    }, [paused]);

    return ref;
}
