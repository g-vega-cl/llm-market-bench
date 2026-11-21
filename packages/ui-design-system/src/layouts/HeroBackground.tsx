import type * as React from 'react';
import type { AtmospherePhase } from '../lib/atmosphere';
import { cn } from '../lib/cn';

/**
 * HeroBackground layout.
 *
 * A spatially contained Voxel hero stage built strictly from Matcha & Cedar
 * semantic tokens with sharp 0px geometry, fluid padding (zero viewport
 * breakpoints), a CSS dot-matrix horizon texture, and an optional living-scene
 * backdrop slot.
 */

export interface HeroBackgroundProps {
    gradient?: 'electric' | 'success' | 'catalyst' | 'ai';
    atmosphere?: AtmospherePhase;
    backdrop?: React.ReactNode;
    children: React.ReactNode;
    className?: string;
}

const overlayMap: Record<NonNullable<HeroBackgroundProps['gradient']>, string> = {
    electric: 'from-voxel-elevated/95 via-voxel-surface/95 to-voxel-canvas/95',
    success: 'from-success-dark/95 via-voxel-surface/95 to-voxel-canvas/95',
    catalyst: 'from-warning-dark/95 via-voxel-surface/95 to-voxel-canvas/95',
    ai: 'from-info-dark/95 via-voxel-surface/95 to-voxel-canvas/95',
};

const atmosphereMap: Record<AtmospherePhase, string> = {
    dawn: 'scene-atmosphere-dawn',
    daylight: 'scene-atmosphere-daylight',
    dusk: 'scene-atmosphere-dusk',
    'after-hours': 'scene-atmosphere-after-hours',
};

const accentEdgeMap: Record<NonNullable<HeroBackgroundProps['gradient']>, string> = {
    electric: 'border-voxel-bevel-hi',
    success: 'border-success/40',
    catalyst: 'border-accent/40',
    ai: 'border-info/40',
};

export function HeroBackground({
    gradient = 'electric',
    atmosphere,
    backdrop,
    children,
    className,
}: HeroBackgroundProps) {
    return (
        <div
            data-slot="hero-background"
            data-atmosphere={atmosphere}
            className={cn(
                'relative isolate overflow-hidden rounded-none border-b-2',
                accentEdgeMap[gradient],
                atmosphere ? atmosphereMap[atmosphere] : 'bg-voxel-canvas',
                className,
            )}
        >
            <div
                aria-hidden="true"
                className="pointer-events-none absolute inset-0 voxel-dot-matrix opacity-25"
            />

            {!atmosphere ? (
                <div
                    aria-hidden="true"
                    className={cn(
                        'pointer-events-none absolute inset-0 bg-gradient-to-br',
                        overlayMap[gradient],
                    )}
                />
            ) : null}

            {backdrop ? (
                <div
                    data-slot="hero-backdrop"
                    aria-hidden="true"
                    className="scene-backdrop pointer-events-none absolute inset-0 z-0 overflow-hidden"
                >
                    {backdrop}
                </div>
            ) : null}

            <div className="relative z-10 mx-auto w-full max-w-7xl min-w-0 px-6 py-12">
                {children}
            </div>
        </div>
    );
}
