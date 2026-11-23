import { Badge, Button } from '@llm-market-bench/ui-design-system';
import { Link } from '@tanstack/react-router';
import { RecipeNameField, type RecipeSaveState } from '../components/RecipeNameField';
import type { PushStrategy } from '../types';

export interface CompiledBotSummaryCardProps {
    strategy: PushStrategy;
    summary?: string;
    isDirty: boolean;
    isBusy: boolean;
    saveState: RecipeSaveState;
    saveError: string | null;
    isRunningBacktest: boolean;
    isTogglingLive: boolean;
    isCurrentlyScheduledLive: boolean;
    backtestButtonLabel: string;
    onNameChange: (name: string) => void;
    onSave: () => void;
    onBacktest: () => void;
    onToggleLive: () => void;
}

/**
 * Focused bot identity, metadata, and unambiguous primary CTA hierarchy inside
 * CompiledBotWorkspace's `.voxel-card` hero container (zero nested cards, zero
 * duplicate status badges — BuilderStatusStrip owns the single status badge).
 */
export function CompiledBotSummaryCard({
    strategy,
    summary,
    isDirty,
    isBusy,
    saveState,
    saveError,
    isRunningBacktest,
    isTogglingLive,
    isCurrentlyScheduledLive,
    backtestButtonLabel,
    onNameChange,
    onSave,
    onBacktest,
    onToggleLive,
}: CompiledBotSummaryCardProps) {
    const stage = strategy.stages[0];
    const activeBlockTypes = Array.from(new Set(stage.blocks.map((b) => b.type)));
    const descriptionText = summary || strategy.description;

    return (
        <div className="flex flex-col gap-4 min-w-0">
            <RecipeNameField
                value={strategy.name}
                onChange={onNameChange}
                onSave={onSave}
                isDirty={isDirty}
                saveState={saveState}
                errorMessage={saveError}
                disabled={isBusy}
            />

            {descriptionText ? (
                <p className="text-xs font-normal text-voxel-muted leading-relaxed break-words">
                    {descriptionText}
                </p>
            ) : null}

            <div className="flex flex-wrap items-center gap-2 min-w-0">
                {activeBlockTypes.map((type) => (
                    <Badge key={type} colorScheme="accent" variant="soft" size="xs">
                        {type}
                    </Badge>
                ))}
                <Badge colorScheme="neutral" variant="soft" size="xs">
                    {`${stage.selected_tools.length} tools`}
                </Badge>
                <span className="text-xs font-normal text-voxel-muted whitespace-nowrap">
                    {`· Live: 30m · Backtest: ${strategy.cadence} · one LLM call`}
                </span>
            </div>

            <div
                data-testid="compiled-bot-next-action"
                className="voxel-trough bg-voxel-trough rounded-none p-4 flex flex-col gap-3 min-w-0"
            >
                <div className="flex flex-wrap items-center justify-between gap-2 min-w-0">
                    <span className="text-sm font-bold text-voxel-ink">
                        {isCurrentlyScheduledLive
                            ? 'Live every 30m during market hours'
                            : 'Next best step: run a 2-week paper backtest'}
                    </span>
                    <span className="text-xs font-normal text-voxel-muted">
                        {isCurrentlyScheduledLive
                            ? 'Inspect live signals or run another backtest below.'
                            : 'Verify your prompt and blocks on historical news before going live.'}
                    </span>
                </div>

                <div className="flex flex-wrap items-center gap-4 min-w-0">
                    <Button
                        size="md"
                        variant="solid"
                        colorScheme="accent"
                        className={isCurrentlyScheduledLive ? undefined : 'voxel-btn--hero'}
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

                    {isCurrentlyScheduledLive && strategy.id ? (
                        <Link
                            to="/recipes/live/$recipeId"
                            params={{ recipeId: strategy.id }}
                            className="text-sm font-bold text-success hover:underline underline-offset-4"
                        >
                            Live Status →
                        </Link>
                    ) : null}
                </div>
            </div>
        </div>
    );
}
