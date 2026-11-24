import {
    type AtmospherePhase,
    Badge,
    Button,
    SceneStage,
} from '@llm-market-bench/ui-design-system';
import { Link } from '@tanstack/react-router';
import { useEffect, useState } from 'react';
import { GardenBackdrop } from '~/features/home/backdrop/GardenBackdrop';
import { SceneHudControls } from '~/features/home/backdrop/SceneHudControls';
import { useDioramaStage } from '~/features/home/backdrop/useDioramaStage';
import type {
    BacktestError,
    RecipeCadence,
    RecipeSummaryItem,
    RecipeUserQuotaStatus,
} from '../types';
import {
    formatTurboRemainingLabel,
    getNextLiveSlotLabel,
    LIVE_CADENCE_LABEL,
} from '../utils/market-hours';
import { BotStageSubNav, type BotStageTab } from './BotStageSubNav';
import { LiveSwitchConfirmation } from './LiveSwitchConfirmation';
import { resolveBacktestButtonLabel, StudioAlertSlot } from './RecipeGuideAndQuotaBlock';
import { TurboButton } from './TurboButton';

export type { BotStageTab } from './BotStageSubNav';

export interface BotStageHeaderProps {
    recipeId: string;
    recipeName: string;
    description?: string;
    cadence: RecipeCadence;
    activeTab: BotStageTab;
    isOwner: boolean;
    isPublic?: boolean;
    isTemplate?: boolean;
    isLive: boolean;
    turboExpiresAt?: string | null;
    turboUsedToday?: boolean;
    initialAtmosphere?: AtmospherePhase;
    quotaStatus?: RecipeUserQuotaStatus | null;
    isRunningBacktest?: boolean;
    isTogglingLive?: boolean;
    isActivatingTurbo?: boolean;
    isForking?: boolean;
    isSaving?: boolean;
    backtestError?: BacktestError | null;
    scheduleError?: string | null;
    forkError?: string | null;
    turboError?: string | null;
    conflictingLiveRecipe?: RecipeSummaryItem | null;
    isSwitchingLive?: boolean;
    onBacktest?: () => void;
    onToggleLive?: () => void;
    onConfirmLiveSwitch?: () => void;
    onCancelLiveSwitch?: () => void;
    onActivateTurbo?: () => void;
    onFork?: () => void;
    onRequestCapacity?: () => void;
}

const MINUTE_MS = 60_000;

function resolveNextRunText(
    isLive: boolean,
    turboRemaining: string | null,
    nextSlotLabel: string,
): string {
    if (!isLive) return 'Paused';
    if (turboRemaining) return 'within 5m (Turbo)';
    return nextSlotLabel;
}

function resolveLiveToggleLabel(isTogglingLive: boolean, isLive: boolean): string {
    if (isTogglingLive) {
        return isLive ? 'Pausing Live...' : 'Enabling Live...';
    }
    return isLive ? 'Pause Live' : 'Enable Live (30m)';
}

function HeaderStatusBadges({
    isOwner,
    isPublic,
    isTemplate,
    isLive,
    turboRemaining,
}: {
    isOwner: boolean;
    isPublic: boolean;
    isTemplate: boolean;
    isLive: boolean;
    turboRemaining: string | null;
}) {
    return (
        <div className="flex flex-wrap items-center gap-2 min-w-0">
            {!isOwner && (isPublic || isTemplate) ? (
                <Badge variant="soft" colorScheme="info" size="xs">
                    {isTemplate ? 'STARTER TEMPLATE' : 'PUBLIC BOT'}
                </Badge>
            ) : null}
            {!isLive ? (
                <Badge variant="soft" colorScheme="neutral" size="xs" showDot>
                    Live: PAUSED
                </Badge>
            ) : turboRemaining ? (
                <Badge
                    variant="solid"
                    colorScheme="accent"
                    size="xs"
                    showDot
                    suppressHydrationWarning
                >
                    Turbo: {turboRemaining} (5m)
                </Badge>
            ) : (
                <Badge variant="solid" colorScheme="success" size="xs" showDot>
                    Live: ON ({LIVE_CADENCE_LABEL})
                </Badge>
            )}
        </div>
    );
}

