import { type AtmospherePhase, Badge, SceneStage } from '@llm-market-bench/ui-design-system';
import { Link } from '@tanstack/react-router';
import type * as React from 'react';
import { CedarRidgeBackdrop } from '~/features/home/backdrop/CedarRidgeBackdrop';
import { SceneHudControls } from '~/features/home/backdrop/SceneHudControls';
import { useDioramaStage } from '~/features/home/backdrop/useDioramaStage';
import { LIVE_CADENCE_LABEL } from '../utils/market-hours';
import { BotStageSubNav, type BotStageTab } from './BotStageSubNav';

export interface BotSceneShellProps {
    recipeId: string;
    recipeName: string;
    /** Which chip is current. Every page owns its own URL, so the chip says `page`. */
    activeTab: BotStageTab;
    /** Section name for the page's own heading, e.g. `Performance & positions`. */
    sectionTitle: string;
    isOwner: boolean;
    isLive: boolean;
    initialAtmosphere?: AtmospherePhase;
    /**
     * Inline notices that belong to the page's actions (live-switch confirmation,
     * quota or execution errors). Rendered under the sub-nav, inside the scene, so
     * a detail page never loses the feedback the hub card gives.
     */
    alerts?: React.ReactNode;
    children: React.ReactNode;
}

const backLinkClass =
    'text-xs font-normal text-voxel-muted hover:text-voxel-ink underline underline-offset-4 whitespace-nowrap';

/**
 * Chrome for every bot tab except Overview: the same Cedar Ridge page-level world,
 * the bot's name and live state on one line, then the chip row that is the
 * navigation. It renders no card of its own — the panel is the page.
 *
 * The name line exists because the hero card (which carried it) now belongs to
 * Overview alone; without it a detail page opened from a shared link had no bot
 * name anywhere in its body.
 */
export function BotSceneShell({
    recipeId,
    recipeName,
    activeTab,
    sectionTitle,
    isOwner,
    isLive,
    initialAtmosphere,
    alerts,
    children,
}: BotSceneShellProps) {
    const { atmosphere, motion, cycleAtmosphere, toggleMotion } =
        useDioramaStage(initialAtmosphere);

    return (
        <div className="min-h-svh bg-voxel-canvas text-voxel-ink flex flex-col">
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
                    {/* The hub owns the visible h1; a detail page still needs its own
                        document heading, and the repo's convention is a sr-only one. */}
                    <h1 className="sr-only">
                        {recipeName} — {sectionTitle}
                    </h1>
                    <div className="flex flex-wrap items-center justify-between gap-2 border-b border-voxel-bevel-hi pb-3 min-w-0">
                        <Link
                            to="/recipes/$recipeId"
                            params={{ recipeId }}
                            aria-label={`Back to ${recipeName} Overview`}
                            className={backLinkClass}
                        >
                            ← Overview
                        </Link>
                        {/* HUD lives in the header row, not its own band: a floating
                            band between the sub-nav and the panel reads as a gap. */}
                        <SceneHudControls
                            atmosphere={atmosphere}
                            motion={motion}
                            onCycleAtmosphere={cycleAtmosphere}
                            onTogglePaused={toggleMotion}
                        />
                    </div>
                    <div className="flex flex-wrap items-center gap-2 min-w-0">
                        <span className="text-lg font-bold text-voxel-ink break-words min-w-0">
                            {recipeName}
                        </span>
                        {isLive ? (
                            <Badge variant="solid" colorScheme="success" size="xs" showDot>
                                Live: ON ({LIVE_CADENCE_LABEL})
                            </Badge>
                        ) : (
                            <Badge variant="soft" colorScheme="neutral" size="xs" showDot>
                                Live: PAUSED
                            </Badge>
                        )}
                    </div>
                    <BotStageSubNav recipeId={recipeId} activeTab={activeTab} isOwner={isOwner} />
                    {alerts}
                </div>
            </SceneStage>

            {/* SceneStage centres a `max-w-7xl` box inside its own `px-6`, so the
                panel must be one `max-w-7xl` *plus* that padding wide for its card
                edge to sit on the back link's edge instead of 24 px to the right.
                PageLayout's `maxWidth` presets would emit a competing `max-w-*`
                utility (clsx, not tailwind-merge), so this box is written out. */}
            <div className="relative z-10 mx-auto flex w-full max-w-[calc(80rem+3rem)] flex-col gap-6 px-6 pb-8 md:pb-12">
                {children}
            </div>
        </div>
    );
}
