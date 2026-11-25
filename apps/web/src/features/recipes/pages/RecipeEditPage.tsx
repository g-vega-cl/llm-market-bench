import { type AtmospherePhase, Card, PageLayout } from '@llm-market-bench/ui-design-system';
import { useState } from 'react';
import { assertServerFnResult } from '~/lib/server-fn';
import { saveRecipeFn } from '../api/recipes-api';
import { previewStrategyPromptFn } from '../api/recipes-studio-api';
import { BuilderStatusStrip } from '../builder/BuilderStatusStrip';
import {
    CompiledBotBlueprintSection,
    type WorkspaceTab,
} from '../builder/CompiledBotBlueprintSection';
import {
    deriveWorkspaceStatus,
    describeRun,
    isInFlightRun,
    LiveWarningBanner,
    resolveLiveWarningMessage,
} from '../builder/compiled-bot-status';
import { BotStageHeader } from '../components/BotStageHeader';
import { RecipeNameField } from '../components/RecipeNameField';
import { WaitlistPledgeModal } from '../components/WaitlistPledgeModal';
import type {
    PreviewState,
    PushStrategy,
    RecipeSummaryItem,
    RecipeUserQuotaStatus,
    StrategyRecipeRecord,
    StrategyStage,
} from '../types';
import { upsertSavedRecipeSummary } from '../utils/live-studio-helpers';
import { useBotHeaderActions } from '../utils/use-bot-header-actions';
import { useLatestRecipeRun } from '../utils/use-latest-recipe-run';
import { useRecipeDraft } from '../utils/use-recipe-draft';

export interface RecipeEditPageProps {
    recipeId: string;
    initialStrategy: PushStrategy;
    initialIsLive: boolean;
    initialAtmosphere?: AtmospherePhase;
    initialQuota?: RecipeUserQuotaStatus | null;
    initialUserRecipes?: RecipeSummaryItem[];
}

/**
 * Dedicated Blueprint & Prompt Editor page (`/recipes/$recipeId/edit`).
 * Shares `BotStageHeader` with Overview and Live Runs, while keeping block/tool
 * configuration and prompt preview cleanly separated from performance telemetry.
 */
export function RecipeEditPage({
    recipeId,
    initialStrategy,
    initialIsLive,
    initialAtmosphere,
    initialQuota = null,
    initialUserRecipes = [],
}: RecipeEditPageProps) {
    const draft = useRecipeDraft(initialStrategy, initialStrategy.name);
    const strategy = draft.strategy;
    const stage = strategy.stages[0];

    const [activeTab, setActiveTab] = useState<WorkspaceTab>('blocks');
    const [preview, setPreview] = useState<PreviewState>({ status: 'template' });

    const { run } = useLatestRecipeRun(recipeId);
    const runView = describeRun(run);
    const runInFlight = isInFlightRun(run);
    const promptBlock = stage.blocks.find((block) => block.type === 'prompt');
    const hasEmptyPrompt = !promptBlock?.text.trim();
    const liveWarningMessage = resolveLiveWarningMessage(undefined, stage.selected_tools);

    const persistActiveStrategy = async (
        options: { restore?: boolean } = {},
    ): Promise<StrategyRecipeRecord> => {
        const saved = await draft.save(async (recipe) => {
            const res = await saveRecipeFn({
                data: { recipe, restore: options.restore ?? false },
            });
            return assertServerFnResult(res, 'Saving strategy') as StrategyRecipeRecord;
        });
        actions.setUserRecipes((prev) => upsertSavedRecipeSummary(prev, saved));
        return saved;
    };

    const actions = useBotHeaderActions({
        recipeId,
        recipeName: strategy.name,
        cadence: strategy.cadence,
        initialIsLive,
        initialQuota,
        initialUserRecipes,
        externalBusy: draft.isSaving,
        persistBeforeAction: () => persistActiveStrategy(),
    });

    const isBusy = draft.isSaving || actions.isRunningBacktest || actions.liveControl.isBusy;

    const draftNote = draft.isDirty
        ? 'Unsaved edits — Save Recipe persists changes before any run.'
        : 'Saved.';
    const statusDetail = [
        runInFlight ? runView?.text : draftNote,
        runInFlight ? draftNote : runView?.text,
    ]
        .filter(Boolean)
        .join(' · ');

    const workspaceStatus = deriveWorkspaceStatus({
        hasEmptyPrompt,
        runInFlight,
        runView,
        isCurrentlyScheduledLive: actions.isLive,
        fallback: false,
        hasLiveWarning: Boolean(liveWarningMessage),
        strategyId: recipeId,
        isDirty: draft.isDirty,
        statusDetail,
    });

    const handleSaveRecipe = async () => {
        if (isBusy || !draft.isDirty || hasEmptyPrompt) return;
        try {
            await persistActiveStrategy({ restore: true });
        } catch {
            // Inline error handled by RecipeNameField
        }
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

    return (
        <div className="min-h-screen bg-voxel-canvas text-voxel-ink flex flex-col">
            <BotStageHeader
                recipeId={recipeId}
                recipeName={strategy.name}
                description={strategy.description}
                cadence={strategy.cadence}
                activeTab="edit"
                isOwner
                isLive={actions.isLive}
                initialAtmosphere={initialAtmosphere}
                quotaStatus={actions.quotaStatus}
                isRunningBacktest={actions.isRunningBacktest}
                isTogglingLive={actions.liveControl.isBusy}
                isSaving={draft.isSaving}
                backtestError={actions.backtestError}
                scheduleError={actions.liveControl.scheduleError}
                conflictingLiveRecipe={
                    actions.liveControl.state.kind === 'confirming' ||
                    actions.liveControl.state.kind === 'switching'
                        ? actions.liveControl.state.conflicting
                        : null
                }
                isSwitchingLive={actions.liveControl.state.kind === 'switching'}
                onBacktest={hasEmptyPrompt ? undefined : actions.handleBacktest}
                onToggleLive={hasEmptyPrompt ? undefined : actions.handleToggleLive}
                onConfirmLiveSwitch={actions.handleConfirmSwitch}
                onCancelLiveSwitch={actions.liveControl.cancelSwitch}
                onRequestCapacity={() => actions.setShowPledgeModal(true)}
            />

            <PageLayout maxWidth="xl" className="relative z-10 flex flex-col gap-6">
                <Card padding="md" className="flex flex-col gap-4 min-w-0">
                    <BuilderStatusStrip
                        phase="ready"
                        label={workspaceStatus.label}
                        tone={workspaceStatus.tone}
                        detail={workspaceStatus.detail}
                    />

                    <LiveWarningBanner
                        show={workspaceStatus.showLiveWarning}
                        message={liveWarningMessage}
                    />

                    <RecipeNameField
                        value={strategy.name}
                        onChange={draft.setName}
                        onSave={handleSaveRecipe}
                        isDirty={draft.isDirty}
                        saveState={draft.saveState}
                        errorMessage={draft.saveError}
                        disabled={isBusy || hasEmptyPrompt}
                    />
                </Card>

                <CompiledBotBlueprintSection
                    activeTab={activeTab}
                    onSelectTab={setActiveTab}
                    stage={stage}
                    preview={preview}
                    onStageChange={handleStageChange}
                    onPreviewLiveData={handlePreviewLiveData}
                />

                <WaitlistPledgeModal
                    isOpen={actions.showPledgeModal}
                    onClose={() => actions.setShowPledgeModal(false)}
                    onSubmit={actions.handlePledgeSubmit}
                />
            </PageLayout>
        </div>
    );
}
