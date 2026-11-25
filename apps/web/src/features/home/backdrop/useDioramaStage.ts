import { type AtmospherePhase, resolveAtmospherePhase } from '@llm-market-bench/ui-design-system';
import { useCallback, useState, useSyncExternalStore } from 'react';
import { nextAtmospherePhase } from './SceneHudControls';

/**
 * Who owns the scene's motion.
 *
 * - `running`  — nothing is frozen; the HUD offers "Pause motion".
 * - `paused`   — the visitor froze it; the HUD offers "Play motion".
 * - `reduced`  — the operating system asked for reduced motion. CSS has already
 *   frozen every loop, so offering a "Pause motion" button would be a lie.
 */
export type SceneMotion = 'running' | 'paused' | 'reduced';

const REDUCED_MOTION_QUERY = '(prefers-reduced-motion: reduce)';

function reducedMotionQuery(): MediaQueryList | null {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return null;
    return window.matchMedia(REDUCED_MOTION_QUERY);
}

function subscribeReducedMotion(onChange: () => void) {
    const query = reducedMotionQuery();
    if (!query) return () => undefined;
    query.addEventListener('change', onChange);
    return () => {
        query.removeEventListener('change', onChange);
    };
}

function getReducedMotion() {
    return reducedMotionQuery()?.matches ?? false;
}

/** Server and first client paint agree on "not reduced"; the query corrects it on hydration. */
function getServerReducedMotion() {
    return false;
}

/**
 * Shared HUD state for SceneStage views: accepts an SSR-resolved
 * `initialAtmosphere` from the route loader so server HTML and client hydration
 * match on first byte without an unmount/mount sky flash, and derives the
 * single `motion` state from the visitor's toggle and the OS preference.
 *
 * The OS preference lives here rather than in a backdrop because every host
 * renders the same HUD: a backdrop that owned the query could only fix its own
 * page (that is how `/build` ended up offering "Pause motion" over a frozen
 * scene), and the next backdrop would repeat the mistake.
 */
export function useDioramaStage(initialAtmosphere?: AtmospherePhase) {
    const [atmosphere, setAtmosphere] = useState<AtmospherePhase>(
        () => initialAtmosphere ?? resolveAtmospherePhase(new Date(), 'market-et'),
    );
    const [userPaused, setUserPaused] = useState(false);
    const reduced = useSyncExternalStore(
        subscribeReducedMotion,
        getReducedMotion,
        getServerReducedMotion,
    );

    // System reduced-motion outranks the visitor's toggle, so the two can never
    // disagree about whether the scene is moving.
    const motion: SceneMotion = reduced ? 'reduced' : userPaused ? 'paused' : 'running';

    const cycleAtmosphere = useCallback(() => {
        setAtmosphere(nextAtmospherePhase);
    }, []);

    const toggleMotion = useCallback(() => {
        setUserPaused((prev) => (reduced ? prev : !prev));
    }, [reduced]);

    return {
        atmosphere,
        motion,
        cycleAtmosphere,
        toggleMotion,
    };
}

/**
 * Replaces a single URL search parameter without invoking router transitions,
 * keeping refreshes aligned with HUD or diagnostic state changes.
 */
export function syncUrlSearchParam(key: string, value: string | null) {
    if (typeof window === 'undefined' || !window.history?.replaceState) return;
    try {
        const url = new URL(window.location.href);
        if (value === null) {
            url.searchParams.delete(key);
        } else {
            url.searchParams.set(key, value);
        }
        window.history.replaceState(window.history.state, '', `${url.pathname}${url.search}`);
    } catch {
        // Ignore history updates in non-standard test or sandboxed environments.
    }
}
