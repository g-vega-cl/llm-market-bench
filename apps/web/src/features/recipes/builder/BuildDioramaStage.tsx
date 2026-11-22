import { type AtmospherePhase, SceneStage } from '@llm-market-bench/ui-design-system';
import type { ReactNode } from 'react';
import { GardenBackdrop } from '../../home/backdrop/GardenBackdrop';
import { SceneHudControls } from '../../home/backdrop/SceneHudControls';

export interface DioramaControls {
    atmosphere: AtmospherePhase;
    paused: boolean;
    setPaused: (paused: boolean) => void;
    cycleAtmosphere: () => void;
    toggleMotion: () => void;
}

export interface BuildDioramaStageProps {
    diorama: DioramaControls;
    /** Full-viewport height during Step 1 chat; compact bounded banner in Step 2. */
    heroViewport?: boolean;
    children: ReactNode;
}

/**
 * Shared Cedar Sanctuary SceneStage shell for `/build`. Keeping this component
 * at the root of BuilderChatPanel ensures GardenBackdrop and HUD state
 * (atmosphere + paused) survive Step 1 -> Step 2 transitions without unmounting.
 */
export function BuildDioramaStage({
    diorama,
    heroViewport = false,
    children,
}: BuildDioramaStageProps) {
    return (
        <SceneStage
            variant="hero"
            atmosphere={diorama.atmosphere}
            motionRole="reactive"
            className={
                heroViewport
                    ? 'home-hero-viewport flex w-full flex-col text-voxel-ink'
                    : 'flex w-full flex-col text-voxel-ink'
            }
            backdrop={
                <GardenBackdrop
                    atmosphere={diorama.atmosphere}
                    paused={diorama.paused}
                    onPausedChange={diorama.setPaused}
                    showControls={false}
                    className="h-full w-full"
                />
            }
            controls={
                <SceneHudControls
                    atmosphere={diorama.atmosphere}
                    paused={diorama.paused}
                    onCycleAtmosphere={diorama.cycleAtmosphere}
                    onTogglePaused={diorama.toggleMotion}
                />
            }
        >
            {children}
        </SceneStage>
    );
}
