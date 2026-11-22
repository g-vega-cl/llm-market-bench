import { Button } from '@llm-market-bench/ui-design-system';
import { usePostHog } from '@posthog/react';
import { Link, useNavigate } from '@tanstack/react-router';
import { useState } from 'react';
import { track } from '~/lib/analytics';
import { enqueueRecipeJobFn, saveRecipeFn } from '../api/recipes-api';
import { fetchRecipeQuotaStatusFn } from '../api/recipes-quota-api';
import { previewStrategyPromptFn, submitWaitlistPledgeFn } from '../api/recipes-studio-api';
import { LiveSwitchConfirmation } from '../components/LiveSwitchConfirmation';
import {
    resolveBacktestButtonLabel,
    StudioAlertSlot,
} from '../components/RecipeGuideAndQuotaBlock';
import { WaitlistPledgeModal } from '../components/WaitlistPledgeModal';
import type {
    BacktestError,
    BacktestResultData,
    PreviewState,
    PushStrategy,
    RecipeJobRecord,
    RecipeSummaryItem,
    RecipeUserQuotaStatus,
    StrategyRecipeRecord,
    StrategyStage,
} from '../types';
import { buildBacktestError, upsertSavedRecipeSummary } from '../utils/live-studio-helpers';
import { useLatestRecipeRun } from '../utils/use-latest-recipe-run';
import { useLiveScheduleControl } from '../utils/use-live-schedule-control';
import { RecipeSaveError, useRecipeDraft } from '../utils/use-recipe-draft';
import { BuilderStatusStrip } from './BuilderStatusStrip';
import type { StatusTone } from './builder-phases';
import { CompiledBotSummaryCard } from './CompiledBotSummaryCard';

export interface CompiledBotWorkspaceProps {
    initialStrategy: PushStrategy;
    initialQuota?: RecipeUserQuotaStatus | null;
    initialUserRecipes?: RecipeSummaryItem[];
    summary?: string;
    fallback?: boolean;
    onStartOver?: () => void;
}

interface RunView {
    label: string;
    text: string;
    tone: StatusTone;
}

function isInFlightRun(run: RecipeJobRecord | null): boolean {
    return run?.status === 'pending' || run?.status === 'processing';
}

/** What the last backtest is doing, so background work is never invisible. */
function describeRun(run: RecipeJobRecord | null): RunView | null {
    if (!run) return null;
    const progress =
        typeof run.progress_pct === 'number' ? `${Math.round(run.progress_pct)}%` : null;
    switch (run.status) {
        case 'pending':
            return {
                label: 'BACKTEST QUEUED',
                text: `Queued${progress ? ` · ${progress}` : ''} — a worker picks it up shortly. You can keep editing.`,
                tone: 'accent',
            };
        case 'processing':
            return {
                label: 'BACKTEST RUNNING',
                text: `Running${progress ? ` · ${progress}` : ''} — you can keep editing while it works.`,
                tone: 'accent',
            };
        case 'completed':
            return {
                label: 'LAST BACKTEST',
                text: 'Last backtest finished.',
                tone: 'success',
            };
        case 'failed':
            return {
                label: 'LAST BACKTEST',
                text: run.error_message
                    ? `Failed: ${run.error_message}`
                    : 'Failed — re-run it from My Bots.',
                tone: 'danger',
            };
        case 'cancelled':
            return { label: 'LAST BACKTEST', text: 'Cancelled.', tone: 'neutral' };
        default:
            return null;
    }
}

/**
 * Step 2 of /build (and /build?recipeId=<id>):
 * Shows a focused bot summary with a single primary CTA ("▶ Backtest (Random 2W)"),
 * while tucking the 5-block editor and raw prompt visualizer behind collapsible toggles.
 */
