import {
    Badge,
    Button,
    Card,
    PageLayout,
    SectionHeading,
    Skeleton,
} from '@llm-market-bench/ui-design-system';
import { useSuspenseQuery } from '@tanstack/react-query';
import { Link } from '@tanstack/react-router';
import { searchMemories } from '~/features/memories/api/fetch-memories';
import { ChainMemorySwitcher } from '~/features/memories/components/ChainMemorySwitcher';
import { eventChainQueries } from '~/features/memories/queries/options';
import type { ChainMemory } from '~/features/memories/utils/build-chain';

interface EventChainData {
    chain: ChainMemory[];
    targetMemory: ChainMemory | null;
}

interface ChainScenario {
    header?: string;
    cleanHeader?: string;
    percentage?: string;
    outcome?: string;
}

interface EventChainPageProps {
    memoryId: string;
    initialData: EventChainData;
    fetchFn: () => Promise<EventChainData>;
}

function getTypeBadgeColor(type?: string | null): 'accent' | 'info' | 'warning' | 'neutral' {
    switch (type) {
        case 'MARKET_EVENT':
        case 'consensus_event':
            return 'accent';
        case 'decision_reasoning':
            return 'info';
        case 'POST_MORTEM':
        case 'post_mortem':
            return 'warning';
        default:
            return 'neutral';
    }
}

function getImpactBadgeColor(impact?: string | null): 'success' | 'danger' | 'neutral' {
    switch (impact) {
        case 'BULLISH':
            return 'success';
        case 'BEARISH':
            return 'danger';
        default:
            return 'neutral';
    }
}

function getRelationshipColor(
    rel?: string | null,
): 'accent' | 'warning' | 'success' | 'info' | 'neutral' {
    switch (rel) {
        case 'RESOLUTION':
            return 'success';
        case 'REVERSAL':
            return 'warning';
        case 'UPDATE':
            return 'info';
        default:
            return 'neutral';
    }
}

function formatType(type?: string | null): string {
    return (type || 'Memory').replace(/_/g, ' ');
}

