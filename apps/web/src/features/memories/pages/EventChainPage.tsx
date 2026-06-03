import { Badge, Button, PageLayout, SectionHeading } from '@llm-market-bench/ui-design-system';
import { useSuspenseQuery } from '@tanstack/react-query';
import { Link } from '@tanstack/react-router';
import { eventChainQueries } from '~/features/memories/queries/options';

interface ChainMemory {
    id: string;
    content: string;
    created_at: string | null;
    formattedDate?: string;
    // biome-ignore lint/suspicious/noExplicitAny: Intentional any for TanStack Start serialization
    metadata?: Record<string, any> | null;
}

interface EventChainData {
    chain: ChainMemory[];
    targetMemory: ChainMemory | null;
}

interface EventChainPageProps {
    memoryId: string;
    initialData: EventChainData;
    fetchFn: () => Promise<EventChainData>;
}

function getTypeBadgeColor(type: string): 'accent' | 'info' | 'warning' | 'neutral' {
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

function getImpactBadgeColor(impact: string): 'success' | 'danger' | 'neutral' {
    switch (impact) {
        case 'BULLISH':
            return 'success';
        case 'BEARISH':
            return 'danger';
        default:
            return 'neutral';
    }
}

function formatType(type: string): string {
    return (type || 'Memory').replace(/_/g, ' ');
}

export function EventChainPage({ memoryId, initialData, fetchFn }: EventChainPageProps) {
    const { data } = useSuspenseQuery({
        ...eventChainQueries.detail({ id: memoryId, fetchFn }),
        initialData,
    });

    const { chain, targetMemory } = data;

    if (!targetMemory) {
        return (
            <div className="min-h-screen">
                <PageLayout maxWidth="sm">
                    <div className="text-center py-12">
                        <p className="text-zinc-500 text-sm">Event not found</p>
                        <Link to="/memories" className="inline-block mt-4">
                            <Button variant="solid" colorScheme="neutral" size="sm">
                                Back to Memories
                            </Button>
                        </Link>
                    </div>
                </PageLayout>
            </div>
        );
    }

    return (
        <div className="min-h-screen">
            <div className="border-b border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950">
                <PageLayout maxWidth="sm" className="py-6">
                    <div className="flex items-center gap-3 mb-4">
                        <Link
                            to="/memories"
                            className="p-1.5 rounded hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
                        >
                            <svg
                                className="w-4 h-4 text-zinc-500"
                                fill="none"
                                stroke="currentColor"
                                viewBox="0 0 24 24"
                            >
                                <title>Back</title>
                                <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    strokeWidth={2}
                                    d="M15 19l-7-7 7-7"
                                />
                            </svg>
                        </Link>
                        <SectionHeading gradient="electric">Event Chain</SectionHeading>
                    </div>
                    <p className="text-zinc-600 dark:text-zinc-400 text-sm">
                        Chronological chain including the selected event
                    </p>
                </PageLayout>
            </div>

            <PageLayout maxWidth="sm" className="py-8">
                <div className="flex flex-col space-y-0">
                    {chain.map((memory: ChainMemory, index: number) => (
                        <div key={memory.id} className="relative">
                            {index < chain.length - 1 && (
                                <div className="absolute left-6 top-14 bottom-0 w-px bg-zinc-200 dark:bg-zinc-800" />
                            )}
                            <div
                                id={memory.id}
                                className={`relative border rounded-md p-5 mb-0 transition-colors ${
                                    memory.id === targetMemory.id
                                        ? 'border-zinc-900 dark:border-zinc-100 bg-zinc-50 dark:bg-zinc-800/50'
                                        : 'border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 hover:border-zinc-300 dark:hover:border-zinc-700'
                                }`}
                            >
                                <div className="flex items-start gap-4 mb-3">
                                    <div
                                        className={`flex-shrink-0 w-12 h-12 rounded-full flex items-center justify-center text-sm font-semibold ${
                                            memory.id === targetMemory.id
                                                ? 'bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900'
                                                : 'bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400'
                                        }`}
                                    >
                                        {index + 1}
                                    </div>
                                    <div className="flex-1 min-w-0 pt-1">
                                        <div className="flex flex-wrap items-center gap-2 mb-1">
                                            <Badge
                                                variant="soft"
                                                size="sm"
                                                colorScheme={getTypeBadgeColor(
                                                    memory.metadata?.type,
                                                )}
                                            >
                                                {formatType(memory.metadata?.type)}
                                            </Badge>
                                            <span className="text-xs text-zinc-400 font-mono">
                                                {memory.formattedDate || 'Pending'}
                                            </span>
                                        </div>
                                        {memory.id === targetMemory.id && (
                                            <span className="text-xs font-semibold text-zinc-900 dark:text-zinc-100">
                                                &larr; You selected this event
                                            </span>
                                        )}
                                    </div>
                                </div>
                                <p className="text-base text-zinc-800 dark:text-zinc-200 leading-relaxed pl-16">
                                    {memory.content}
                                </p>
                                {(memory.metadata?.ticker || memory.metadata?.impact) && (
                                    <div className="flex flex-wrap gap-2 mt-3 pl-16">
                                        {memory.metadata.ticker && (
                                            <Badge variant="soft" size="sm" colorScheme="accent">
                                                ${memory.metadata.ticker}
                                            </Badge>
                                        )}
                                        {memory.metadata.impact && (
                                            <Badge
                                                variant="soft"
                                                size="sm"
                                                colorScheme={getImpactBadgeColor(
                                                    memory.metadata.impact,
                                                )}
                                            >
                                                {memory.metadata.impact}
                                            </Badge>
                                        )}
                                    </div>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
                <div className="mt-8 flex justify-center">
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
