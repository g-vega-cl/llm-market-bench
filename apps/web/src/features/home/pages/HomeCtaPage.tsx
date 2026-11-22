import { SceneStage } from '@llm-market-bench/ui-design-system';
import { Link } from '@tanstack/react-router';
import { useCallback, useEffect, useState } from 'react';
import { GardenBackdrop } from '../backdrop/GardenBackdrop';
import { nextWorldId, SceneHudControls } from '../backdrop/SceneHudControls';
import { syncUrlSearchParam, useDioramaStage } from '../backdrop/useDioramaStage';
import type { WorldId } from '../backdrop/voxel-world';
import { readPreferredWorld, writePreferredWorld } from '../backdrop/world-storage';

export interface HomeCtaPageProps {
    /** Optional initial diorama world passed via URL search param (`?world=`). */
    initialWorld?: WorldId;
}

/**
 * The homepage: crisp open-sky hero above a configurable multi-layered voxel
 * diorama. Built on `SceneStage` (`variant="hero"`, `motionRole="reactive"`).
 */
export function HomeCtaPage({ initialWorld }: HomeCtaPageProps) {
    const { atmosphere, paused, setPaused, cycleAtmosphere, toggleMotion } = useDioramaStage();
    const [world, setWorld] = useState<WorldId>(initialWorld ?? 'sakura-garden');

    useEffect(() => {
        if (initialWorld) {
            setWorld(initialWorld);
            writePreferredWorld(initialWorld);
            return;
        }
        const saved = readPreferredWorld();
        if (saved) setWorld(saved);
    }, [initialWorld]);

    const cycleWorld = useCallback(() => {
        setWorld((current) => {
            const next = nextWorldId(current);
            writePreferredWorld(next);
            syncUrlSearchParam('world', next);
            return next;
        });
    }, []);

    return (
        <SceneStage
            variant="hero"
            atmosphere={atmosphere}
            motionRole="reactive"
            className="home-hero-viewport flex w-full flex-col text-voxel-ink"
            backdrop={
                <GardenBackdrop
                    world={world}
                    atmosphere={atmosphere}
                    paused={paused}
                    onPausedChange={setPaused}
                    showControls={false}
                    className="h-full w-full"
                />
            }
            controls={
                <SceneHudControls
                    world={world}
                    atmosphere={atmosphere}
                    paused={paused}
                    onCycleWorld={cycleWorld}
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

                    <p className="home-hero-copy max-w-[44ch] text-sm font-normal leading-relaxed text-voxel-ink">
                        Describe a strategy in plain English, test it on point-in-time news, and
                        switch it Live.
                    </p>
                </div>

                <div
                    data-testid="home-cta-plaque"
                    className="scene-scrim voxel-card flex w-full max-w-md flex-col items-center gap-3 rounded-none px-6 py-5"
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
