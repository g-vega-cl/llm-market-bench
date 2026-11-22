import { Badge, Button, Card } from '@llm-market-bench/ui-design-system';
import { Link } from '@tanstack/react-router';
import { PromptVisualizer } from '../components/PromptVisualizer';
import { RecipeNameField, type RecipeSaveState } from '../components/RecipeNameField';
import { StageBuilder } from '../components/StageBuilder';
import type { PreviewState, PushStrategy, StrategyStage } from '../types';

export interface CompiledBotSummaryCardProps {
    strategy: PushStrategy;
    summary?: string;
    fallback?: boolean;
    isDirty: boolean;
    isBusy: boolean;
    saveState: RecipeSaveState;
    saveError: string | null;
    isRunningBacktest: boolean;
    isTogglingLive: boolean;
    isCurrentlyScheduledLive: boolean;
    backtestButtonLabel: string;
    showBlockEditor: boolean;
    showRawPrompt: boolean;
    preview: PreviewState;
    onNameChange: (name: string) => void;
    onSave: () => void;
    onBacktest: () => void;
    onToggleLive: () => void;
    onToggleBlockEditor: () => void;
    onToggleRawPrompt: () => void;
    onStageChange: (updated: StrategyStage) => void;
    onPreviewLiveData: () => void;
}

function resolveStatusBadge(strategyId?: string, fallback?: boolean): string {
    if (strategyId) return 'SAVED BOT';
    if (fallback) return 'CLOSEST WORKING TEMPLATE';
    return 'BOT READY';
}

export function CompiledBotSummaryCard({
    strategy,
    summary,
    fallback = false,
    isDirty,
    isBusy,
    saveState,
    saveError,
    isRunningBacktest,
    isTogglingLive,
    isCurrentlyScheduledLive,
    backtestButtonLabel,
    showBlockEditor,
    showRawPrompt,
    preview,
    onNameChange,
    onSave,
    onBacktest,
    onToggleLive,
    onToggleBlockEditor,
    onToggleRawPrompt,
    onStageChange,
    onPreviewLiveData,
}: CompiledBotSummaryCardProps) {
    const stage = strategy.stages[0];
    const activeBlockTypes = Array.from(new Set(stage.blocks.map((b) => b.type)));
    const statusBadge = resolveStatusBadge(strategy.id, fallback);
    const descriptionText = summary || strategy.description;

    return (
        <>
            <Card padding="lg" className="flex flex-col gap-4">
                <div className="flex flex-wrap items-center gap-2">
                    <Badge colorScheme={fallback ? 'warning' : 'success'} variant="soft" size="sm">
                        {statusBadge}
                    </Badge>
                    <span className="text-xs font-normal text-voxel-muted">
                        Live: 30m · Backtest: {strategy.cadence} · one LLM call
                    </span>
                </div>

                <RecipeNameField
                    value={strategy.name}
                    onChange={onNameChange}
                    onSave={onSave}
                    isDirty={isDirty}
                    saveState={saveState}
                    errorMessage={saveError}
                    disabled={isBusy}
                />

                {descriptionText && (
                    <p className="text-xs font-normal text-voxel-muted leading-relaxed">
                        {descriptionText}
                    </p>
                )}

                <div className="flex flex-wrap gap-1.5">
                    {activeBlockTypes.map((type) => (
                        <Badge key={type} colorScheme="accent" variant="soft" size="xs">
                            {type}
                        </Badge>
                    ))}
                    <Badge colorScheme="neutral" variant="soft" size="xs">
                        {stage.selected_tools.length} tools
                    </Badge>
                </div>

                <div className="flex flex-wrap items-center gap-3 pt-2">
                    <Button
                        size="md"
                        variant="solid"
                        onClick={onBacktest}
                        disabled={isBusy}
                        isLoading={isRunningBacktest}
                    >
                        {backtestButtonLabel}
                    </Button>

                    <Button
                        size="sm"
                        variant={isCurrentlyScheduledLive ? 'solid' : 'outline'}
                        colorScheme={isCurrentlyScheduledLive ? 'success' : 'neutral'}
                        onClick={onToggleLive}
                        disabled={isBusy}
                        isLoading={isTogglingLive}
                    >
                        {isCurrentlyScheduledLive ? 'Live: ON (30m)' : 'Enable Live (30m)'}
                    </Button>

                    {isCurrentlyScheduledLive && strategy.id && (
                        <Link
                            to="/recipes/live/$recipeId"
                            params={{ recipeId: strategy.id }}
                            className="text-xs font-bold text-success hover:underline underline-offset-4"
                        >
                            Live Status →
                        </Link>
                    )}
                </div>
            </Card>

            <div className="flex flex-col gap-3">
                <div>
                    <Button
                        size="sm"
                        variant="outline"
                        colorScheme="neutral"
                        aria-expanded={showBlockEditor}
                        onClick={onToggleBlockEditor}
                    >
                        {showBlockEditor ? 'Hide blocks & tools ▲' : 'Edit blocks & tools ▼'}
                    </Button>
                </div>

                {showBlockEditor && (
                    <div className="flex flex-col gap-4">
                        <StageBuilder stage={stage} onChange={onStageChange} />

                        <div>
                            <Button
                                size="sm"
                                variant="outline"
                                colorScheme="neutral"
                                aria-expanded={showRawPrompt}
                                onClick={onToggleRawPrompt}
                            >
                                {showRawPrompt ? 'Hide raw prompt ▲' : 'View raw prompt ▼'}
                            </Button>
                        </div>

                        {showRawPrompt && (
                            <PromptVisualizer
                                stage={stage}
                                previewState={preview}
                                onPreviewLiveData={onPreviewLiveData}
                            />
                        )}
                    </div>
                )}
            </div>
        </>
    );
}
