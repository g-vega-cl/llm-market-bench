import { Button, Card, PageLayout, SectionHeading } from '@llm-market-bench/ui-design-system';
import { Link, useRouterState } from '@tanstack/react-router';
import { useState } from 'react';
import { fetchRecipeQuotaStatusFn } from '../api/recipes-quota-api';
import {
    fetchRecipeAlertsFn,
    markAlertReadFn,
    submitWaitlistPledgeFn,
} from '../api/recipes-studio-api';
import { BotCard } from '../components/BotCard';
import { LiveSwitchConfirmation } from '../components/LiveSwitchConfirmation';
import { RecipeAlertsInbox } from '../components/RecipeAlertsInbox';
import {
    RecentBacktestsStrip,
    RecipeQuotaStrip,
    StudioAlertSlot,
} from '../components/RecipeGuideAndQuotaBlock';
import { WaitlistPledgeModal } from '../components/WaitlistPledgeModal';
import type {
    RecipeAlert,
    RecipeJobRecord,
    RecipeSummaryItem,
    RecipeUserQuotaStatus,
} from '../types';
import { pendingRecipeTarget } from '../utils/pending-recipe-nav';
import { useLiveScheduleControl } from '../utils/use-live-schedule-control';
import { useStrategyRemoval } from '../utils/use-strategy-removal';

export interface RecipeDashboardPageProps {
    recentBacktests?: RecipeJobRecord[];
    initialQuota?: RecipeUserQuotaStatus | null;
    initialUserRecipes?: RecipeSummaryItem[];
}

/**
 * Logged-in /recipes dashboard ("My Bots").
 *
 * Keeps a single primary CTA ("Build Your First Bot →" when empty, "+ Build New Bot"
 * when bots exist) and minimal per-bot cards linking to /build?recipeId=<id>.
 */