export function CompiledBotWorkspace({
    initialStrategy,
    initialQuota = null,
    initialUserRecipes = [],
    summary,
    fallback = false,
    onStartOver,
}: CompiledBotWorkspaceProps) {
    const navigate = useNavigate();
    const posthog = usePostHog();
    const draft = useRecipeDraft(initialStrategy, initialStrategy.id ? initialStrategy.name : null);
    const strategy = draft.strategy;
    const { run } = useLatestRecipeRun(strategy.id);
    const runView = describeRun(run);
    const runInFlight = isInFlightRun(run);
    const draftNote = draft.isDirty
        ? 'Draft not saved yet — Save Recipe persists it before any run.'
        : 'Saved.';
    // Both axes stay visible: a finished run from last week must never hide an
    // unsaved draft, and a running job must never be hidden by the draft note.
    const statusDetail = [
        runInFlight ? runView?.text : draftNote,
        runInFlight ? draftNote : runView?.text,
    ]
        .filter(Boolean)
        .join(' · ');

    const [quotaStatus, setQuotaStatus] = useState<RecipeUserQuotaStatus | null>(initialQuota);
    const [userRecipes, setUserRecipes] = useState<RecipeSummaryItem[]>(initialUserRecipes);
    const [preview, setPreview] = useState<PreviewState>({ status: 'template' });
    const [isRunningBacktest, setIsRunningBacktest] = useState(false);
    const [backtestError, setBacktestError] = useState<BacktestError | null>(null);
    const [showPledgeModal, setShowPledgeModal] = useState(false);
    const [showBlockEditor, setShowBlockEditor] = useState(false);
    const [showRawPrompt, setShowRawPrompt] = useState(false);

    const currentSavedRecord = userRecipes.find((r) => r.id === strategy.id);
    const isCurrentlyScheduledLive = Boolean(currentSavedRecord?.is_live);

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
        onEnabledNavigate: async (recipeId) => {
            await navigate({ to: '/recipes/live/$recipeId', params: { recipeId } });
        },
    });

    const isBusy = draft.isSaving || isRunningBacktest || liveControl.isBusy;

    const persistActiveStrategy = async (
        options: { restore?: boolean } = {},
    ): Promise<StrategyRecipeRecord> => {
        const saved = await draft.save(
            (recipe) =>
                saveRecipeFn({
                    data: { recipe, restore: options.restore ?? false },
                }) as Promise<StrategyRecipeRecord>,
        );
        setUserRecipes((prev) => upsertSavedRecipeSummary(prev, saved));
        return saved;
    };

    const handleSaveRecipe = async () => {
        if (isBusy || !draft.isDirty) return;
        try {
            await persistActiveStrategy({ restore: true });
        } catch {
            // Inline error handled by RecipeNameField
        }
    };

    const handleBacktest = async () => {
        if (isBusy) return;
        setIsRunningBacktest(true);
        liveControl.setScheduleError(null);
        let queuedBacktestJobId: string | undefined;
        let didNavigate = false;
        try {
            const saved = await persistActiveStrategy();
            const job = (await enqueueRecipeJobFn({
                data: { recipeId: saved.id, mode: 'backtest' },
            })) as { id: string; status: string; result_json?: BacktestResultData };
            queuedBacktestJobId = job.id;
            track(posthog, 'run_queued', { recipeId: saved.id, jobId: job.id });
            await navigate({ to: '/recipes/backtest/$jobId', params: { jobId: job.id } });
            didNavigate = true;
            return;
        } catch (err) {
            if (!(err instanceof RecipeSaveError)) {
                setBacktestError((prev) => {
                    const next = buildBacktestError({ err, queuedBacktestJobId });
                    if (!next.backtestJobId && prev?.backtestJobId) {
                        return { ...next, backtestJobId: prev.backtestJobId };
                    }
                    return next;
                });
            }
        } finally {
            setIsRunningBacktest(false);
            if (!didNavigate) await refreshQuota();
        }
    };

    const handleToggleScheduledLive = () => {
        if (isBusy) return;
        setBacktestError(null);
        const target: RecipeSummaryItem = currentSavedRecord ?? {
            id: strategy.id ?? '',
            name: strategy.name,
            cadence: strategy.cadence,
            is_live: isCurrentlyScheduledLive,
            trial_count: 0,
            updated_at: new Date().toISOString(),
        };
        void liveControl.toggle(target, () => persistActiveStrategy());
    };

    const handleStageChange = (updated: StrategyStage) => {
        draft.setStage(updated);
        setPreview({ status: 'template' });
    };

    const handlePreviewLiveData = async () => {
        setPreview({ status: 'loading' });
        try {
            const hydratedByBlockId = await previewStrategyPromptFn({ data: { strategy } });
            setPreview({ status: 'hydrated', hydratedByBlockId });
        } catch (err) {
            setPreview({
                status: 'error',
                message: err instanceof Error ? err.message : 'Failed to preview live data',
            });
        }
    };

    const handlePledgeSubmit = async (email: string, tier: string, feedback: string) => {
        await submitWaitlistPledgeFn({
            data: { email, intendedTier: tier, feedback },
        });
    };

    return (
        <div className="flex flex-col gap-6">
            <BuilderStatusStrip
                phase="ready"
                label={runInFlight ? runView?.label : undefined}
                tone={runInFlight ? runView?.tone : draft.isDirty ? 'neutral' : 'success'}
                detail={statusDetail}
                action={
                    run ? (
                        <Link
                            to="/recipes/backtest/$jobId"
                            params={{ jobId: run.id }}
                            className="text-xs font-normal text-accent underline underline-offset-4 hover:text-accent-hover"
                        >
                            Open run →
                        </Link>
                    ) : undefined
                }
            />
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-voxel-bevel-hi pb-3">
                {onStartOver ? (
                    <Button size="sm" variant="outline" colorScheme="neutral" onClick={onStartOver}>
                        ← Describe a different bot
                    </Button>
                ) : (
                    <Link
                        to="/recipes"
                        className="text-xs font-normal text-voxel-muted hover:text-voxel-ink underline underline-offset-4"
                    >
                        ← My Bots
                    </Link>
                )}
            </div>

            {liveControl.state.kind === 'confirming' && (
                <LiveSwitchConfirmation
                    conflictingRecipe={liveControl.state.conflicting}
                    targetRecipeName={strategy.name}
                    isSwitching={false}
                    onConfirm={() => void liveControl.confirmSwitch(() => persistActiveStrategy())}
                    onCancel={liveControl.cancelSwitch}
                />
            )}

            <StudioAlertSlot
                backtestError={backtestError}
                scheduleError={liveControl.scheduleError}
                onRequestCapacity={() => setShowPledgeModal(true)}
            />

            <CompiledBotSummaryCard
                strategy={strategy}
                summary={summary}
                fallback={fallback}
                isDirty={draft.isDirty}
                isBusy={isBusy}
                saveState={draft.saveState}
                saveError={draft.saveError}
                isRunningBacktest={isRunningBacktest}
                isTogglingLive={liveControl.isBusy}
                isCurrentlyScheduledLive={isCurrentlyScheduledLive}
                backtestButtonLabel={resolveBacktestButtonLabel(isRunningBacktest, quotaStatus)}
                showBlockEditor={showBlockEditor}
                showRawPrompt={showRawPrompt}
                preview={preview}
                onNameChange={draft.setName}
                onSave={handleSaveRecipe}
                onBacktest={handleBacktest}
                onToggleLive={handleToggleScheduledLive}
                onToggleBlockEditor={() => setShowBlockEditor((prev) => !prev)}
                onToggleRawPrompt={() => setShowRawPrompt((prev) => !prev)}
                onStageChange={handleStageChange}
                onPreviewLiveData={handlePreviewLiveData}
            />

            <WaitlistPledgeModal
                isOpen={showPledgeModal}
                onClose={() => setShowPledgeModal(false)}
                onSubmit={handlePledgeSubmit}
            />
        </div>
    );
}
