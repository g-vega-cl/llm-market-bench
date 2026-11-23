import { Badge, Button } from '@llm-market-bench/ui-design-system';
import { Link } from '@tanstack/react-router';
import { RecipeNameField, type RecipeSaveState } from '../components/RecipeNameField';
import type { PushStrategy } from '../types';

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
    onNameChange: (name: string) => void;
    onSave: () => void;
    onBacktest: () => void;
    onToggleLive: () => void;
}

function resolveStatusBadge(strategyId?: string, fallback?: boolean): string {
    if (strategyId) return 'SAVED BOT';
    if (fallback) return 'CLOSEST WORKING TEMPLATE';
    return 'BOT READY';
}

/**
 * Focused bot identity, status badges, and primary CTAs rendered inside
 * CompiledBotWorkspace's `.voxel-card` hero container (zero nested cards).
 */
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
    onNameChange,
    onSave,
    onBacktest,
    onToggleLive,
}: CompiledBotSummaryCardProps) {
    const stage = strategy.stages[0];
    const activeBlockTypes = Array.from(new Set(stage.blocks.map((b) => b.type)));
    const statusBadge = resolveStatusBadge(strategy.id, fallback);
    const descriptionText = summary || strategy.description;

    return (
        <div className="flex flex-col gap-4 min-w-0">
            <div className="flex flex-wrap items-baseline gap-x-2 gap-y-2 min-w-0">
                <Badge colorScheme={fallback ? 'warning' : 'success'} variant="soft" size="sm">
                    {statusBadge}
                </Badge>
                <span className="text-xs font-normal text-voxel-muted whitespace-nowrap">
                    Live: 30m
                </span>
                <span className="text-xs font-normal text-voxel-muted whitespace-nowrap">
                    {`· Backtest: ${strategy.cadence}`}
                </span>
                <span className="text-xs font-normal text-voxel-muted whitespace-nowrap">
                    · one LLM call
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

            {descriptionText ? (
                <p className="text-xs font-normal text-voxel-muted leading-relaxed break-words">
                    {descriptionText}
                </p>
            ) : null}

            <div className="flex flex-wrap gap-2">
                {activeBlockTypes.map((type) => (
                    <Badge key={type} colorScheme="accent" variant="soft" size="xs">
                        {type}
                    </Badge>
                ))}
                <Badge colorScheme="neutral" variant="soft" size="xs">
                    {stage.selected_tools.length} tools
                </Badge>
            </div>

            <div className="flex flex-wrap items-center gap-4 pt-2">
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
    );
}