export function RecipeDashboardPage({
    recentBacktests = [],
    initialQuota = null,
    initialUserRecipes = [],
}: RecipeDashboardPageProps = {}) {
    const [quotaStatus, setQuotaStatus] = useState<RecipeUserQuotaStatus | null>(initialQuota);
    const [userRecipes, setUserRecipes] = useState<RecipeSummaryItem[]>(initialUserRecipes);
    const [alerts, setAlerts] = useState<RecipeAlert[]>([]);
    const [showAlertsInbox, setShowAlertsInbox] = useState(false);
    const [showPledgeModal, setShowPledgeModal] = useState(false);

    const removal = useStrategyRemoval((item) => {
        setUserRecipes((prev) => prev.filter((r) => r.id !== item.id));
    });

    const refreshQuota = async () => {
        try {
            const next = await fetchRecipeQuotaStatusFn();
            if (next) setQuotaStatus(next);
        } catch {
            // Non-blocking refresh
        }
    };

    const liveControl = useLiveScheduleControl({
        userRecipes,
        quotaStatus,
        onRecipesChange: setUserRecipes,
        onRefreshQuota: refreshQuota,
    });

    const pendingRecipeId = useRouterState({
        select: (state) => pendingRecipeTarget(state.status, state.location)?.recipeId ?? null,
    });
    const pendingDestination = useRouterState({
        select: (state) => pendingRecipeTarget(state.status, state.location)?.destination ?? null,
    });

    const handleLoadAlerts = async () => {
        try {
            const list = await fetchRecipeAlertsFn();
            setAlerts(list);
        } finally {
            setShowAlertsInbox(true);
        }
    };

    const handleMarkAlertRead = async (alertId: string) => {
        await markAlertReadFn({ data: { alertId } });
        setAlerts((prev) => prev.map((a) => (a.id === alertId ? { ...a, is_read: true } : a)));
    };

    const handlePledgeSubmit = async (email: string, tier: string, feedback: string) => {
        await submitWaitlistPledgeFn({
            data: { email, intendedTier: tier, feedback },
        });
    };

    const unreadAlerts = alerts.filter((a) => !a.is_read).length;
    const isActionLocked =
        liveControl.isBusy ||
        liveControl.state.kind === 'confirming' ||
        Boolean(removal.removingId);

    return (
        <div className="min-h-screen bg-voxel-canvas text-voxel-ink">
            <PageLayout maxWidth="xl" className="flex flex-col gap-6">
                <header className="flex flex-wrap items-center justify-between gap-4 border-b border-voxel-bevel-hi pb-4">
                    <div className="flex flex-col gap-1">
                        <SectionHeading className="text-sm">My Bots</SectionHeading>
                        <p className="text-xs font-normal text-voxel-muted">
                            Manage your saved trading bots, live schedules, and 2-week backtests.
                        </p>
                    </div>

                    <div className="flex flex-wrap items-center gap-3">
                        <Button size="sm" variant="outline" onClick={handleLoadAlerts}>
                            Alerts ({unreadAlerts})
                        </Button>
                        {userRecipes.length > 0 && (
                            <Link
                                to="/build"
                                disabled={isActionLocked}
                                aria-disabled={isActionLocked || undefined}
                                className="voxel-btn inline-flex items-center px-4 py-2 text-sm font-bold bg-accent text-voxel-trough hover:bg-accent-hover"
                            >
                                + Build New Bot
                            </Link>
                        )}
                    </div>
                </header>

                <RecipeQuotaStrip
                    quotaStatus={quotaStatus}
                    onRequestCapacity={() => setShowPledgeModal(true)}
                />

                {(liveControl.state.kind === 'confirming' ||
                    liveControl.state.kind === 'switching') && (
                    <LiveSwitchConfirmation
                        conflictingRecipe={liveControl.state.conflicting}
                        targetRecipeName={liveControl.state.target.name}
                        isSwitching={liveControl.state.kind === 'switching'}
                        onConfirm={() => void liveControl.confirmSwitch()}
                        onCancel={liveControl.cancelSwitch}
                    />
                )}

                <StudioAlertSlot
                    backtestError={null}
                    scheduleError={liveControl.scheduleError}
                    onRequestCapacity={() => setShowPledgeModal(true)}
                />

                {userRecipes.length === 0 ? (
                    <Card
                        padding="lg"
                        data-testid="empty-bots-hero"
                        className="flex flex-col items-start gap-4"
                    >
                        <div className="flex flex-col gap-1">
                            <h2 className="text-sm font-bold text-voxel-ink">
                                You haven&apos;t built a bot yet
                            </h2>
                            <p className="text-xs font-normal text-voxel-muted max-w-prose">
                                Describe a trading strategy in plain English and run a 2-week
                                point-in-time backtest on paper cash in under a minute.
                            </p>
                        </div>
                        <Link
                            to="/build"
                            className="voxel-btn inline-flex items-center px-5 py-2.5 text-sm font-bold bg-accent text-voxel-trough hover:bg-accent-hover"
                        >
                            Build Your First Bot →
                        </Link>
                    </Card>
                ) : (
                    <div className="flex flex-col gap-3">
                        <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,20rem),1fr))] gap-4">
                            {userRecipes.map((item) => {
                                const isTogglingThis =
                                    liveControl.state.kind === 'toggling' &&
                                    liveControl.state.recipeId === item.id;
                                return (
                                    <BotCard
                                        key={item.id}
                                        item={item}
                                        pendingDestination={
                                            pendingRecipeId === item.id ? pendingDestination : null
                                        }
                                        isLocked={isActionLocked}
                                        isTogglingLive={isTogglingThis}
                                        isRemoving={removal.removingId === item.id}
                                        onToggleLive={(recipe) => void liveControl.toggle(recipe)}
                                        onRemove={(recipe) => removal.remove(recipe)}
                                    />
                                );
                            })}
                        </div>
                        {removal.errorMessage && (
                            <span role="alert" className="text-xs font-normal text-danger">
                                {removal.errorMessage}
                            </span>
                        )}
                    </div>
                )}

                <RecentBacktestsStrip recentBacktests={recentBacktests} />

                {showAlertsInbox && (
                    <RecipeAlertsInbox
                        alerts={alerts}
                        onClose={() => setShowAlertsInbox(false)}
                        onMarkRead={handleMarkAlertRead}
                    />
                )}

                <WaitlistPledgeModal
                    isOpen={showPledgeModal}
                    onClose={() => setShowPledgeModal(false)}
                    onSubmit={handlePledgeSubmit}
                />
            </PageLayout>
        </div>
    );
}
