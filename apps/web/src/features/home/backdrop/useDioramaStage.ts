import { type AtmospherePhase, resolveAtmospherePhase } from '@llm-market-bench/ui-design-system';
import { useCallback, useEffect, useState } from 'react';
import { nextAtmospherePhase } from './SceneHudControls';

/**
 * Shared HUD timing state for SceneStage views: starts at deterministic `'dusk'`
 * for SSR, resolves the US Eastern market-session atmosphere on mount, and exposes
 * cycle/pause callbacks with prefers-reduced-motion synchronization.
 */
export function useDioramaStage() {
    const [atmosphere, setAtmosphere] = useState<AtmospherePhase>('dusk');
    const [paused, setPaused] = useState(false);

    useEffect(() => {
        setAtmosphere(resolveAtmospherePhase(new Date(), 'market-et'));
    }, []);

    const cycleAtmosphere = useCallback(() => {
        setAtmosphere(nextAtmospherePhase);
    }, []);

    const toggleMotion = useCallback(() => {
        setPaused((prev) => !prev);
    }, []);

    return {
        atmosphere,
        paused,
        setPaused,
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
