import type { AtmospherePhase } from '@llm-market-bench/ui-design-system';
import { useMemo } from 'react';
import { BotStageHeader } from '../components/BotStageHeader';
import { BotSummaryStrip } from '../components/BotSummaryStrip';
import { WaitlistPledgeModal } from '../components/WaitlistPledgeModal';
import type { RecipeOverviewData, RecipeSummaryItem, RecipeUserQuotaStatus } from '../types';
import { deriveOverviewMetrics } from '../utils/overview-metrics';
import { useBotHeaderActions } from '../utils/use-bot-header-actions';

export interface RecipeOverviewPageProps {
    data: RecipeOverviewData;
    initialAtmosphere?: AtmospherePhase;
    initialQuota?: RecipeUserQuotaStatus | null;
    initialUserRecipes?: RecipeSummaryItem[];
}

function formatDollar(value: number): string {
    return `$${value.toLocaleString('en-US', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    })}`;
}

function formatSignedPct(value: number | null): string {
    if (value === null || !Number.isFinite(value)) return '—';
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
}

function returnToneClass(value: number | null): string {
    if (value === null) return 'text-voxel-muted';
    return value >= 0 ? 'text-success' : 'text-danger';
}

/**
 * Overview tab (`/recipes/$recipeId`).
 *
 * The bot's identity, its owner actions and the four numbers that summarise it.
 * Performance, Behaviour and Live Runs are chips in the header, so this page holds
 * no "→" link and no panels: it is one card you can read without scrolling.
 */
export function RecipeOverviewPage({
    data,
    initialAtmosphere,
    initialQuota = null,
    initialUserRecipes = [],
}: RecipeOverviewPageProps) {
    const actions = useBotHeaderActions({
        recipeId: data.recipeId,
        recipeName: data.strategy.name,
        cadence: data.strategy.cadence,
        initialIsLive: data.isLive,
        initialQuota,
        initialUserRecipes,
        initialTurboExpiresAt: data.turboExpiresAt ?? null,
        initialTurboUsedToday: data.turboUsedToday ?? false,
    });

    const metrics = useMemo(
        () =>
            deriveOverviewMetrics({
                portfolio: data.portfolio,
                liveRuns: data.recentLiveRuns,
                backtests: data.recentBacktests,
            }),
        [data.portfolio, data.recentLiveRuns, data.recentBacktests],
    );

    const conflictingLiveRecipe =
        actions.liveControl.state.kind === 'confirming' ||
        actions.liveControl.state.kind === 'switching'
            ? actions.liveControl.state.conflicting
            : null;

    return (
        <div className="min-h-screen bg-voxel-canvas text-voxel-ink flex flex-col">
            <BotStageHeader
                recipeId={data.recipeId}
                recipeName={data.strategy.name}
                description={data.strategy.description}
                cadence={data.strategy.cadence}
                activeTab="overview"
                isOwner={data.isOwner}
                isPublic={data.isPublic}
                isTemplate={data.isTemplate}
                isLive={actions.isLive}
                turboExpiresAt={actions.turboExpiresAt}
                turboUsedToday={actions.turboUsedToday}
                initialAtmosphere={initialAtmosphere}
                quotaStatus={actions.quotaStatus}
                isRunningBacktest={actions.isRunningBacktest}
                isTogglingLive={actions.liveControl.isBusy}
                isActivatingTurbo={actions.isActivatingTurbo}
                isForking={actions.isForking}
                backtestError={actions.backtestError}
                scheduleError={actions.liveControl.scheduleError}
                forkError={actions.forkError}
                turboError={actions.turboError}
                conflictingLiveRecipe={conflictingLiveRecipe}
                isSwitchingLive={actions.liveControl.state.kind === 'switching'}
                onBacktest={actions.handleBacktest}
                onToggleLive={actions.handleToggleLive}
                onConfirmLiveSwitch={actions.handleConfirmSwitch}
                onCancelLiveSwitch={actions.liveControl.cancelSwitch}
                onFork={actions.handleFork}
                onActivateTurbo={actions.handleActivateTurbo}
                onRequestCapacity={() => actions.setShowPledgeModal(true)}
            >
                <BotSummaryStrip
                    items={[
                        {
                            label: 'Total Equity',
                            value: (
                                <span className="font-mono tabular-nums">
                                    {formatDollar(metrics.totalEquity)}
                                </span>
                            ),
                        },
                        {
                            label: 'Net Return',
                            value: (
                                <span
                                    className={`font-mono tabular-nums ${returnToneClass(metrics.netReturnPct)}`}
                                >
                                    {formatSignedPct(metrics.netReturnPct)}
                                </span>
                            ),
                        },
                        {
                            label: 'Win Rate',
                            value: (
                                <span className="font-mono tabular-nums">
                                    {metrics.winRatePct === null
                                        ? '—'
                                        : `${metrics.winRatePct.toFixed(1)}%`}
                                </span>
                            ),
                        },
                        {
                            label: 'Open Positions',
                            value: (
                                <span className="font-mono tabular-nums">
                                    {metrics.openPositionsCount} / 4
                                </span>
                            ),
                        },
                    ]}
                />
            </BotStageHeader>

            <WaitlistPledgeModal
                isOpen={actions.showPledgeModal}
                onClose={() => actions.setShowPledgeModal(false)}
                onSubmit={actions.handlePledgeSubmit}
            />
        </div>
    );
}
