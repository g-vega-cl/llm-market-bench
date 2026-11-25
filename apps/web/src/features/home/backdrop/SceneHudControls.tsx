import {
    ATMOSPHERE_PHASES,
    type AtmospherePhase,
    Button,
} from '@llm-market-bench/ui-design-system';
import type { SceneMotion } from './useDioramaStage';

export const ATMOSPHERE_LABELS: Record<AtmospherePhase, string> = {
    dawn: 'Dawn',
    daylight: 'Daylight',
    dusk: 'Dusk',
    'after-hours': 'After-Hours',
};

export function nextAtmospherePhase(current: AtmospherePhase): AtmospherePhase {
    const idx = ATMOSPHERE_PHASES.indexOf(current);
    return ATMOSPHERE_PHASES[(idx + 1) % ATMOSPHERE_PHASES.length];
}

export interface SceneHudControlsProps {
    atmosphere: AtmospherePhase;
    /** Derived state from `useDioramaStage` — never a bare boolean. */
    motion: SceneMotion;
    onCycleAtmosphere: () => void;
    onTogglePaused: () => void;
}

/**
 * Accessible bottom-right HUD cluster rendered inside SceneStage's foreground
 * `controls` slot outside the aria-hidden backdrop.
 *
 * The motion control reports the derived state rather than guessing: under
 * `prefers-reduced-motion` the scene is already frozen, so it reads "Motion:
 * reduced" and is inert instead of offering a toggle that changes nothing.
 */
export function SceneHudControls({
    atmosphere,
    motion,
    onCycleAtmosphere,
    onTogglePaused,
}: SceneHudControlsProps) {
    const reduced = motion === 'reduced';
    const paused = motion === 'paused';

    return (
        <>
            <Button
                type="button"
                onClick={onCycleAtmosphere}
                variant="outline"
                colorScheme="neutral"
                size="sm"
                data-testid="atmosphere-switcher"
            >
                {`Sky: ${ATMOSPHERE_LABELS[atmosphere]}`}
            </Button>
            <Button
                type="button"
                onClick={onTogglePaused}
                variant="outline"
                colorScheme="neutral"
                size="sm"
                disabled={reduced}
                aria-pressed={paused}
                data-testid="motion-toggle"
                data-motion={motion}
            >
                {reduced ? 'Motion: reduced' : paused ? 'Play motion' : 'Pause motion'}
            </Button>
        </>
    );
}
