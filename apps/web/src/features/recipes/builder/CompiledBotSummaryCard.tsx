import { Badge, Button } from '@llm-market-bench/ui-design-system';
import { Link } from '@tanstack/react-router';
import { RecipeNameField, type RecipeSaveState } from '../components/RecipeNameField';
import type { PushStrategy } from '../types';

export interface CompiledBotSummaryCardProps {
    strategy: PushStrategy;
    summary?: string;
    preferLive?: boolean;
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

function resolveNextActionCopy(isCurrentlyScheduledLive: boolean, preferLive: boolean) {
    if (isCurrentlyScheduledLive) {
        return {
            title: 'Live every 30m during market hours',
            subtitle: 'Inspect live signals or run another backtest below.',
        };
    }
    if (preferLive) {
        return {
            title: 'Recommended next step: run the bot live (30m)',
            subtitle:
                'Some signals need live execution — enable Live (30m) or backtest the offline-compatible logic.',
        };
    }
    return {
        title: 'Next best step: run a 2-week paper backtest',
        subtitle: 'Verify your prompt and blocks on historical news before going live.',
    };
}

function resolveLiveButtonStyle(
    emphasizeLive: boolean,
    isCurrentlyScheduledLive: boolean,
    isTogglingLive: boolean,
) {
    const label = isTogglingLive
        ? isCurrentlyScheduledLive
            ? 'Pausing Live...'
            : 'Enabling Live...'
        : isCurrentlyScheduledLive
          ? 'Live: ON (30m)'
          : 'Enable Live (30m)';

    if (emphasizeLive) {
        return {
            size: 'md' as const,
            variant: 'solid' as const,
            colorScheme: 'accent' as const,
            className: 'voxel-btn--hero',
            label,
        };
    }
    if (isCurrentlyScheduledLive) {
        return {
            size: 'sm' as const,
            variant: 'solid' as const,
            colorScheme: 'success' as const,
            className: undefined,
            label,
        };
    }
    return {
        size: 'sm' as const,
        variant: 'outline' as const,
        colorScheme: 'neutral' as const,
        className: undefined,
        label,
    };
}

function NextActionCtas({
    strategyId,
    preferLive,
    isCurrentlyScheduledLive,
    isBusy,
    isRunningBacktest,
    isTogglingLive,
    backtestButtonLabel,
    onBacktest,
    onToggleLive,
}: {
    strategyId?: string;
    preferLive: boolean;
    isCurrentlyScheduledLive: boolean;
    isBusy: boolean;
    isRunningBacktest: boolean;
    isTogglingLive: boolean;
    backtestButtonLabel: string;
    onBacktest: () => void;
    onToggleLive: () => void;
}) {
    const emphasizeLive = preferLive && !isCurrentlyScheduledLive;
    const liveStyle = resolveLiveButtonStyle(
        emphasizeLive,
        isCurrentlyScheduledLive,
        isTogglingLive,
    );
    const backtestBtn = (
        <Button
            size={emphasizeLive ? 'sm' : 'md'}
            variant={emphasizeLive ? 'outline' : 'solid'}
            colorScheme={emphasizeLive ? 'neutral' : 'accent'}
            className={!emphasizeLive && !isCurrentlyScheduledLive ? 'voxel-btn--hero' : undefined}
            onClick={onBacktest}
            disabled={isBusy}
            isLoading={isRunningBacktest}
        >
            {backtestButtonLabel}
        </Button>
    );
    const liveBtn = (
        <Button
            size={liveStyle.size}
            variant={liveStyle.variant}
            colorScheme={liveStyle.colorScheme}
            className={liveStyle.className}
            onClick={onToggleLive}
            disabled={isBusy}
            isLoading={isTogglingLive}
        >
            {liveStyle.label}
        </Button>
    );

    return (
        <div className="flex flex-wrap items-center gap-4 min-w-0">
            {emphasizeLive ? (
                <>
                    {liveBtn}
                    {backtestBtn}
                </>
            ) : (
                <>
                    {backtestBtn}
                    {liveBtn}
                </>
            )}

            {isCurrentlyScheduledLive && strategyId ? (
                <Link
                    to="/recipes/live/$recipeId/runs"
                    params={{ recipeId: strategyId }}
                    className="text-sm font-bold text-success hover:underline underline-offset-4"
                >
                    Live Runs →
                </Link>
            ) : null}
        </div>
    );
}

/**
 * Focused bot identity, metadata, and unambiguous primary CTA hierarchy inside
 * CompiledBotWorkspace's `.voxel-card` hero container (zero nested cards, zero
 * duplicate status badges — BuilderStatusStrip owns the single status badge).
 */
export function CompiledBotSummaryCard({
    strategy,
    summary,
    preferLive = false,
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
    const nextAction = resolveNextActionCopy(isCurrentlyScheduledLive, preferLive);

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
                    <span className="text-sm font-bold text-voxel-ink">{nextAction.title}</span>
                    <span className="text-xs font-normal text-voxel-muted">
                        {nextAction.subtitle}
                    </span>
                </div>

                <NextActionCtas
                    strategyId={strategy.id}
                    preferLive={preferLive}
                    isCurrentlyScheduledLive={isCurrentlyScheduledLive}
                    isBusy={isBusy}
                    isRunningBacktest={isRunningBacktest}
                    isTogglingLive={isTogglingLive}
                    backtestButtonLabel={backtestButtonLabel}
                    onBacktest={onBacktest}
                    onToggleLive={onToggleLive}
                />
            </div>
        </div>
    );
}
