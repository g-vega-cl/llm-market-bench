import {
    ATMOSPHERE_PHASES,
    type AtmospherePhase,
    Button,
    resolveAtmospherePhase,
    SceneStage,
} from '@llm-market-bench/ui-design-system';
import { Link } from '@tanstack/react-router';
import { useCallback, useEffect, useState } from 'react';
import { GardenBackdrop } from '../backdrop/GardenBackdrop';

const ATMOSPHERE_LABELS: Record<AtmospherePhase, string> = {
    dawn: 'Dawn',
    daylight: 'Daylight',
    dusk: 'Dusk',
    'after-hours': 'After-Hours',
};

/**
 * The homepage: crisp open-sky hero above the multi-layered voxel garden diorama.
 *
 * Built on the design-system `SceneStage` primitive (`variant="hero"`,
 * `motionRole="reactive"`):
 * - Auto-resolves the US Eastern market session atmosphere (`dawn`, `daylight`,
 *   `dusk`, `after-hours`) on mount after a deterministic `'dusk'` SSR render,
 *   with an accessible foreground HUD control to cycle phases on demand.
 * - Keeps the headline and subtitle breathing in the upper zenith sky while
 *   housing the interactive CTA cluster and trust strip inside a compact tactile
 *   `.scene-scrim .voxel-card` Matcha plaque (zero glassmorphism) above the
 *   floating voxel island.
 */
export function HomeCtaPage() {
    const [atmosphere, setAtmosphere] = useState<AtmospherePhase>('dusk');
    const [paused, setPaused] = useState(false);

    useEffect(() => {
        setAtmosphere(resolveAtmospherePhase(new Date(), 'market-et'));
    }, []);

    const cycleAtmosphere = useCallback(() => {
        setAtmosphere((current) => {
            const idx = ATMOSPHERE_PHASES.indexOf(current);
            return ATMOSPHERE_PHASES[(idx + 1) % ATMOSPHERE_PHASES.length];
        });
    }, []);

    const toggleMotion = useCallback(() => {
        setPaused((prev) => !prev);
    }, []);

    return (
        <SceneStage
            variant="hero"
            atmosphere={atmosphere}
            motionRole="reactive"
            className="home-hero-viewport flex w-full flex-col text-voxel-ink"
            backdrop={
                <GardenBackdrop
                    atmosphere={atmosphere}
                    paused={paused}
                    onPausedChange={setPaused}
                    showControls={false}
                    className="h-full w-full"
                />
            }
            controls={
                <>
                    <Button
                        type="button"
                        onClick={cycleAtmosphere}
                        variant="outline"
                        colorScheme="neutral"
                        size="sm"
                        data-testid="atmosphere-switcher"
                    >
                        {`Sky: ${ATMOSPHERE_LABELS[atmosphere]}`}
                    </Button>
                    <Button
                        type="button"
                        onClick={toggleMotion}
                        variant="outline"
                        colorScheme="neutral"
                        size="sm"
                    >
                        {paused ? 'Play motion' : 'Pause motion'}
                    </Button>
                </>
            }
        >
            <div
                data-testid="home-hero-content"
                className="flex flex-1 flex-col items-center justify-start gap-6 pb-12 text-center"
            >
                <div className="flex flex-col items-center gap-2">
                    <p className="home-hero-copy text-sm font-bold tracking-[0.28em] uppercase text-accent">
                        Benchify
                    </p>

                    <h1 className="home-hero-heading max-w-[16ch] text-balance text-[clamp(2.1rem,5vw,3.35rem)] font-bold leading-[1.06] text-voxel-ink">
                        Build your own trading bot.
                    </h1>

                    <p className="home-hero-copy max-w-[44ch] text-sm font-normal leading-relaxed text-voxel-ink">
                        Describe a strategy in plain English, test it on point-in-time news, and
                        switch it Live.
                    </p>
                </div>

                <div
                    data-testid="home-cta-plaque"
                    className="scene-scrim voxel-card flex w-full max-w-md flex-col items-center gap-4 rounded-none px-6 py-5"
                >
                    <Link
                        to="/lab"
                        data-testid="start-building"
                        className="voxel-btn voxel-btn--hero inline-flex w-full max-w-xs min-h-14 items-center justify-center bg-accent px-10 py-4 text-sm font-bold uppercase tracking-[0.16em] text-accent-ink hover:bg-accent-hover"
                    >
                        Start building
                    </Link>

                    <Link
                        to="/leaderboard"
                        className="text-sm font-normal text-voxel-ink underline decoration-voxel-bevel-hi underline-offset-4 hover:text-accent"
                    >
                        See how the published bots are doing
                    </Link>

                    <div
                        data-testid="home-trust-strip"
                        className="flex flex-wrap items-baseline justify-center gap-x-4 gap-y-1 text-sm font-normal text-voxel-ink"
                    >
                        <span className="whitespace-nowrap">Paper cash only</span>
                        <span className="whitespace-nowrap">• Live every 30m ET</span>
                        <span className="whitespace-nowrap">• Every loser stays on the record</span>
                    </div>
                </div>
            </div>
        </SceneStage>
    );
}
