import type { AtmospherePhase } from '@llm-market-bench/ui-design-system';
import { Link } from '@tanstack/react-router';
import { useState } from 'react';
import { formatEasternDateTime } from '~/utils/date';
import { activateRecipeTurboFn } from '../api/recipes-quota-api';
import { BotStageHeader } from '../components/BotStageHeader';
import { BotSummaryStrip } from '../components/BotSummaryStrip';
import { WaitlistPledgeModal } from '../components/WaitlistPledgeModal';
import type {
    LivePortfolioSnapshot,
    LiveStatusMeta,
    RecipeCadence,
    RecipeJobRecord,
    RecipeSummaryItem,
    RecipeUserQuotaStatus,
} from '../types';
import { extractLiveRunResult } from '../utils/recipe-insights';
import { useBotHeaderActions } from '../utils/use-bot-header-actions';

export interface RecipeLivePageProps {
    recipeId: string;
    initialData: {
        portfolio: LivePortfolioSnapshot;
        recentLiveRuns: RecipeJobRecord[];
        liveMeta?: LiveStatusMeta;
    } | null;
    cadence?: RecipeCadence;
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

/** Latest run's ET stamp, or the job id when a run never produced a result. */
function latestRunLabel(job: RecipeJobRecord | undefined): string {
    if (!job) return '—';
    const result = extractLiveRunResult(job);
    const stamp = formatEasternDateTime(result?.as_of_utc ?? job.created_at);
    if (stamp && stamp !== 'Unknown') return stamp;
    return job.id.slice(0, 8);
}

const detailLinkClass =
    'text-xs font-normal text-accent underline underline-offset-4 hover:text-accent-hover whitespace-nowrap';

/**
 * Live Runs hub (`/recipes/live/$recipeId`).
 *
 * The card and the live numbers only. The run traces, paper portfolio and closed
 * trades live at `/recipes/live/$recipeId/runs`, which is where the ~4,000 px of
 * prompt output now belongs instead of under this card.
 */
export function RecipeLivePage({
    recipeId,
    initialData,
    cadence = '3h',
    initialAtmosphere,
    initialQuota = null,
    initialUserRecipes = [],
}: RecipeLivePageProps) {
    const [turboExpiresAt, setTurboExpiresAt] = useState<string | null>(
        () => initialData?.liveMeta?.turboExpiresAt ?? null,
    );
    const [turboUsedToday, setTurboUsedToday] = useState<boolean>(
        () => initialData?.liveMeta?.turboUsedToday ?? false,
    );
    const [isActivatingTurbo, setIsActivatingTurbo] = useState(false);
    const [turboError, setTurboError] = useState<string | null>(null);

    const recentLiveRuns = initialData?.recentLiveRuns ?? [];
    const portfolio = initialData?.portfolio ?? null;
    const liveMeta = initialData?.liveMeta;
    const isLiveEnabled = liveMeta ? liveMeta.isLive : true;

    const actions = useBotHeaderActions({
        recipeId,
        recipeName: liveMeta?.recipeName || `Recipe ${recipeId.slice(0, 8)}`,
        cadence: liveMeta?.cadence ?? cadence,
        initialIsLive: isLiveEnabled,
        initialQuota,
        initialUserRecipes,
    });

    const handleActivateTurbo = async () => {
        if (isActivatingTurbo) return;
        setIsActivatingTurbo(true);
        setTurboError(null);
        try {
            const res = await activateRecipeTurboFn({ data: { recipeId } });
            setTurboExpiresAt(res.turboExpiresAt);
            setTurboUsedToday(true);
        } catch (err) {
            setTurboError(err instanceof Error ? err.message : 'Failed activating Turbo mode');
        } finally {
            setIsActivatingTurbo(false);
        }
    };

    const isOwner = liveMeta?.isOwner ?? false;
    const conflictingLiveRecipe =
        actions.liveControl.state.kind === 'confirming' ||
        actions.liveControl.state.kind === 'switching'
            ? actions.liveControl.state.conflicting
            : null;

    const latestRun = recentLiveRuns[0];
    const latestResult = extractLiveRunResult(latestRun);

    return (
        <div className="min-h-screen bg-voxel-canvas text-voxel-ink flex flex-col">
            <BotStageHeader
                recipeId={recipeId}
                recipeName={liveMeta?.recipeName || `Live Runs · ${recipeId.slice(0, 8)}`}
                description={liveMeta?.description}
                cadence={liveMeta?.cadence ?? cadence}
                activeTab="live"
                isOwner={isOwner}
                isPublic={liveMeta?.isPublic}
                isTemplate={liveMeta?.isTemplate}
                isLive={actions.isLive}
                turboExpiresAt={turboExpiresAt}
                turboUsedToday={turboUsedToday}
                initialAtmosphere={initialAtmosphere}
                quotaStatus={actions.quotaStatus}
                isRunningBacktest={actions.isRunningBacktest}
                isTogglingLive={actions.liveControl.isBusy}
                isActivatingTurbo={isActivatingTurbo}
                isForking={actions.isForking}
                backtestError={actions.backtestError}
                scheduleError={actions.liveControl.scheduleError}
                forkError={actions.forkError}
                turboError={turboError}
                conflictingLiveRecipe={conflictingLiveRecipe}
                isSwitchingLive={actions.liveControl.state.kind === 'switching'}
                onBacktest={isOwner ? actions.handleBacktest : undefined}
                onToggleLive={isOwner ? actions.handleToggleLive : undefined}
                onConfirmLiveSwitch={actions.handleConfirmSwitch}
                onCancelLiveSwitch={actions.liveControl.cancelSwitch}
                onActivateTurbo={isOwner ? handleActivateTurbo : undefined}
                onFork={!isOwner ? actions.handleFork : undefined}
                onRequestCapacity={() => actions.setShowPledgeModal(true)}
            >
                <BotSummaryStrip
                    items={[
                        {
                            label: 'Total Equity',
                            value: (
                                <span className="font-mono tabular-nums">
                                    {portfolio ? formatDollar(portfolio.total_equity) : '—'}
                                </span>
                            ),
                        },
                        {
                            label: 'Cash',
                            value: (
                                <span className="font-mono tabular-nums">
                                    {portfolio ? formatDollar(portfolio.cash) : '—'}
                                </span>
                            ),
                        },
                        {
                            label: 'Open Positions',
                            value: (
                                <span className="font-mono tabular-nums">
                                    {portfolio ? `${portfolio.open_positions.length} / 4` : '—'}
                                </span>
                            ),
                        },
                        {
                            label: 'Latest Run',
                            value: (
                                <span className="font-mono tabular-nums">
                                    {latestRunLabel(latestRun)}
                                    {latestResult
                                        ? ` · ${latestResult.signals.length} signals`
                                        : ''}
                                </span>
                            ),
                        },
                    ]}
                    detailLink={
                        <Link
                            to="/recipes/live/$recipeId/runs"
                            params={{ recipeId }}
                            className={detailLinkClass}
                        >
                            Run traces, portfolio &amp; closed trades →
                        </Link>
                    }
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
