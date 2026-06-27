import {
    Badge,
    Button,
    Input,
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@llm-market-bench/ui-design-system';
import { usePostHog } from '@posthog/react';
import { useQuery } from '@tanstack/react-query';
import { Link } from '@tanstack/react-router';
import * as React from 'react';
import { useMemo, useState } from 'react';
import type { ConceptMemory } from '../api/fetch-concepts';
import { conceptsQueries } from '../queries/options';

export type Concept = {
    id: string;
    concept_name: string;
    pca_x: number | null;
    pca_y: number | null;
    mention_count: number;
    velocity_score: number;
    first_mention_at: string;
    last_mention_at: string;
};

type TabType = 'trending' | 'volume' | 'newest';

export function ConceptMap({
    data,
    fetchMemoriesFn,
}: {
    data: Concept[];
    fetchMemoriesFn: (conceptId: string) => Promise<ConceptMemory[]>;
}) {
    const posthog = usePostHog();
    const [activeTab, setActiveTab] = useState<TabType>('trending');
    const [searchQuery, setSearchQuery] = useState('');
    const [expandedId, setExpandedId] = useState<string | null>(null);

    // Track tab changes in PostHog
    const handleTabChange = (tab: TabType) => {
        setActiveTab(tab);
        posthog?.capture('concept_tab_changed', { tab });
    };

    // Track row expansions in PostHog
    const handleRowClick = (concept: Concept) => {
        const nextId = expandedId === concept.id ? null : concept.id;
        setExpandedId(nextId);
        if (nextId) {
            posthog?.capture('concept_row_expanded', {
                concept_name: concept.concept_name,
                mention_count: concept.mention_count,
                velocity_score: concept.velocity_score,
            });
        }
    };

    // Process concepts: Filter and Sort
    const processedConcepts = useMemo(() => {
        if (!data) return [];

        // 1. Filter by search query
        const filtered = data.filter((c) =>
            c.concept_name.toLowerCase().includes(searchQuery.toLowerCase()),
        );

        // 2. Sort based on active tab
        return [...filtered].sort((a, b) => {
            if (activeTab === 'trending') {
                return (b.velocity_score || 0) - (a.velocity_score || 0);
            }
            if (activeTab === 'volume') {
                return (b.mention_count || 0) - (a.mention_count || 0);
            }
            if (activeTab === 'newest') {
                const aTime = a.first_mention_at ? new Date(a.first_mention_at).getTime() : 0;
                const bTime = b.first_mention_at ? new Date(b.first_mention_at).getTime() : 0;
                return bTime - aTime;
            }
            return 0;
        });
    }, [data, activeTab, searchQuery]);

    // Format utility for Date
    const formatDate = (dateStr: string | null) => {
        if (!dateStr) return 'N/A';
        return new Date(dateStr).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            timeZone: 'UTC',
        });
    };

    // Calculate elapsed duration in days
    const getDurationDays = (first: string | null, last: string | null) => {
        if (!first || !last) return 0;
        const fTime = new Date(first).getTime();
        const lTime = new Date(last).getTime();
        const diffMs = Math.abs(lTime - fTime);
        const days = Math.ceil(diffMs / (1000 * 60 * 60 * 24));
        return Math.max(1, days);
    };

    // Categorize momentum to assign proper badge color scheme
    const getVelocityBadge = (score: number) => {
        if (score >= 3.0) {
            return (
                <Badge colorScheme="danger" variant="soft" size="sm" showDot>
                    Accelerating
                </Badge>
            );
        }
        if (score >= 1.0) {
            return (
                <Badge colorScheme="success" variant="soft" size="sm" showDot>
                    Stable
                </Badge>
            );
        }
        return (
            <Badge colorScheme="neutral" variant="soft" size="sm" showDot>
                Cooling
            </Badge>
        );
    };

    return (
        <div className="space-y-6 w-full">
            {/* Controls Header */}
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                {/* Tabs */}
                <div className="flex gap-2 bg-zinc-100 dark:bg-zinc-900 p-1.5 rounded-xl border border-zinc-200 dark:border-zinc-800">
                    <Button
                        variant={activeTab === 'trending' ? 'solid' : 'ghost'}
                        onClick={() => handleTabChange('trending')}
                        className="px-4 py-1.5 text-xs font-semibold rounded-lg transition-all"
                    >
                        Trending 🔥
                    </Button>
                    <Button
                        variant={activeTab === 'volume' ? 'solid' : 'ghost'}
                        onClick={() => handleTabChange('volume')}
                        className="px-4 py-1.5 text-xs font-semibold rounded-lg transition-all"
                    >
                        Most Mentioned 📊
                    </Button>
                    <Button
                        variant={activeTab === 'newest' ? 'solid' : 'ghost'}
                        onClick={() => handleTabChange('newest')}
                        className="px-4 py-1.5 text-xs font-semibold rounded-lg transition-all"
                    >
                        Newest ⏱️
                    </Button>
                </div>

                {/* Search */}
                <div className="w-full sm:w-72">
                    <Input
                        placeholder="Search concepts..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        leftAddon={
                            <svg
                                className="w-4 h-4 text-zinc-400"
                                fill="none"
                                viewBox="0 0 24 24"
                                stroke="currentColor"
                                aria-label="Search Icon"
                            >
                                <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    strokeWidth={2}
                                    d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                                />
                            </svg>
                        }
                    />
                </div>
            </div>

            {/* Concepts Table */}
            <Table>
                <TableHeader>
                    <TableRow isHoverable={false}>
                        <TableHead>Concept Name</TableHead>
                        <TableHead align="right">Mentions</TableHead>
                        <TableHead align="right">Momentum Velocity</TableHead>
                        <TableHead align="center">Status</TableHead>
                    </TableRow>
                </TableHeader>
                <TableBody>
                    {processedConcepts.map((concept) => {
                        const isExpanded = expandedId === concept.id;
                        return (
                            <React.Fragment key={concept.id}>
                                <TableRow
                                    className="cursor-pointer group select-none"
                                    onClick={() => handleRowClick(concept)}
                                >
                                    <TableCell className="font-bold text-zinc-900 dark:text-zinc-100">
                                        <div className="flex items-center gap-2">
                                            <span
                                                className={`transition-transform duration-200 ${
                                                    isExpanded ? 'rotate-90' : ''
                                                }`}
                                            >
                                                <svg
                                                    className="w-4 h-4 text-zinc-400 group-hover:text-zinc-600 dark:group-hover:text-zinc-200"
                                                    fill="none"
                                                    viewBox="0 0 24 24"
                                                    stroke="currentColor"
                                                >
                                                    <title>Arrow</title>
                                                    <path
                                                        strokeLinecap="round"
                                                        strokeLinejoin="round"
                                                        strokeWidth={2}
                                                        d="M9 5l7 7-7 7"
                                                    />
                                                </svg>
                                            </span>
                                            {concept.concept_name}
                                        </div>
                                    </TableCell>
                                    <TableCell
                                        align="right"
                                        className="text-zinc-700 dark:text-zinc-300 font-mono"
                                    >
                                        {concept.mention_count}
                                    </TableCell>
                                    <TableCell
                                        align="right"
                                        className="text-zinc-700 dark:text-zinc-300 font-mono"
                                    >
                                        {concept.velocity_score.toFixed(2)}
                                    </TableCell>
                                    <TableCell align="center">
                                        {getVelocityBadge(concept.velocity_score)}
                                    </TableCell>
                                </TableRow>

                                {isExpanded && (
                                    <TableRow
                                        isHoverable={false}
                                        className="bg-zinc-50/40 dark:bg-zinc-950/40"
                                    >
                                        <TableCell colSpan={4} className="px-6 py-4">
                                            <ConceptDetails
                                                concept={concept}
                                                fetchMemoriesFn={fetchMemoriesFn}
                                                formatDate={formatDate}
                                                getDurationDays={getDurationDays}
                                            />
                                        </TableCell>
                                    </TableRow>
                                )}
                            </React.Fragment>
                        );
                    })}
                    {processedConcepts.length === 0 && (
                        <TableRow isHoverable={false}>
                            <TableCell colSpan={4} className="py-12 text-center text-zinc-500">
                                No concepts found matching your filters.
                            </TableCell>
                        </TableRow>
                    )}
                </TableBody>
            </Table>
        </div>
    );
}

