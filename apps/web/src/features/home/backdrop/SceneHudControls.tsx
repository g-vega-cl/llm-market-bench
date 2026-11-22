import {
    ATMOSPHERE_PHASES,
    type AtmospherePhase,
    Button,
} from '@llm-market-bench/ui-design-system';

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
    paused: boolean;
    onCycleAtmosphere: () => void;
    onTogglePaused: () => void;
}

/**
 * Accessible bottom-right HUD cluster rendered inside SceneStage's foreground
 * `controls` slot outside the aria-hidden backdrop.
 */
export function SceneHudControls({
    atmosphere,
    paused,
    onCycleAtmosphere,
    onTogglePaused,
}: SceneHudControlsProps) {
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
            >
                {paused ? 'Play motion' : 'Pause motion'}
            </Button>
        </>
    );
}
