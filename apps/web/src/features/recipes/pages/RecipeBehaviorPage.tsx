import { type AtmospherePhase, Card, SectionHeading } from '@llm-market-bench/ui-design-system';
import { useMemo } from 'react';
import { BotBehaviorsBlock } from '../components/BotBehaviorsBlock';
import { BotSceneShell } from '../components/BotSceneShell';
import type { RecipeOverviewData } from '../types';
import { computeBotBehaviors } from '../utils/recipe-insights';

export interface RecipeBehaviorPageProps {
    data: RecipeOverviewData;
    initialAtmosphere?: AtmospherePhase;
}

/**
 * Behaviour tab (`/recipes/$recipeId/behavior`).
 *
 * `computeBotBehaviors` reads live turns first and falls back to backtests; with
 * neither, the summary is empty and the block below it renders nothing at all. A
 * chip that opens onto a blank page is worse than a chip that explains itself, so
 * the empty case says which run fills it.
 */
export function RecipeBehaviorPage({ data, initialAtmosphere }: RecipeBehaviorPageProps) {
    const behaviors = useMemo(
        () =>
            computeBotBehaviors({
                strategy: data.strategy,
                liveRuns: data.recentLiveRuns,
                trades: data.portfolio.trades,
                backtests: data.recentBacktests,
            }),
        [data.strategy, data.recentLiveRuns, data.portfolio.trades, data.recentBacktests],
    );

    const hasRunHistory = data.recentLiveRuns.length > 0 || data.recentBacktests.length > 0;

    return (
        <BotSceneShell
            recipeId={data.recipeId}
            recipeName={data.strategy.name}
            activeTab="behavior"
            sectionTitle="Behaviour"
            isOwner={data.isOwner}
            isLive={data.isLive}
            initialAtmosphere={initialAtmosphere}
        >
            {hasRunHistory ? (
                <BotBehaviorsBlock recipeId={data.recipeId} behaviors={behaviors} />
            ) : (
                <Card padding="md" className="flex flex-col gap-2 min-w-0">
                    <SectionHeading>Behaviours</SectionHeading>
                    <div className="voxel-trough bg-voxel-trough p-4">
                        <span className="text-xs font-normal text-voxel-muted">
                            Behaviours appear after the first live run. Every scheduled turn records
                            its tool calls, decisions and exits, and this tab summarises them.
                        </span>
                    </div>
                </Card>
            )}
        </BotSceneShell>
    );
}
