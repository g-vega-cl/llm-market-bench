import { Badge, Button, Card } from '@llm-market-bench/ui-design-system';
import { Link } from '@tanstack/react-router';
import { TypeCodeGrid } from '~/components/ui/TypeCodeGrid';
import {
    ARCHETYPES,
    type ArchetypeId,
    type ArchetypeMatch,
    AXIS_DEFINITIONS,
    formatRecipeExecutionSpec,
    type QuizScoreResult,
    summarizeRecipeCoreGate,
    TYPE_GRID,
} from './personality-data';

const ROW_HEADERS = ['LV', 'LN', 'QV', 'QN'] as const;
const COLUMN_HEADERS = ['FP', 'FR', 'MP', 'MR'] as const;

function newsWindowToken(match: ArchetypeMatch): string {
    const news = match.recipe.stages[0]?.blocks.find((block) => block.type === 'news');
    return news ? `News ${news.recency_hours}h` : 'News Off';
}

function BotRecommendationCard({
    match,
    rankLabel,
    selfDescription,
}: {
    match: ArchetypeMatch;
    rankLabel: string;
    selfDescription?: string;
}) {
    const coreGate = summarizeRecipeCoreGate(match.recipe);
    const executionSpec = formatRecipeExecutionSpec(match.recipe);
    const words = selfDescription?.trim() ?? '';
    // The visitor's own words ride along with the archetype prompt: never scored,
    // never changing the type, only enriching the builder seed.
    const buildIdea = words
        ? `${match.archetype.builderIdeaPrompt}\n\nIn their words: "${words}"`
        : match.archetype.builderIdeaPrompt;

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
                    {newsWindowToken(match)}
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
                    search={{ idea: buildIdea }}
                    className="voxel-btn inline-flex items-center justify-center bg-accent px-4 py-2 text-sm font-bold uppercase tracking-wider text-voxel-trough hover:bg-accent-hover"
                >
                    Build this bot
                </Link>
            </div>
        </Card>
    );
}

export interface PersonalityResultPanelProps {
    result: QuizScoreResult;
    /** Optional Act-4 free text; never scored, only appended to the build seed. */
    selfDescription?: string;
    copiedLink: boolean;
    canReturnToQuizMatch: boolean;
    onCopyShareUrl: (archetypeId: ArchetypeId) => void;
    onReturnToQuizMatch: () => void;
    onRetake: () => void;
    onInspectArchetype: (archetypeId: ArchetypeId) => void;
}

/**
 * Renders the matched type plaque (`personality-result`) with the 4x4 type grid
 * and canonical recipe summaries derived directly from
 * `packages/config/starter-recipes.json`, preserving zero nested `.voxel-card`.
 */
export function PersonalityResultPanel({
    result,
    selfDescription,
    copiedLink,
    canReturnToQuizMatch,
    onCopyShareUrl,
    onReturnToQuizMatch,
    onRetake,
    onInspectArchetype,
}: PersonalityResultPanelProps) {
    const primaryArch = result.primary.archetype;
    const neighbourCell = result.neighbour
        ? TYPE_GRID.find((cell) => cell.code === result.neighbour?.code)
        : undefined;
    const neighbourArch = neighbourCell?.archetypeId
        ? ARCHETYPES[neighbourCell.archetypeId]
        : undefined;
    const weakestAxis = result.neighbour
        ? AXIS_DEFINITIONS.find((axis) => axis.id === result.neighbour?.axis)
        : undefined;

    const cells = TYPE_GRID.map((cell) => ({
        code: cell.code,
        label: cell.archetypeId ? ARCHETYPES[cell.archetypeId].title : cell.code,
    }));

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
                    All 16 types — rows are horizon + signal, columns are stance + tempo:
                </p>
                <TypeCodeGrid
                    testId="type-code-grid"
                    cells={cells}
                    activeCode={result.code}
                    onSelect={(code) => {
                        const cell = TYPE_GRID.find((candidate) => candidate.code === code);
                        if (cell?.archetypeId) onInspectArchetype(cell.archetypeId);
                    }}
                    rowHeaders={ROW_HEADERS}
                    columnHeaders={COLUMN_HEADERS}
                    description={`${result.code} - ${primaryArch.title} - ${primaryArch.recipeName}`}
                />
            </div>

            <div className="flex flex-wrap items-start justify-between gap-4 border-b-2 border-voxel-bevel-hi pb-4">
                <div className="flex min-w-0 flex-1 basis-80 flex-col gap-2">
                    <div className="flex min-w-0 flex-wrap items-baseline gap-2">
                        <span
                            data-testid="archetype-code"
                            className="text-sm font-bold tracking-wider text-accent"
                        >
                            {result.code}
                        </span>
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
                    {selfDescription?.trim() ? (
                        <p
                            data-testid="your-words"
                            className="min-w-0 break-words border-l-2 border-voxel-bevel-hi bg-voxel-surface p-3 text-xs font-normal text-voxel-ink"
                        >
                            {`Your words: "${selfDescription.trim()}"`}
                        </p>
                    ) : null}
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
                        Retake 16Q quiz
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
                        const letter = result.letters.find((entry) => entry.axis === axis.id);
                        return (
                            <div key={axis.id} className="flex min-w-0 flex-col gap-2">
                                <div className="flex min-w-0 flex-wrap items-baseline justify-between gap-x-2 gap-y-1 text-xs font-normal">
                                    <span className="min-w-0 whitespace-nowrap text-voxel-ink">
                                        {`${letter?.letter ?? ''} - ${axis.label}`}
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
                <h3 className="text-sm font-bold text-voxel-ink">Your Matched Trading Bot</h3>
                <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,19rem),1fr))] items-stretch gap-4">
                    <BotRecommendationCard
                        match={result.primary}
                        rankLabel="Your best match"
                        selfDescription={selfDescription}
                    />
                </div>
            </div>

            {result.neighbour && neighbourArch ? (
                <div
                    data-testid="neighbour-type"
                    className="voxel-trough flex min-w-0 flex-col gap-2 rounded-none p-4"
                >
                    <div className="flex min-w-0 flex-wrap items-baseline justify-between gap-2">
                        <h3 className="text-sm font-bold text-voxel-ink">One letter away</h3>
                        <span className="min-w-0 whitespace-nowrap text-xs font-normal text-voxel-muted">
                            {`Weakest letter: ${result.neighbour.letter} on ${weakestAxis?.label ?? ''}`}
                        </span>
                    </div>
                    <p className="min-w-0 break-words text-xs font-normal text-voxel-muted">
                        {`Flip it and you are ${result.neighbour.code} - ${neighbourArch.title}.`}
                    </p>
                    <div className="flex flex-wrap gap-2">
                        <Button
                            type="button"
                            size="sm"
                            variant="outline"
                            colorScheme="neutral"
                            data-testid="inspect-neighbour"
                            onClick={() => onInspectArchetype(neighbourArch.id)}
                        >
                            {`Inspect ${result.neighbour.code}`}
                        </Button>
                        <Link
                            to="/build"
                            search={{ idea: neighbourArch.builderIdeaPrompt }}
                            className="voxel-btn inline-flex items-center justify-center border-2 border-voxel-bevel-hi px-4 py-2 text-sm font-bold text-voxel-ink hover:bg-voxel-elevated"
                        >
                            Build that bot
                        </Link>
                    </div>
                </div>
            ) : null}
        </div>
    );
}
