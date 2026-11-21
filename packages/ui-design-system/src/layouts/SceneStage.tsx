import type * as React from 'react';
import type { AtmospherePhase } from '../lib/atmosphere';
import { cn } from '../lib/cn';

/**
 * SceneStage layout primitive.
 *
 * A spatially contained Voxel stage for multi-layered living-scene heroes and
 * parallax footers. Enforces strict foreground/background separation:
 * - Clipped overflow (`overflow-hidden isolate`) so animated layers never bleed
 *   into adjacent data tables or cards.
 * - Dedicated non-interactive `aria-hidden` backdrop layer for canvas/SVG/voxel
 *   dioramas.
 * - Optional opaque/semi-opaque Matcha scrim (`scrim="panel"`) to protect CTAs
 *   and telemetry without glassmorphism blur.
 * - Dynamic Matcha & Cedar atmospheric sky gradient (`dawn`, `daylight`,
 *   `dusk`, `after-hours`).
 */

export type SceneStageVariant = 'hero' | 'footer';
export type SceneMotionRole = 'background' | 'reactive' | 'story';
export type SceneScrim = 'none' | 'panel';

export interface SceneStageProps extends React.HTMLAttributes<HTMLElement> {
    /** Stage placement: full-bleed hero header or bounded parallax footer. */
    variant?: SceneStageVariant;
    /** Dynamic Matcha & Cedar atmospheric sky state. */
    atmosphere?: AtmospherePhase;
    /** Semantic motion role from the living-scene taxonomy. */
    motionRole?: SceneMotionRole;
    /** Foreground CTA/content protection layer. */
    scrim?: SceneScrim;
    /** Multi-layer diorama, canvas, or sprite backdrop rendered behind children. */
    backdrop?: React.ReactNode;
    /** Accessible foreground HUD controls anchored to the bottom-right stage corner. */
    controls?: React.ReactNode;
    children: React.ReactNode;
}

const atmosphereClassMap: Record<AtmospherePhase, string> = {
    dawn: 'scene-atmosphere-dawn',
    daylight: 'scene-atmosphere-daylight',
    dusk: 'scene-atmosphere-dusk',
    'after-hours': 'scene-atmosphere-after-hours',
};

const variantClassMap: Record<SceneStageVariant, string> = {
    hero: 'scene-stage-hero px-6 py-12',
    footer: 'scene-stage-footer px-6 py-8 border-t-2 border-voxel-bevel-hi',
};

export function SceneStage({
    variant = 'hero',
    atmosphere = 'dusk',
    motionRole = 'background',
    scrim = 'none',
    backdrop,
    controls,
    children,
    className,
    ...rest
}: SceneStageProps) {
    const Tag = variant === 'footer' ? 'footer' : 'section';

    return (
        <Tag
            data-slot="scene-stage"
            data-stage-variant={variant}
            data-atmosphere={atmosphere}
            data-motion-role={motionRole}
            className={cn(
                'relative isolate overflow-hidden rounded-none',
                atmosphereClassMap[atmosphere],
                variantClassMap[variant],
                className,
            )}
            {...rest}
        >
            {backdrop ? (
                <div
                    data-slot="scene-backdrop"
                    aria-hidden="true"
                    className="scene-backdrop pointer-events-none absolute inset-0 z-0 overflow-hidden"
                >
                    {backdrop}
                </div>
            ) : null}

            <div className="relative z-10 mx-auto w-full max-w-7xl min-w-0">
                {scrim === 'panel' ? (
                    <div
                        data-slot="scene-scrim"
                        className="scene-scrim voxel-card rounded-none p-6 min-w-0"
                    >
                        {children}
                    </div>
                ) : (
                    children
                )}
            </div>

            {controls ? (
                <div
                    data-slot="scene-controls"
                    className="pointer-events-auto absolute right-3 bottom-3 z-20 flex items-center gap-2"
                >
                    {controls}
                </div>
            ) : null}
        </Tag>
    );
}
