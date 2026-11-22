import { Badge, Button, Card } from '@llm-market-bench/ui-design-system';
import { Link } from '@tanstack/react-router';
import type { PushStrategy } from '../recipes/types';
import {
    ARCHETYPE_IDS,
    ARCHETYPES,
    type ArchetypeId,
    type ArchetypeMatch,
    AXIS_DEFINITIONS,
    type QuizScoreResult,
} from './personality-data';

function promptSnippet(recipe: PushStrategy): string {
    const promptBlock = recipe.stages[0]?.blocks.find((block) => block.type === 'prompt');
    if (!promptBlock || promptBlock.type !== 'prompt') return recipe.description ?? '';
    return promptBlock.text;
}

function summarizeRecipeBlocks(recipe: PushStrategy): string[] {
    const blocks = recipe.stages[0]?.blocks ?? [];
    const tags: string[] = [];
    for (const block of blocks) {
        if (block.type === 'news') {
            tags.push(`News (${block.recency_hours}h)`);
        } else if (block.type === 'memories') {
            tags.push(`Memories (${block.category})`);
        } else if (block.type === 'technicals') {
            tags.push(block.rules.map((r) => `${r.metric} ${r.operator} ${r.target}`).join(' · '));
        }
    }
    return tags;
}

function BotRecommendationCard({
    match,
    rankLabel,
    builderIdeaPrompt,
}: {
    match: ArchetypeMatch;
    rankLabel: string;
    builderIdeaPrompt: string;
}) {
    const blockSummaries = summarizeRecipeBlocks(match.recipe);
    return (
        <Card
            variant="outlined"
            padding="md"
            data-testid="bot-recommendation-card"
            className="flex h-full min-w-0 flex-col gap-3 rounded-none"
        >
            <div className="flex flex-wrap items-center justify-between gap-2 border-b-2 border-voxel-bevel-hi pb-2">
                <Badge colorScheme="accent" variant="soft" size="sm">
                    {rankLabel}
                </Badge>
                <span className="text-xs font-normal text-voxel-muted">
                    {`${match.fitPercent}% profile match`}
                </span>
            </div>

            <div className="flex flex-col gap-1">
                <h3 className="text-sm font-bold text-voxel-ink">{match.recipe.name}</h3>
                <p className="text-xs font-normal text-voxel-muted">{match.recipe.description}</p>
            </div>

            <p className="border-l-2 border-voxel-bevel-hi bg-voxel-surface p-3 text-xs font-normal text-voxel-ink">
                {promptSnippet(match.recipe)}
            </p>

            <div className="flex flex-wrap gap-2">
                <Badge colorScheme="neutral" variant="soft" size="sm">
                    {`Backtest: ${match.recipe.cadence}`}
                </Badge>
                <Badge colorScheme="neutral" variant="soft" size="sm">
                    {`${match.recipe.stages[0]?.selected_tools.length ?? 0} live tools`}
                </Badge>
                {blockSummaries.map((summary) => (
                    <Badge key={summary} colorScheme="neutral" variant="soft" size="sm">
                        {summary}
                    </Badge>
                ))}
            </div>

            <div className="mt-auto flex flex-wrap gap-2 pt-2">
                <Link
                    to="/build"
                    search={{ idea: builderIdeaPrompt }}
                    className="voxel-btn inline-flex items-center justify-center bg-accent px-4 py-2 text-xs font-normal uppercase tracking-wider text-accent-ink hover:bg-accent-hover"
                >
                    Build this bot
                </Link>
                <Link
                    to="/recipes"
                    className="voxel-btn inline-flex items-center justify-center bg-voxel-surface px-4 py-2 text-xs font-normal text-voxel-ink hover:bg-voxel-elevated"
                >
                    Open Recipe Studio
                </Link>
            </div>
        </Card>
    );
}

export interface PersonalityResultPanelProps {
    result: QuizScoreResult;
    copiedLink: boolean;
    onCopyShareUrl: (archetypeId: ArchetypeId) => void;
    onRetake: () => void;
    onInspectArchetype: (archetypeId: ArchetypeId) => void;
}

/**
 * Renders the matched archetype plaque (`personality-result`) using recessed
 * `.voxel-trough` (`Card variant="outlined"`) children to honor the zero nested
 * `.voxel-card` rule from `.agents/rules/design-spec.md`.
 */
