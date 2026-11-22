import { type AtmospherePhase, SceneStage } from '@llm-market-bench/ui-design-system';
import { Link } from '@tanstack/react-router';
import { GardenBackdrop } from '../backdrop/GardenBackdrop';
import { SceneHudControls } from '../backdrop/SceneHudControls';
import { useDioramaStage } from '../backdrop/useDioramaStage';

export interface HomeCtaPageProps {
    /** SSR-resolved market-ET atmosphere phase passed from route loader to eliminate initial flash. */
    initialAtmosphere?: AtmospherePhase;
}

/**
 * The homepage: crisp open-sky hero above the panoramic Cedar Sanctuary
 * voxel diorama. Built on `SceneStage` (`variant="hero"`, `motionRole="reactive"`).
 */
export function HomeCtaPage({ initialAtmosphere }: HomeCtaPageProps) {
    const { atmosphere, paused, setPaused, cycleAtmosphere, toggleMotion } =
        useDioramaStage(initialAtmosphere);

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
                <SceneHudControls
                    atmosphere={atmosphere}
                    paused={paused}
                    onCycleAtmosphere={cycleAtmosphere}
                    onTogglePaused={toggleMotion}
                />
            }
        >
            <div
                data-testid="home-hero-content"
                className="flex flex-1 flex-col items-center justify-start gap-6 pb-16 text-center"
            >
                <div className="flex flex-col items-center gap-2">
                    <p className="home-hero-copy text-sm font-bold tracking-[0.28em] uppercase text-accent">
                        Benchify
                    </p>

                    <h1 className="home-hero-heading max-w-[16ch] text-balance text-[clamp(2.1rem,5vw,3.35rem)] font-bold leading-[1.06] text-voxel-ink">
                        Build your own trading bot.
                    </h1>

                    <p className="home-hero-copy max-w-[44ch] text-xs font-normal leading-relaxed text-voxel-ink">
                        Describe a strategy in plain English, test it on point-in-time news, and
                        switch it Live.
                    </p>
                </div>

                <div
                    data-testid="home-cta-actions"
                    className="flex w-full max-w-md flex-col items-center gap-4"
                >
                    <Link
                        to="/lab"
                        data-testid="start-building"
                        className="voxel-btn voxel-btn--hero inline-flex w-full max-w-xs min-h-14 items-center justify-center bg-accent px-10 py-4 text-sm font-bold uppercase tracking-[0.16em] text-accent-ink hover:bg-accent-hover"
                    >
                        Start building
                    </Link>

                    <Link
                        to="/personality"
                        data-testid="take-personality-test"
                        className="voxel-btn inline-flex w-full max-w-xs min-h-10 items-center justify-center bg-voxel-surface px-6 py-2 text-sm font-bold text-voxel-ink hover:bg-voxel-elevated"
                    >
                        Take the investing style test
                    </Link>

                    <Link
                        to="/leaderboard"
                        className="home-hero-copy text-sm font-bold text-voxel-ink underline decoration-voxel-bevel-hi underline-offset-4 hover:text-accent"
                    >
                        See how the published bots are doing
                    </Link>
                </div>
            </div>
        </SceneStage>
    );
}
