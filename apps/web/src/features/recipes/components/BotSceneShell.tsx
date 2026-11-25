import { type AtmospherePhase, PageLayout, SceneStage } from '@llm-market-bench/ui-design-system';
import { Link } from '@tanstack/react-router';
import type * as React from 'react';
import { CedarRidgeBackdrop } from '~/features/home/backdrop/CedarRidgeBackdrop';
import { SceneHudControls } from '~/features/home/backdrop/SceneHudControls';
import { useDioramaStage } from '~/features/home/backdrop/useDioramaStage';
import { BotStageSubNav, type BotStageTab } from './BotStageSubNav';

export interface BotSceneShellProps {
    recipeId: string;
    recipeName: string;
    /** Tab this detail page belongs to; its sub-nav chip must not claim `aria-current`. */
    activeTab: BotStageTab;
    parent: 'overview' | 'live';
    isOwner: boolean;
    isLive: boolean;
    initialAtmosphere?: AtmospherePhase;
    children: React.ReactNode;
}

const backLinkClass =
    'text-xs font-normal text-voxel-muted hover:text-voxel-ink underline underline-offset-4 whitespace-nowrap';

/**
 * Chrome for a bot detail page: the same Cedar Ridge page-level world as the hub,
 * a back link to the hub it came from, and the sub-nav so the bot stays the
 * context. It renders no card of its own — the panel is the page.
 */
export function BotSceneShell({
    recipeId,
    recipeName,
    activeTab,
    parent,
    isOwner,
    isLive,
    initialAtmosphere,
    children,
}: BotSceneShellProps) {
    const { atmosphere, motion, cycleAtmosphere, toggleMotion } =
        useDioramaStage(initialAtmosphere);

    return (
        <div className="min-h-screen bg-voxel-canvas text-voxel-ink flex flex-col">
            <SceneStage
                variant="hero"
                backdropMode="page"
                atmosphere={atmosphere}
                motionRole="reactive"
                aria-label={`${recipeName} details`}
                backdrop={
                    <CedarRidgeBackdrop
                        atmosphere={atmosphere}
                        motion={motion}
                        fauna={isLive ? 'walking' : 'standby'}
                        className="h-full w-full"
                    />
                }
            >
                <div className="flex flex-col gap-3 min-w-0">
                    <div className="flex flex-wrap items-center justify-between gap-2 border-b border-voxel-bevel-hi pb-3 min-w-0">
                        {parent === 'live' ? (
                            <Link
                                to="/recipes/live/$recipeId"
                                params={{ recipeId }}
                                className={backLinkClass}
                            >
                                ← {recipeName}
                            </Link>
                        ) : (
                            <Link
                                to="/recipes/$recipeId"
                                params={{ recipeId }}
                                className={backLinkClass}
                            >
                                ← {recipeName}
                            </Link>
                        )}
                        {/* HUD lives in the header row, not its own band: a floating
                            band between the sub-nav and the panel reads as a gap. */}
                        <SceneHudControls
                            atmosphere={atmosphere}
                            motion={motion}
                            onCycleAtmosphere={cycleAtmosphere}
                            onTogglePaused={toggleMotion}
                        />
                    </div>
                    <BotStageSubNav
                        recipeId={recipeId}
                        activeTab={activeTab}
                        isOwner={isOwner}
                        markCurrent={false}
                    />
                </div>
            </SceneStage>

            <PageLayout
                maxWidth="xl"
                withPadding={false}
                className="relative z-10 flex flex-col gap-6 px-6 md:px-12 pb-8 md:pb-12"
            >
                {children}
            </PageLayout>
        </div>
    );
}