export function PersonalityResultPanel({
    result,
    copiedLink,
    onCopyShareUrl,
    onRetake,
    onInspectArchetype,
}: PersonalityResultPanelProps) {
    const primaryArch = result.primary.archetype;

    return (
        <div
            data-testid="personality-result"
            className="scene-scrim voxel-card flex w-full max-w-4xl flex-col gap-6 rounded-none p-6"
        >
            <div className="flex flex-wrap items-start justify-between gap-4 border-b-2 border-voxel-bevel-hi pb-4">
                <div className="flex flex-col gap-2">
                    <div className="flex flex-wrap items-center gap-2">
                        <Badge colorScheme="accent" variant="soft" size="sm">
                            {`${result.primary.fitPercent}% style fit`}
                        </Badge>
                        <Badge colorScheme="neutral" variant="soft" size="sm">
                            {`Best Bot: ${primaryArch.recipeName}`}
                        </Badge>
                    </div>
                    <h2 data-testid="archetype-title" className="text-sm font-bold text-voxel-ink">
                        {primaryArch.title}
                    </h2>
                    <p className="max-w-prose text-xs font-normal text-voxel-muted">
                        {primaryArch.summary}
                    </p>
                </div>

                <div className="flex flex-wrap gap-2">
                    <Button
                        type="button"
                        variant="outline"
                        colorScheme="neutral"
                        size="sm"
                        onClick={() => onCopyShareUrl(primaryArch.id)}
                    >
                        {copiedLink ? 'Share link copied' : 'Copy share link'}
                    </Button>
                    <Button
                        type="button"
                        variant="outline"
                        colorScheme="neutral"
                        size="sm"
                        data-testid="retake-quiz"
                        onClick={onRetake}
                    >
                        Retake 10Q quiz
                    </Button>
                </div>
            </div>

            <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,18rem),1fr))] gap-4">
                <div
                    data-testid="axis-breakdown"
                    className="voxel-trough flex flex-col gap-3 rounded-none p-4"
                >
                    <h3 className="text-sm font-bold text-voxel-ink">4-Axis Diagnostic Profile</h3>
                    {AXIS_DEFINITIONS.map((axis) => {
                        const score = result.profile[axis.id];
                        return (
                            <div key={axis.id} className="flex flex-col gap-1">
                                <div className="flex items-center justify-between gap-2 text-xs font-normal">
                                    <span className="text-voxel-ink">{axis.label}</span>
                                    <span className="text-accent">{`${score}/100`}</span>
                                </div>
                                <div className="h-2 w-full overflow-hidden rounded-none border-2 border-voxel-bevel-lo bg-voxel-surface">
                                    <div
                                        className="h-full bg-accent"
                                        style={{ width: `${score}%` }}
                                    />
                                </div>
                                <div className="flex justify-between gap-2 text-xs font-normal text-voxel-muted">
                                    <span>{axis.lowLabel}</span>
                                    <span>{axis.highLabel}</span>
                                </div>
                            </div>
                        );
                    })}
                </div>

                <div className="voxel-trough flex flex-col justify-between gap-3 rounded-none p-4">
                    <div className="flex flex-col gap-2">
                        <h3 className="text-sm font-bold text-voxel-ink">Edge &amp; Blind Spot</h3>
                        <ul className="flex flex-col gap-1.5 text-xs font-normal text-voxel-ink">
                            {primaryArch.strengths.map((s) => (
                                <li key={s}>{`• ${s}`}</li>
                            ))}
                        </ul>
                    </div>
                    <div className="border-t-2 border-voxel-bevel-hi pt-2">
                        <p className="text-xs font-normal text-voxel-muted">
                            {`Watchout: ${primaryArch.watchout}`}
                        </p>
                    </div>
                </div>
            </div>

            <div className="flex flex-col gap-3">
                <h3 className="text-sm font-bold text-voxel-ink">
                    Your Top-2 Matched Trading Bots
                </h3>
                <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,19rem),1fr))] items-stretch gap-4">
                    <BotRecommendationCard
                        match={result.primary}
                        rankLabel="#1 Best Bot Match"
                        builderIdeaPrompt={primaryArch.builderIdeaPrompt}
                    />
                    <BotRecommendationCard
                        match={result.runnerUp}
                        rankLabel="#2 Runner-Up Match"
                        builderIdeaPrompt={result.runnerUp.archetype.builderIdeaPrompt}
                    />
                </div>
            </div>

            <div className="flex flex-col gap-2 border-t-2 border-voxel-bevel-hi pt-4">
                <p className="text-xs font-normal text-voxel-muted">
                    Explore all 5 investing archetypes:
                </p>
                <div className="flex flex-wrap gap-2">
                    {ARCHETYPE_IDS.map((id) => {
                        const arch = ARCHETYPES[id];
                        const active = id === primaryArch.id;
                        return (
                            <Button
                                key={id}
                                type="button"
                                size="sm"
                                variant={active ? 'solid' : 'outline'}
                                colorScheme={active ? 'accent' : 'neutral'}
                                onClick={() => onInspectArchetype(id)}
                            >
                                {arch.title}
                            </Button>
                        );
                    })}
                </div>
            </div>
        </div>
    );
}
