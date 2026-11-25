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

/**
 * Where the world sits relative to the page.
 *
 * `stage` (default) clips the backdrop inside the stage — the shape for a hero or
 * footer band that owns a slice of the page. `page` mounts the backdrop as its own
 * fixed, full-viewport `z-0` layer with the atmosphere sky on it, so content flows
 * straight over the world instead of starting below a reserved band. In `page`
 * mode the host page must keep its own content in positioned layers (`relative
 * z-10`) so the world never paints over text — see `.agents/rules/design-spec.md`
 * §12.2.
 */
export type SceneBackdropMode = 'stage' | 'page';

/**
 * Who owns a scene's motion, mirrored from the host's `useDioramaStage`.
 * `reduced` means the operating system asked for it, so the UI must not offer
 * to un-freeze the scene.
 */
export type SceneMotion = 'running' | 'paused' | 'reduced';

/**
 * The contract every SceneStage backdrop implements, so a new surface picks a
 * world rather than inventing a third prop shape.
 */
export interface SceneBackdropProps {
    atmosphere: AtmospherePhase;
    motion: SceneMotion;
    className?: string;
}
export type SceneScrim = 'none' | 'panel';

export interface SceneStageProps extends React.HTMLAttributes<HTMLElement> {
    /** Stage placement: full-bleed hero header or bounded parallax footer. */
    variant?: SceneStageVariant;
    /** Backdrop placement: clipped inside the stage band, or fixed behind the page. */
    backdropMode?: SceneBackdropMode;
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

/** `page` mode owns no band, so it carries padding only — no `min-height`. */
const pageClassMap: Record<SceneStageVariant, string> = {
    hero: 'px-6 py-6',
    footer: 'px-6 py-8 border-t-2 border-voxel-bevel-hi',
};

export function SceneStage({
    variant = 'hero',
    backdropMode = 'stage',
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

    const content = (
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
    );

    if (backdropMode === 'page') {
        return (
            <>
                {backdrop ? (
                    <div
                        data-slot="scene-backdrop"
                        aria-hidden="true"
                        className={cn(
                            'scene-backdrop pointer-events-none fixed inset-0 z-0 overflow-hidden',
                            atmosphereClassMap[atmosphere],
                        )}
                    >
                        {backdrop}
                    </div>
                ) : null}

                <Tag
                    data-slot="scene-stage"
                    data-stage-variant={variant}
                    data-backdrop-mode="page"
                    data-atmosphere={atmosphere}
                    data-motion-role={motionRole}
                    className={cn('relative z-10 rounded-none', pageClassMap[variant], className)}
                    {...rest}
                >
                    <div className="relative z-10 mx-auto flex w-full max-w-7xl min-w-0 flex-col gap-3">
                        {content}
                        {controls ? (
                            <div
                                data-slot="scene-controls"
                                className="pointer-events-auto flex flex-wrap items-center justify-end gap-2"
                            >
                                {controls}
                            </div>
                        ) : null}
                    </div>
                </Tag>
            </>
        );
    }

    return (
        <Tag
            data-slot="scene-stage"
            data-stage-variant={variant}
            data-backdrop-mode="stage"
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
                    className="pointer-events-auto absolute right-3 bottom-3 left-3 z-20 flex flex-wrap items-center justify-end gap-2"
                >
                    {controls}
                </div>
            ) : null}
        </Tag>
    );
}