export function EventChainPage({ memoryId, initialData, fetchFn }: EventChainPageProps) {
    const { data, isFetching } = useSuspenseQuery({
        ...eventChainQueries.detail({ id: memoryId, fetchFn }),
        initialData,
        initialDataUpdatedAt: initialData.chain.length > 1 ? undefined : 0,
    });

    const { chain, targetMemory } = data;

    if (!targetMemory) {
        return (
            <div className="min-h-screen">
                <PageLayout maxWidth="md">
                    <div className="text-center py-12 flex flex-col items-center gap-4">
                        <p className="text-voxel-muted text-xs font-normal">Event not found</p>
                        <Link to="/memories">
                            <Button variant="solid" colorScheme="neutral" size="sm">
                                Back to Memories
                            </Button>
                        </Link>
                    </div>
                </PageLayout>
            </div>
        );
    }

    const primaryTicker =
        targetMemory.metadata?.ticker ||
        chain.find((m) => m.metadata?.ticker)?.metadata?.ticker ||
        undefined;

    const chatInquiryText = `Analyze the thought chain for ${primaryTicker ? `$${primaryTicker}` : 'this event'}: Started with "${chain[0]?.content?.slice(0, 80) || ''}...", evolved through ${chain.length} events, leading to "${chain[chain.length - 1]?.content?.slice(0, 80) || ''}...". What critical risks and portfolio lessons apply?`;

    return (
        <div className="min-h-screen">
            {/* Header */}
            <div className="border-b border-voxel-bevel-hi bg-voxel-surface">
                <PageLayout
                    maxWidth="md"
                    className="px-6 md:px-12 py-6 flex flex-col gap-4"
                    withPadding={false}
                >
                    <div className="flex items-center gap-3">
                        <Link
                            to="/memories"
                            aria-label="Back to Memories"
                            className="p-1.5 rounded-none hover:bg-voxel-elevated transition-colors"
                        >
                            <svg
                                className="w-4 h-4 text-voxel-muted"
                                fill="none"
                                stroke="currentColor"
                                viewBox="0 0 24 24"
                                aria-hidden="true"
                            >
                                <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    strokeWidth={2}
                                    d="M15 19l-7-7 7-7"
                                />
                            </svg>
                        </Link>
                        <SectionHeading>Thought Journey & Event Chain</SectionHeading>
                    </div>
                    <div className="flex flex-wrap items-center justify-between gap-3">
                        <p className="text-voxel-muted text-xs font-normal m-0">
                            Tracing how this catalyst evolved through model reasoning, debate
                            stress-tests, and market resolutions.
                        </p>
                        {isFetching && (
                            <span className="inline-flex items-center gap-1.5 text-sm text-accent font-bold bg-voxel-trough px-2 py-0.5 rounded-none border border-voxel-bevel-hi">
                                <span
                                    aria-hidden="true"
                                    className="inline-block w-2 h-2 rounded-none bg-accent animate-pulse motion-reduce:animate-none"
                                />
                                Loading chain...
                            </span>
                        )}
                    </div>
                </PageLayout>
            </div>

            {/* Main Content Area */}
            <PageLayout maxWidth="md" className="flex flex-col gap-6">
                {/* Chain Switcher Bar */}
                <Card variant="default" padding="sm">
                    <ChainMemorySwitcher currentMemoryId={memoryId} searchFn={searchMemories} />
                </Card>

                {/* Timeline Thought Stream */}
                <div className="flex flex-col gap-0">
                    {chain.map((memory: ChainMemory, index: number) => {
                        const isSelected = memory.id === targetMemory.id;
                        const isRoot = memory.isRoot || index === 0;
                        const isFinal = index === chain.length - 1 && chain.length > 1;
                        const models = memory.modelsInvolved || [];
                        const debate = memory.metadata?.debate;
                        const scenarios = Array.isArray(memory.metadata?.scenarios)
                            ? memory.metadata.scenarios
                            : [];

                        return (
                            <div key={memory.id} className="flex flex-col">
                                {/* Directional Connector from Previous Step */}
                                {index > 0 && (
                                    <div className="flex flex-col items-center py-3 relative">
                                        <div className="w-px h-6 bg-voxel-bevel-hi" />
                                        <div className="flex items-center gap-2 px-3 py-1 bg-voxel-trough border border-voxel-bevel-hi rounded-none shadow-sm z-10">
                                            <span className="text-sm font-bold text-voxel-muted">
                                                ↓
                                            </span>
                                            <Badge
                                                size="xs"
                                                variant="solid"
                                                colorScheme={getRelationshipColor(
                                                    memory.relationship_type,
                                                )}
                                            >
                                                {memory.relationship_type || 'UPDATE'}
                                            </Badge>
                                            <span className="text-xs font-mono text-voxel-muted">
                                                {memory.elapsedFromPreceding || '+later'}
                                            </span>
                                        </div>
                                        <div className="w-px h-6 bg-voxel-bevel-hi" />
                                    </div>
                                )}

                                {/* Step Card */}
                                <div
                                    id={memory.id}
                                    className={`relative border rounded-none p-5 transition-all shadow-sm ${
                                        isSelected
                                            ? 'border-accent bg-voxel-elevated ring-1 ring-accent/30'
                                            : 'border-voxel-bevel-hi bg-voxel-surface hover:border-voxel-muted'
                                    }`}
                                >
                                    {/* Top Metadata Header */}
                                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-voxel-bevel-lo">
                                        <div className="flex items-center gap-2 flex-wrap">
                                            <span className="px-2 py-0.5 bg-accent text-voxel-trough text-sm font-bold font-mono uppercase">
                                                {isRoot
                                                    ? 'STEP 1 • CATALYST ORIGIN'
                                                    : isFinal
                                                      ? `STEP ${index + 1} • RESOLUTION`
                                                      : `STEP ${index + 1}`}
                                            </span>

                                            <Badge
                                                variant="soft"
                                                size="xs"
                                                colorScheme={getTypeBadgeColor(
                                                    memory.metadata?.type || memory.memory_type,
                                                )}
                                            >
                                                {formatType(
                                                    memory.metadata?.type || memory.memory_type,
                                                )}
                                            </Badge>

                                            {memory.metadata?.ticker && (
                                                <Badge
                                                    variant="soft"
                                                    size="xs"
                                                    colorScheme="accent"
                                                >
                                                    ${memory.metadata.ticker}
                                                </Badge>
                                            )}

                                            {memory.metadata?.impact && (
                                                <Badge
                                                    variant="soft"
                                                    size="xs"
                                                    colorScheme={getImpactBadgeColor(
                                                        memory.metadata.impact,
                                                    )}
                                                >
                                                    {memory.metadata.impact}
                                                </Badge>
                                            )}

                                            {memory.importance_score && (
                                                <span className="text-sm font-mono font-bold text-amber-500">
                                                    ★ {memory.importance_score}/10
                                                </span>
                                            )}
                                        </div>

                                        <div className="flex items-center gap-2 flex-wrap">
                                            <span className="text-xs text-voxel-muted font-mono">
                                                {memory.formattedDate || 'Pending'}
                                            </span>
                                            {memory.elapsedFromRoot && !isRoot && (
                                                <span className="text-sm font-bold font-mono text-success">
                                                    ({memory.elapsedFromRoot})
                                                </span>
                                            )}
                                        </div>
                                    </div>

                                    {/* Selected Focus Banner */}
                                    {isSelected && (
                                        <div className="mt-3 p-2 bg-emerald-500/10 border-l-2 border-emerald-500 text-sm font-bold text-success">
                                            ← You selected this event
                                        </div>
                                    )}

                                    {/* Memory Content Text */}
                                    <p className="mt-4 text-xs font-normal text-voxel-ink leading-relaxed font-sans">
                                        {memory.content}
                                    </p>

                                    {/* The Model Process Section */}
                                    {(models.length > 0 || debate || scenarios.length > 0) && (
                                        <div className="mt-4 pt-3 border-t border-voxel-bevel-lo flex flex-col gap-3">
                                            {/* Models Involved */}
                                            {models.length > 0 && (
                                                <div className="flex items-center gap-2 flex-wrap">
                                                    <span className="text-sm font-bold uppercase tracking-wider text-zinc-400">
                                                        Models Involved:
                                                    </span>
                                                    {models.map((modName, mIdx) => (
                                                        <Badge
                                                            key={mIdx}
                                                            variant="soft"
                                                            size="xs"
                                                            colorScheme="info"
                                                        >
                                                            🤖 {modName}
                                                        </Badge>
                                                    ))}
                                                </div>
                                            )}

                                            {/* Debate Stress-Test */}
                                            {debate && (
                                                <div className="p-3 bg-amber-500/5 border border-amber-500/20 rounded-none flex flex-col gap-2">
                                                    <div className="flex items-center justify-between gap-2 flex-wrap">
                                                        <span className="text-sm font-bold text-accent uppercase tracking-wide">
                                                            🛡️ Red-Team Stress-Test
                                                        </span>
                                                        {debate.adversary_model && (
                                                            <span className="text-xs font-mono text-voxel-muted">
                                                                Challenger: {debate.adversary_model}
                                                            </span>
                                                        )}
                                                    </div>
                                                    {debate.counter_thesis && (
                                                        <p className="text-xs font-normal text-voxel-ink leading-relaxed m-0">
                                                            <b>Counter-Thesis:</b>{' '}
                                                            {debate.counter_thesis}
                                                        </p>
                                                    )}
                                                    {debate.pre_mortem && (
                                                        <p className="text-xs font-normal text-danger font-mono m-0">
                                                            <b>Pre-Mortem Failure Mode:</b>{' '}
                                                            {debate.pre_mortem}
                                                        </p>
                                                    )}
                                                    {Array.isArray(debate.key_risks) &&
                                                        debate.key_risks.length > 0 && (
                                                            <div className="flex flex-col gap-0.5">
                                                                <span className="text-sm font-bold text-voxel-muted uppercase">
                                                                    Key Risks:
                                                                </span>
                                                                <ul className="list-disc list-inside text-xs font-normal text-voxel-muted">
                                                                    {debate.key_risks.map(
                                                                        (
                                                                            risk: string,
                                                                            rIdx: number,
                                                                        ) => (
                                                                            <li key={rIdx}>
                                                                                {risk}
                                                                            </li>
                                                                        ),
                                                                    )}
                                                                </ul>
                                                            </div>
                                                        )}
                                                </div>
                                            )}

                                            {/* Scenarios */}
                                            {scenarios.length > 0 && (
                                                <div className="flex flex-col gap-2">
                                                    <span className="text-sm font-bold uppercase tracking-wider text-zinc-400">
                                                        Probability Scenarios:
                                                    </span>
                                                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                                                        {scenarios.map(
                                                            (sc: ChainScenario, sIdx: number) => (
                                                                <div
                                                                    key={sIdx}
                                                                    className="p-2.5 bg-voxel-trough border border-voxel-bevel-hi rounded-none flex flex-col gap-1"
                                                                >
                                                                    <div className="flex items-center justify-between gap-2">
                                                                        <span className="text-sm font-bold text-voxel-ink">
                                                                            {sc.header ||
                                                                                sc.cleanHeader ||
                                                                                `Scenario ${sIdx + 1}`}
                                                                        </span>
                                                                        {sc.percentage && (
                                                                            <Badge
                                                                                size="xs"
                                                                                variant="solid"
                                                                                colorScheme="accent"
                                                                            >
                                                                                {sc.percentage}
                                                                            </Badge>
                                                                        )}
                                                                    </div>
                                                                    {sc.outcome && (
                                                                        <p className="text-xs font-normal text-voxel-muted line-clamp-2 m-0">
                                                                            {sc.outcome}
                                                                        </p>
                                                                    )}
                                                                </div>
                                                            ),
                                                        )}
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                    )}
                                </div>
                            </div>
                        );
                    })}

                    {/* Subsequent Loading Placeholder */}
                    {chain.length === 1 && isFetching && (
                        <div
                            role="status"
                            aria-busy="true"
                            aria-label="Loading other memories in this chain..."
                            className="flex flex-col items-center py-6 gap-2"
                        >
                            <div className="w-px h-8 bg-voxel-bevel-hi" />
                            <Skeleton variant="card" lines={2} className="w-full" />
                        </div>
                    )}
                </div>

                {/* Bottom Action Footer */}
                <div className="mt-4 pt-6 border-t border-zinc-200 border-zinc-800 flex flex-col sm:flex-row items-center justify-between gap-4">
                    <Link
                        to="/chat"
                        search={{
                            q: chatInquiryText,
                            ticker: primaryTicker,
                        }}
                    >
                        <Button variant="solid" colorScheme="accent" className="font-bold">
                            💬 Interrogate Chain in AI Chat →
                        </Button>
                    </Link>

                    <Link to="/memories">
                        <Button variant="outline" colorScheme="neutral">
                            Back to All Memories
                        </Button>
                    </Link>
                </div>
            </PageLayout>
        </div>
    );
}
