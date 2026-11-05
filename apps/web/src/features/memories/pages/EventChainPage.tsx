import {
    Badge,
    Button,
    Card,
    LoadingSpinner,
    PageLayout,
    SectionHeading,
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
        initialDataUpdatedAt: 0,
    });

    const { chain, targetMemory } = data;

    if (!targetMemory) {
        return (
            <div className="min-h-screen">
                <PageLayout maxWidth="md">
                    <div className="text-center py-12 flex flex-col items-center gap-4">
                        <p className="text-zinc-500 text-xs font-normal">Event not found</p>
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
            <div className="border-b border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950">
                <PageLayout maxWidth="md" className="py-6 flex flex-col gap-4">
                    <div className="flex items-center gap-3">
                        <Link
                            to="/memories"
                            className="p-1.5 rounded-none hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
                        >
                            <svg
                                className="w-4 h-4 text-zinc-500"
                                fill="none"
                                stroke="currentColor"
                                viewBox="0 0 24 24"
                            >
                                <title>Back to Memories</title>
                                <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    strokeWidth={2}
                                    d="M15 19l-7-7 7-7"
                                />
                            </svg>
                        </Link>
                        <SectionHeading gradient="electric">
                            Thought Journey & Event Chain
                        </SectionHeading>
                    </div>
                    <div className="flex flex-wrap items-center justify-between gap-3">
                        <p className="text-zinc-600 dark:text-zinc-400 text-xs font-normal m-0">
                            Tracing how this catalyst evolved through model reasoning, debate
                            stress-tests, and market resolutions.
                        </p>
                        {isFetching && (
                            <span className="inline-flex items-center gap-1.5 text-xs text-amber-500 font-bold bg-amber-50/50 dark:bg-amber-950/20 px-2 py-0.5 rounded-none border border-amber-200/50 dark:border-amber-900/30">
                                <LoadingSpinner size="sm" className="text-amber-500" />
                                Loading chain...
                            </span>
                        )}
                    </div>
                </PageLayout>
            </div>

            {/* Main Content Area */}
            <PageLayout maxWidth="md" className="py-8 flex flex-col gap-6">
                {/* Chain Switcher Bar */}
                <Card variant="glass" padding="sm">
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
                                        <div className="w-px h-6 bg-zinc-300 dark:bg-zinc-700" />
                                        <div className="flex items-center gap-2 px-3 py-1 bg-zinc-100 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-none shadow-sm z-10">
                                            <span className="text-xs font-bold text-zinc-400">
                                                ↓
                                            </span>
                                            <Badge
                                                size="xs"
                                                variant="solid"
                                                radius="none"
                                                colorScheme={getRelationshipColor(
                                                    memory.relationship_type,
                                                )}
                                            >
                                                {memory.relationship_type || 'UPDATE'}
                                            </Badge>
                                            <span className="text-xs font-mono text-zinc-500 dark:text-zinc-400">
                                                {memory.elapsedFromPreceding || '+later'}
                                            </span>
                                        </div>
                                        <div className="w-px h-6 bg-zinc-300 dark:bg-zinc-700" />
                                    </div>
                                )}

                                {/* Step Card */}
                                <div
                                    id={memory.id}
                                    className={`relative border rounded-none p-5 transition-all shadow-sm ${
                                        isSelected
                                            ? 'border-zinc-900 dark:border-zinc-100 bg-zinc-50 dark:bg-zinc-900/90 ring-1 ring-zinc-900/10 dark:ring-zinc-100/20'
                                            : 'border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 hover:border-zinc-300 dark:hover:border-zinc-700'
                                    }`}
                                >
                                    {/* Top Metadata Header */}
                                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-zinc-100 dark:border-zinc-800/80">
                                        <div className="flex items-center gap-2 flex-wrap">
                                            <span className="px-2 py-0.5 bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 text-xs font-bold font-mono uppercase">
                                                {isRoot
                                                    ? 'STEP 1 • CATALYST ORIGIN'
                                                    : isFinal
                                                      ? `STEP ${index + 1} • RESOLUTION`
                                                      : `STEP ${index + 1}`}
                                            </span>

                                            <Badge
                                                variant="soft"
                                                size="xs"
                                                radius="none"
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
                                                    radius="none"
                                                >
                                                    ${memory.metadata.ticker}
                                                </Badge>
                                            )}

                                            {memory.metadata?.impact && (
                                                <Badge
                                                    variant="soft"
                                                    size="xs"
                                                    radius="none"
                                                    colorScheme={getImpactBadgeColor(
                                                        memory.metadata.impact,
                                                    )}
                                                >
                                                    {memory.metadata.impact}
                                                </Badge>
                                            )}

                                            {memory.importance_score && (
                                                <span className="text-xs font-mono font-bold text-amber-500">
                                                    ★ {memory.importance_score}/10
                                                </span>
                                            )}
                                        </div>

                                        <div className="flex items-center gap-2 flex-wrap">
                                            <span className="text-xs text-zinc-500 font-mono">
                                                {memory.formattedDate || 'Pending'}
                                            </span>
                                            {memory.elapsedFromRoot && !isRoot && (
                                                <span className="text-xs font-bold font-mono text-emerald-600 dark:text-emerald-400">
                                                    ({memory.elapsedFromRoot})
                                                </span>
                                            )}
                                        </div>
                                    </div>

                                    {/* Selected Focus Banner */}
                                    {isSelected && (
                                        <div className="mt-3 p-2 bg-emerald-500/10 border-l-2 border-emerald-500 text-xs font-bold text-emerald-700 dark:text-emerald-300">
                                            ← You selected this event
                                        </div>
                                    )}

                                    {/* Memory Content Text */}
                                    <p className="mt-4 text-xs font-normal text-zinc-800 dark:text-zinc-200 leading-relaxed font-sans">
                                        {memory.content}
                                    </p>

                                    {/* The Model Process Section */}
                                    {(models.length > 0 || debate || scenarios.length > 0) && (
                                        <div className="mt-4 pt-3 border-t border-zinc-100 dark:border-zinc-800/80 flex flex-col gap-3">
                                            {/* Models Involved */}
                                            {models.length > 0 && (
                                                <div className="flex items-center gap-2 flex-wrap">
                                                    <span className="text-xs font-bold uppercase tracking-wider text-zinc-400">
                                                        Models Involved:
                                                    </span>
                                                    {models.map((modName, mIdx) => (
                                                        <Badge
                                                            key={mIdx}
                                                            variant="outline"
                                                            size="xs"
                                                            colorScheme="info"
                                                            radius="none"
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
                                                        <span className="text-xs font-bold text-amber-600 dark:text-amber-400 uppercase tracking-wide">
                                                            🛡️ Red-Team Stress-Test
                                                        </span>
                                                        {debate.adversary_model && (
                                                            <span className="text-xs font-mono text-zinc-400">
                                                                Challenger: {debate.adversary_model}
                                                            </span>
                                                        )}
                                                    </div>
                                                    {debate.counter_thesis && (
                                                        <p className="text-xs font-normal text-zinc-700 dark:text-zinc-300 leading-relaxed m-0">
                                                            <b>Counter-Thesis:</b>{' '}
                                                            {debate.counter_thesis}
                                                        </p>
                                                    )}
                                                    {debate.pre_mortem && (
                                                        <p className="text-xs font-normal text-rose-600 dark:text-rose-400 font-mono m-0">
                                                            <b>Pre-Mortem Failure Mode:</b>{' '}
                                                            {debate.pre_mortem}
                                                        </p>
                                                    )}
                                                    {Array.isArray(debate.key_risks) &&
                                                        debate.key_risks.length > 0 && (
                                                            <div className="flex flex-col gap-0.5">
                                                                <span className="text-xs font-bold text-zinc-400 uppercase">
                                                                    Key Risks:
                                                                </span>
                                                                <ul className="list-disc list-inside text-xs font-normal text-zinc-600 dark:text-zinc-400">
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
                                                    <span className="text-xs font-bold uppercase tracking-wider text-zinc-400">
                                                        Probability Scenarios:
                                                    </span>
                                                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                                                        {scenarios.map(
                                                            (sc: ChainScenario, sIdx: number) => (
                                                                <div
                                                                    key={sIdx}
                                                                    className="p-2.5 bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-none flex flex-col gap-1"
                                                                >
                                                                    <div className="flex items-center justify-between gap-2">
                                                                        <span className="text-xs font-bold text-zinc-900 dark:text-zinc-100">
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
                                                                        <p className="text-xs font-normal text-zinc-600 dark:text-zinc-400 line-clamp-2 m-0">
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
                        <div className="flex flex-col items-center py-6">
                            <div className="w-px h-8 bg-zinc-300 dark:bg-zinc-700" />
                            <div className="border border-dashed border-zinc-300 dark:border-zinc-700 rounded-none p-5 bg-zinc-50/50 dark:bg-zinc-900/30 w-full flex items-center gap-4">
                                <div className="flex-shrink-0 w-10 h-10 flex items-center justify-center bg-zinc-100 dark:bg-zinc-800 text-zinc-400">
                                    <LoadingSpinner size="sm" className="text-zinc-400" />
                                </div>
                                <div className="flex-1 flex flex-col gap-1">
                                    <p className="text-xs font-bold text-zinc-500 dark:text-zinc-400 m-0">
                                        Loading other memories in this chain...
                                    </p>
                                    <p className="text-xs font-normal text-zinc-400 dark:text-zinc-500 m-0">
                                        Retrieving preceding and succeeding events
                                    </p>
                                </div>
                            </div>
                        </div>
                    )}
                </div>

                {/* Bottom Action Footer */}
                <div className="mt-4 pt-6 border-t border-zinc-200 dark:border-zinc-800 flex flex-col sm:flex-row items-center justify-between gap-4">
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