interface ConceptDetailsProps {
    concept: Concept;
    fetchMemoriesFn: (conceptId: string) => Promise<ConceptMemory[]>;
    formatDate: (dateStr: string | null) => string;
    getDurationDays: (first: string | null, last: string | null) => number;
}

function ConceptDetails({
    concept,
    fetchMemoriesFn,
    formatDate,
    getDurationDays,
}: ConceptDetailsProps) {
    const {
        data: memories,
        isLoading,
        error,
    } = useQuery({
        ...conceptsQueries.memories(concept.id, () => fetchMemoriesFn(concept.id)),
    });

    return (
        <div className="space-y-6 bg-white dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-xl p-4 shadow-sm animate-fade-in">
            {/* Top row: Metrics */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pb-4 border-b border-zinc-100 dark:border-zinc-900">
                <div className="space-y-1">
                    <span className="text-[10px] font-bold text-zinc-400 uppercase tracking-widest block">
                        Timeline Activity
                    </span>
                    <div className="text-sm text-zinc-700 dark:text-zinc-300">
                        <span className="font-semibold text-zinc-500">First Seen:</span>{' '}
                        {formatDate(concept.first_mention_at)}
                    </div>
                    <div className="text-sm text-zinc-700 dark:text-zinc-300">
                        <span className="font-semibold text-zinc-500">Last Seen:</span>{' '}
                        {formatDate(concept.last_mention_at)}
                    </div>
                </div>

                <div className="space-y-1">
                    <span className="text-[10px] font-bold text-zinc-400 uppercase tracking-widest block">
                        Lifespan Duration
                    </span>
                    <div className="text-sm text-zinc-700 dark:text-zinc-300">
                        <span className="font-semibold text-zinc-500">Duration Active:</span>{' '}
                        {getDurationDays(concept.first_mention_at, concept.last_mention_at)} days
                    </div>
                </div>

                <div className="space-y-1">
                    <span className="text-[10px] font-bold text-zinc-400 uppercase tracking-widest block">
                        Semantic Coordinates
                    </span>
                    <div className="text-sm text-zinc-700 dark:text-zinc-300 font-mono text-zinc-500">
                        X: {concept.pca_x?.toFixed(4) ?? 'N/A'}, Y:{' '}
                        {concept.pca_y?.toFixed(4) ?? 'N/A'}
                    </div>
                </div>
            </div>

            {/* Bottom Section: Related Memories */}
            <div className="space-y-3 pt-2">
                <span className="text-[10px] font-bold text-zinc-400 uppercase tracking-widest block">
                    Sources & Related Memories
                </span>

                {isLoading && (
                    <div className="py-4 text-center text-sm text-zinc-500 animate-pulse">
                        Loading related memories...
                    </div>
                )}

                {error && (
                    <div className="py-4 text-center text-sm text-red-500">
                        Failed to load related memories.
                    </div>
                )}

                {!isLoading && !error && (!memories || memories.length === 0) && (
                    <div className="py-4 text-center text-sm text-zinc-500">
                        No related memories found.
                    </div>
                )}

                {!isLoading && !error && memories && memories.length > 0 && (
                    <div className="space-y-3">
                        {memories.map((memory) => {
                            const matchPercentage = Math.round(memory.similarity * 100);
                            const impact = memory.metadata?.impact;

                            return (
                                <div
                                    key={memory.id}
                                    className="p-3 bg-zinc-50 dark:bg-zinc-900 border border-zinc-150 dark:border-zinc-800/60 rounded-lg flex flex-col md:flex-row md:items-start justify-between gap-4 transition-all hover:bg-zinc-100/60 dark:hover:bg-zinc-850"
                                >
                                    <div className="space-y-1.5 flex-1">
                                        <div className="flex items-center gap-2 flex-wrap">
                                            {impact && (
                                                <Badge
                                                    variant="soft"
                                                    colorScheme={
                                                        impact === 'BULLISH'
                                                            ? 'success'
                                                            : impact === 'BEARISH'
                                                              ? 'danger'
                                                              : 'neutral'
                                                    }
                                                    size="xs"
                                                >
                                                    {impact}
                                                </Badge>
                                            )}
                                            <Badge variant="soft" colorScheme="info" size="xs">
                                                {matchPercentage}% Match
                                            </Badge>
                                            {memory.created_at && (
                                                <span className="text-xs text-zinc-400 font-mono">
                                                    {formatDate(memory.created_at)}
                                                </span>
                                            )}
                                        </div>
                                        <p className="text-sm text-zinc-700 dark:text-zinc-300 leading-relaxed">
                                            {memory.content}
                                        </p>
                                    </div>
                                    <div className="flex items-center self-end md:self-start">
                                        <Link
                                            to="/memories/chain/$memoryId"
                                            params={{ memoryId: memory.id }}
                                            className="text-xs text-accent hover:text-accent/80 font-semibold flex items-center gap-1 transition-colors"
                                        >
                                            View Event Chain ↗
                                        </Link>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                )}
            </div>
        </div>
    );
}