function HeaderActionButtons({
    isOwner,
    isLive,
    isBusy,
    activeTab,
    quotaStatus,
    isRunningBacktest,
    isTogglingLive,
    isActivatingTurbo,
    isForking,
    turboExpiresAt,
    turboUsedToday,
    now,
    onBacktest,
    onToggleLive,
    onActivateTurbo,
    onFork,
}: {
    isOwner: boolean;
    isLive: boolean;
    isBusy: boolean;
    activeTab: BotStageTab;
    quotaStatus: RecipeUserQuotaStatus | null;
    isRunningBacktest: boolean;
    isTogglingLive: boolean;
    isActivatingTurbo: boolean;
    isForking: boolean;
    turboExpiresAt: string | null;
    turboUsedToday: boolean;
    now: Date;
    onBacktest?: () => void;
    onToggleLive?: () => void;
    onActivateTurbo?: () => void;
    onFork?: () => void;
}) {
    if (!isOwner) {
        if (!onFork) return null;
        return (
            <Button
                size="sm"
                variant="solid"
                colorScheme="accent"
                disabled={isBusy}
                isLoading={isForking}
                onClick={onFork}
            >
                Fork to My Bots
            </Button>
        );
    }

    return (
        <div className="flex flex-wrap items-center gap-2 shrink-0 max-w-full">
            {onBacktest ? (
                <Button
                    size="sm"
                    variant="solid"
                    colorScheme="accent"
                    disabled={isBusy}
                    isLoading={isRunningBacktest}
                    onClick={onBacktest}
                >
                    {resolveBacktestButtonLabel(isRunningBacktest, quotaStatus)}
                </Button>
            ) : null}
            {onToggleLive ? (
                <Button
                    size="sm"
                    variant={isLive ? 'solid' : 'outline'}
                    colorScheme={isLive ? 'success' : 'neutral'}
                    disabled={isBusy}
                    isLoading={isTogglingLive}
                    onClick={onToggleLive}
                >
                    {resolveLiveToggleLabel(isTogglingLive, isLive)}
                </Button>
            ) : null}
            {activeTab === 'live' && isLive && onActivateTurbo ? (
                <TurboButton
                    turboExpiresAt={turboExpiresAt}
                    turboUsedToday={turboUsedToday}
                    isActivating={isActivatingTurbo}
                    now={now}
                    onActivate={onActivateTurbo}
                />
            ) : null}
        </div>
    );
}

/**
 * Shared living-diorama hero header across `/recipes/$recipeId`,
 * `/recipes/live/$recipeId`, and `/recipes/$recipeId/edit`.
 *
 * Keeps the 4-plane Cedar Sanctuary backdrop spatially clipped inside `SceneStage`
 * and protects navigation and primary CTAs with `scrim="panel"`.
 */
