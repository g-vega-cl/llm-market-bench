import { Badge, Button, Card } from '@llm-market-bench/ui-design-system';
import { Link } from '@tanstack/react-router';
import {
    ARCHETYPE_IDS,
    ARCHETYPES,
    type ArchetypeId,
    type ArchetypeMatch,
    AXIS_DEFINITIONS,
    formatRecipeExecutionSpec,
    type QuizScoreResult,
    summarizeRecipeCoreGate,
} from './personality-data';

function BotRecommendationCard({ match, rankLabel }: { match: ArchetypeMatch; rankLabel: string }) {
    const coreGate = summarizeRecipeCoreGate(match.recipe);
    const executionSpec = formatRecipeExecutionSpec(match.recipe);

    return (
        <Card
            variant="outlined"
            padding="md"
            data-testid="bot-recommendation-card"
            className="flex h-full min-w-0 flex-col justify-between gap-4 rounded-none"
        >
            <div className="flex flex-wrap items-baseline justify-between gap-2 border-b-2 border-voxel-bevel-hi pb-2">
                <Badge colorScheme="accent" variant="soft" size="sm">
                    {rankLabel}
                </Badge>
                <span className="min-w-0 whitespace-nowrap text-xs font-normal text-voxel-muted">
                    {`${match.fitPercent}% profile match`}
                </span>
            </div>

            <div className="flex min-w-0 flex-col gap-2">
                <h4 className="text-sm font-bold text-voxel-ink">{match.recipe.name}</h4>
                <p className="text-xs font-normal text-voxel-muted">{match.recipe.description}</p>
            </div>

            <p className="border-l-2 border-voxel-bevel-hi bg-voxel-surface p-3 text-xs font-normal text-voxel-ink">
                {executionSpec}
            </p>

            <div className="flex flex-wrap content-start gap-2">
                <Badge colorScheme="neutral" variant="soft" size="sm">
                    {`Backtest: ${match.recipe.cadence}`}
                </Badge>
                <Badge colorScheme="neutral" variant="soft" size="sm">
                    {`${match.recipe.stages[0]?.selected_tools.length ?? 0} live tools`}
                </Badge>
                <Badge colorScheme="neutral" variant="soft" size="sm">
                    {coreGate}
                </Badge>
            </div>

            <div className="mt-auto flex flex-wrap gap-2 pt-2">
                <Link
                    to="/build"
                    search={{ idea: match.archetype.builderIdeaPrompt }}
                    className="voxel-btn inline-flex items-center justify-center bg-accent px-4 py-2 text-sm font-bold uppercase tracking-wider text-voxel-trough hover:bg-accent-hover"
                >
                    Build this bot
                </Link>
                <Link
                    to="/recipes"
                    className="voxel-btn inline-flex items-center justify-center bg-voxel-surface px-4 py-2 text-sm font-bold text-voxel-ink hover:bg-voxel-elevated"
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
    canReturnToQuizMatch: boolean;
    onCopyShareUrl: (archetypeId: ArchetypeId) => void;
    onReturnToQuizMatch: () => void;
    onRetake: () => void;
    onInspectArchetype: (archetypeId: ArchetypeId) => void;
}

/**
 * Renders the matched archetype plaque (`personality-result`) with a top-anchored
 * 5-archetype switcher and canonical recipe summaries derived directly from
 * `packages/config/starter-recipes.json`, preserving zero nested `.voxel-card`.
 */
export function PersonalityResultPanel({
    result,
    copiedLink,
    canReturnToQuizMatch,
    onCopyShareUrl,
    onReturnToQuizMatch,
    onRetake,
    onInspectArchetype,
}: PersonalityResultPanelProps) {
    const primaryArch = result.primary.archetype;

    return (
        <div
            data-testid="personality-result"
            className="scene-scrim voxel-card flex w-full max-w-4xl flex-col gap-6 rounded-none p-6"
        >
            <div
                data-testid="archetype-switcher"
                className="flex flex-col gap-2 border-b-2 border-voxel-bevel-hi pb-4"
            >
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
                                aria-pressed={active}
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

            <div className="flex flex-wrap items-start justify-between gap-4 border-b-2 border-voxel-bevel-hi pb-4">
                <div className="flex min-w-0 flex-1 basis-80 flex-col gap-2">
                    <div className="flex min-w-0 flex-wrap items-baseline gap-2">
                        <Badge colorScheme="accent" variant="soft" size="sm">
                            {`${result.primary.fitPercent}% style fit`}
                        </Badge>
                        <span
                            data-testid="header-best-bot"
                            className="inline-flex min-w-0 flex-wrap gap-2 text-xs font-normal text-voxel-muted"
                        >
                            <span className="whitespace-nowrap">Best Bot:</span>
                            <span className="min-w-0 break-words">{primaryArch.recipeName}</span>
                        </span>
                    </div>
                    <h2 data-testid="archetype-title" className="text-sm font-bold text-voxel-ink">
                        {primaryArch.title}
                    </h2>
                    <p className="max-w-prose text-xs font-normal leading-relaxed text-voxel-muted">
                        {primaryArch.summary}
                    </p>
                </div>

                <div className="flex min-w-0 max-w-full flex-wrap gap-2">
                    {canReturnToQuizMatch ? (
                        <Button
                            type="button"
                            size="sm"
                            variant="outline"
                            colorScheme="neutral"
                            data-testid="return-to-quiz-match"
                            onClick={onReturnToQuizMatch}
                        >
                            Back to my quiz match
                        </Button>
                    ) : null}
                    <Button
                        type="button"
                        variant="outline"
                        colorScheme="neutral"
                        size="sm"
                        onClick={() => onCopyShareUrl(primaryArch.id)}
                    >
                        {copiedLink ? 'Link copied' : 'Share link'}
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

            <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,18rem),1fr))] items-stretch gap-4">
                <div
                    data-testid="axis-breakdown"
                    className="voxel-trough flex h-full min-w-0 flex-col justify-between gap-4 rounded-none p-4"
                >
                    <h3 className="text-sm font-bold text-voxel-ink">4-Axis Diagnostic Profile</h3>
                    {AXIS_DEFINITIONS.map((axis) => {
                        const score = result.profile[axis.id];
                        return (
                            <div key={axis.id} className="flex min-w-0 flex-col gap-2">
                                <div className="flex min-w-0 flex-wrap items-baseline justify-between gap-x-2 gap-y-1 text-xs font-normal">
                                    <span className="min-w-0 whitespace-nowrap text-voxel-ink">
                                        {axis.label}
                                    </span>
                                    <span className="min-w-0 whitespace-nowrap text-accent">
                                        {`${score}/100`}
                                    </span>
                                </div>
                                <div className="h-2 w-full overflow-hidden rounded-none border-2 border-voxel-bevel-lo bg-voxel-surface">
                                    <div
                                        className="h-full bg-accent"
                                        style={{ width: `${score}%` }}
                                    />
                                </div>
                                <div className="flex min-w-0 flex-wrap items-baseline justify-between gap-x-2 gap-y-1 text-xs font-normal text-voxel-muted">
                                    <span className="min-w-0 whitespace-nowrap">
                                        {axis.lowLabel}
                                    </span>
                                    <span className="min-w-0 whitespace-nowrap">
                                        {axis.highLabel}
                                    </span>
                                </div>
                            </div>
                        );
                    })}
                </div>

                <div className="voxel-trough flex h-full min-w-0 flex-col justify-between gap-4 rounded-none p-4">
                    <div className="flex flex-col gap-2">
                        <h3 className="text-sm font-bold text-voxel-ink">Edge &amp; Blind Spot</h3>
                        <ul className="flex flex-col gap-2 text-xs font-normal text-voxel-ink">
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

            <div className="flex flex-col gap-4">
                <h3 className="text-sm font-bold text-voxel-ink">
                    Your Top-2 Matched Trading Bots
                </h3>
                <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,19rem),1fr))] items-stretch gap-4">
                    <BotRecommendationCard match={result.primary} rankLabel="#1 Best Bot Match" />
                    <BotRecommendationCard match={result.runnerUp} rankLabel="#2 Runner-Up Match" />
                </div>
            </div>
        </div>
    );
}