export function BotStageHeader({
    recipeId,
    recipeName,
    description,
    cadence,
    activeTab,
    isOwner,
    isPublic = false,
    isTemplate = false,
    isLive,
    turboExpiresAt = null,
    turboUsedToday = false,
    initialAtmosphere,
    quotaStatus = null,
    isRunningBacktest = false,
    isTogglingLive = false,
    isActivatingTurbo = false,
    isForking = false,
    isSaving = false,
    backtestError = null,
    scheduleError = null,
    forkError = null,
    turboError = null,
    conflictingLiveRecipe = null,
    isSwitchingLive = false,
    onBacktest,
    onToggleLive,
    onConfirmLiveSwitch,
    onCancelLiveSwitch,
    onActivateTurbo,
    onFork,
    onRequestCapacity,
}: BotStageHeaderProps) {
    const { atmosphere, paused, setPaused, cycleAtmosphere, toggleMotion } =
        useDioramaStage(initialAtmosphere);
    const [now, setNow] = useState(() => new Date());

    useEffect(() => {
        setNow(new Date());
        let timer: ReturnType<typeof setTimeout>;
        const schedule = () => {
            const delay = MINUTE_MS - (Date.now() % MINUTE_MS) + 100;
            timer = setTimeout(() => {
                setNow(new Date());
                schedule();
            }, delay);
        };
        schedule();
        return () => clearTimeout(timer);
    }, []);

    const turboRemaining = isLive ? formatTurboRemainingLabel(turboExpiresAt, now) : null;
    const nextSlotLabel = getNextLiveSlotLabel(now);
    const isBusy =
        isSaving ||
        isRunningBacktest ||
        isTogglingLive ||
        isSwitchingLive ||
        isActivatingTurbo ||
        isForking;
    const extraError = forkError || turboError;

    return (
        <SceneStage
            variant="hero"
            atmosphere={atmosphere}
            motionRole="reactive"
            scrim="panel"
            aria-label={`${recipeName} header`}
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
            <div className="flex flex-col gap-4 min-w-0">
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-voxel-bevel-hi pb-3 min-w-0">
                    <Link
                        to="/recipes"
                        className="text-xs font-normal text-voxel-muted hover:text-voxel-ink underline underline-offset-4 whitespace-nowrap"
                    >
                        ← My Bots
                    </Link>

                    <HeaderStatusBadges
                        isOwner={isOwner}
                        isPublic={isPublic}
                        isTemplate={isTemplate}
                        isLive={isLive}
                        turboRemaining={turboRemaining}
                    />
                </div>

                <div className="flex flex-wrap items-start justify-between gap-4 min-w-0">
                    <div className="flex flex-col gap-1.5 min-w-0 flex-1 basis-72">
                        <h1 className="text-lg font-bold text-voxel-ink break-words min-w-0">
                            {recipeName || 'Strategy Bot'}
                        </h1>
                        {description ? (
                            <p className="text-xs font-normal text-voxel-muted break-words">
                                {description}
                            </p>
                        ) : null}
                        <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1 text-xs font-normal text-voxel-muted min-w-0">
                            <span className="whitespace-nowrap">Live: {LIVE_CADENCE_LABEL}</span>
                            <span className="whitespace-nowrap">• Backtest: {cadence}</span>
                            <span className="whitespace-nowrap">• 1 LLM call</span>
                            <span className="whitespace-nowrap" suppressHydrationWarning>
                                • Next run:{' '}
                                {resolveNextRunText(isLive, turboRemaining, nextSlotLabel)}
                            </span>
                        </div>
                    </div>

                    <HeaderActionButtons
                        isOwner={isOwner}
                        isLive={isLive}
                        isBusy={isBusy}
                        activeTab={activeTab}
                        quotaStatus={quotaStatus}
                        isRunningBacktest={isRunningBacktest}
                        isTogglingLive={isTogglingLive}
                        isActivatingTurbo={isActivatingTurbo}
                        isForking={isForking}
                        turboExpiresAt={turboExpiresAt}
                        turboUsedToday={turboUsedToday}
                        now={now}
                        onBacktest={onBacktest}
                        onToggleLive={onToggleLive}
                        onActivateTurbo={onActivateTurbo}
                        onFork={onFork}
                    />
                </div>

                {conflictingLiveRecipe && onConfirmLiveSwitch && onCancelLiveSwitch ? (
                    <LiveSwitchConfirmation
                        conflictingRecipe={conflictingLiveRecipe}
                        targetRecipeName={recipeName}
                        isSwitching={isSwitchingLive}
                        onConfirm={onConfirmLiveSwitch}
                        onCancel={onCancelLiveSwitch}
                    />
                ) : null}

                <StudioAlertSlot
                    backtestError={backtestError}
                    scheduleError={scheduleError}
                    onRequestCapacity={onRequestCapacity ?? (() => {})}
                />

                {extraError ? (
                    <div
                        role="alert"
                        className="border border-danger bg-voxel-surface p-3 text-xs font-normal text-danger rounded-none"
                    >
                        {extraError}
                    </div>
                ) : null}

                <BotStageSubNav recipeId={recipeId} activeTab={activeTab} isOwner={isOwner} />
            </div>
        </SceneStage>
    );
}
