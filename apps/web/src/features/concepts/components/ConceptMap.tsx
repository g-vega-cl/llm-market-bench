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

export interface ConceptCatalyst {
    catalyst_id: string;
    catalyst_title: string;
    target_date: string;
    days_to_event: number;
    stage: 'upcoming' | 'active' | 'digesting';
    date_offset_label: string;
    impact: string;
    similarity: number;
    memory_content?: string;
    related_tickers?: string[];
}

export type Concept = {
    id: string;
    concept_name: string;
    pca_x: number | null;
    pca_y: number | null;
    mention_count: number;
    velocity_score: number;
    first_mention_at: string;
    last_mention_at: string;
    concept_vector?: number[] | string | null;
    catalyst?: ConceptCatalyst | null;
};

type TabType = 'trending' | 'volume' | 'newest' | 'keep-an-eye';

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

    const catalystCount = useMemo(() => {
        return (data || []).filter((c) => c.catalyst != null).length;
    }, [data]);

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

        let baseList = data;
        if (activeTab === 'keep-an-eye') {
            baseList = data.filter((c) => c.catalyst != null);
        }

        // 1. Filter by search query
        const filtered = baseList.filter((c) => {
            const matchesName = c.concept_name.toLowerCase().includes(searchQuery.toLowerCase());
            const matchesCatalyst = c.catalyst?.catalyst_title
                ?.toLowerCase()
                .includes(searchQuery.toLowerCase());
            return matchesName || matchesCatalyst;
        });

        // 2. Sort based on active tab
        return [...filtered].sort((a, b) => {
            if (activeTab === 'keep-an-eye') {
                const daysA = a.catalyst ? Math.abs(a.catalyst.days_to_event) : 999;
                const daysB = b.catalyst ? Math.abs(b.catalyst.days_to_event) : 999;
                if (daysA !== daysB) return daysA - daysB;
                return (b.velocity_score || 0) - (a.velocity_score || 0);
            }
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

    const getStageBadge = (stage: 'upcoming' | 'active' | 'digesting') => {
        if (stage === 'active') {
            return (
                <Badge colorScheme="danger" variant="soft" size="sm" showDot>
                    Today
                </Badge>
            );
        }
        if (stage === 'upcoming') {
            return (
                <Badge colorScheme="info" variant="soft" size="sm" showDot>
                    Upcoming
                </Badge>
            );
        }
        return (
            <Badge colorScheme="warning" variant="soft" size="sm" showDot>
                Digesting
            </Badge>
        );
    };

    const getImpactBadge = (impact: string) => {
        const imp = impact.toUpperCase();
        if (imp.includes('BULLISH')) {
            return (
                <Badge colorScheme="success" variant="soft" size="sm">
                    {impact}
                </Badge>
            );
        }
        if (imp.includes('BEARISH')) {
            return (
                <Badge colorScheme="danger" variant="soft" size="sm">
                    {impact}
                </Badge>
            );
        }
        return (
            <Badge colorScheme="neutral" variant="soft" size="sm">
                {impact}
            </Badge>
        );
    };

    return (
        <div className="space-y-6 w-full max-w-full overflow-hidden">
            {/* Controls Header */}
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                {/* Tabs - Scrollable on mobile */}
                <div className="w-full sm:w-auto overflow-x-auto max-w-full whitespace-nowrap scrollbar-none pb-1 sm:pb-0">
                    <div className="inline-flex gap-2 bg-voxel-trough p-1.5 rounded-none border border-voxel-bevel-hi">
                        <Button
                            variant={activeTab === 'trending' ? 'solid' : 'outline'}
                            colorScheme={activeTab === 'trending' ? 'accent' : 'neutral'}
                            size="sm"
                            onClick={() => handleTabChange('trending')}
                        >
                            Trending 🔥
                        </Button>
                        <Button
                            variant={activeTab === 'volume' ? 'solid' : 'outline'}
                            colorScheme={activeTab === 'volume' ? 'accent' : 'neutral'}
                            size="sm"
                            onClick={() => handleTabChange('volume')}
                        >
                            Most Mentioned 📊
                        </Button>
                        <Button
                            variant={activeTab === 'newest' ? 'solid' : 'outline'}
                            colorScheme={activeTab === 'newest' ? 'accent' : 'neutral'}
                            size="sm"
                            onClick={() => handleTabChange('newest')}
                        >
                            Newest ⏱️
                        </Button>
                        <Button
                            variant={activeTab === 'keep-an-eye' ? 'solid' : 'outline'}
                            colorScheme={activeTab === 'keep-an-eye' ? 'accent' : 'neutral'}
                            size="sm"
                            onClick={() => handleTabChange('keep-an-eye')}
                        >
                            ⚡ Keep an Eye {catalystCount > 0 ? `(${catalystCount})` : ''}
                        </Button>
                    </div>
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

            {/* Mobile Concepts Card List (< md breakpoint) */}
            <div className="block md:hidden flex flex-col gap-3 w-full max-w-full">
                {processedConcepts.map((concept) => {
                    const isExpanded = expandedId === concept.id;
                    return (
                        <div
                            key={concept.id}
                            className="bg-voxel-surface border border-voxel-bevel-hi rounded-none p-4 shadow-sm flex flex-col gap-3 min-w-0 max-w-full"
                            data-testid={`mobile-concept-card-${concept.id}`}
                        >
                            <Button
                                type="button"
                                variant="outline"
                                colorScheme="neutral"
                                size="sm"
                                className="w-full text-left flex items-center justify-between gap-2 select-none"
                                onClick={() => handleRowClick(concept)}
                            >
                                <div className="flex items-center gap-2 font-bold text-sm text-voxel-ink min-w-0 flex-1 truncate">
                                    <span
                                        className={`transition-transform duration-200 flex-shrink-0 ${
                                            isExpanded ? 'rotate-90' : ''
                                        }`}
                                    >
                                        <svg
                                            className="w-4 h-4 text-zinc-400"
                                            fill="none"
                                            viewBox="0 0 24 24"
                                            stroke="currentColor"
                                            aria-hidden="true"
                                        >
                                            <path
                                                strokeLinecap="round"
                                                strokeLinejoin="round"
                                                strokeWidth={2}
                                                d="M9 5l7 7-7 7"
                                            />
                                        </svg>
                                    </span>
                                    <span className="truncate">{concept.concept_name}</span>
                                </div>
                                <div className="flex-shrink-0">
                                    {getVelocityBadge(concept.velocity_score)}
                                </div>
                            </Button>

                            {concept.catalyst ? (
                                <div className="flex flex-col gap-1.5 pt-2 border-t border-voxel-bevel-lo text-xs font-normal">
                                    <div className="font-bold text-sm text-voxel-ink flex items-center justify-between gap-2">
                                        <span className="truncate">
                                            {concept.catalyst.catalyst_title}
                                        </span>
                                        {getStageBadge(concept.catalyst.stage)}
                                    </div>
                                    <div className="flex items-center justify-between text-voxel-muted font-mono text-xs font-normal">
                                        <span>
                                            {concept.catalyst.target_date} (
                                            {concept.catalyst.date_offset_label})
                                        </span>
                                        {getImpactBadge(concept.catalyst.impact)}
                                    </div>
                                </div>
                            ) : (
                                <div className="flex items-center justify-between text-xs font-normal text-voxel-muted pt-2 border-t border-voxel-bevel-lo font-mono">
                                    <div>
                                        <span>Mentions: </span>
                                        <span className="font-bold text-voxel-ink">
                                            {concept.mention_count}
                                        </span>
                                    </div>
                                    <div>
                                        <span>Velocity: </span>
                                        <span className="font-bold text-voxel-ink">
                                            {concept.velocity_score.toFixed(2)}
                                        </span>
                                    </div>
                                </div>
                            )}

                            {isExpanded && (
                                <div className="pt-2 border-t border-voxel-bevel-lo min-w-0">
                                    <ConceptDetails
                                        concept={concept}
                                        fetchMemoriesFn={fetchMemoriesFn}
                                        formatDate={formatDate}
                                        getDurationDays={getDurationDays}
                                        getStageBadge={getStageBadge}
                                        getImpactBadge={getImpactBadge}
                                    />
                                </div>
                            )}
                        </div>
                    );
                })}
                {processedConcepts.length === 0 && (
                    <div className="py-12 text-center text-xs font-normal text-voxel-muted bg-voxel-surface border border-voxel-bevel-hi rounded-none">
                        No concepts found matching your filters.
                    </div>
                )}
            </div>

            {/* Desktop Concepts Table (>= md breakpoint) */}
            <div className="hidden md:block w-full max-w-full">
                <Table>
                    <TableHeader>
                        {activeTab === 'keep-an-eye' ? (
                            <TableRow isHoverable={false}>
                                <TableHead>Concept Name</TableHead>
                                <TableHead>Catalyst Event</TableHead>
                                <TableHead align="right">Target Date</TableHead>
                                <TableHead align="center">Stage</TableHead>
                                <TableHead align="center">Impact</TableHead>
                            </TableRow>
                        ) : (
                            <TableRow isHoverable={false}>
                                <TableHead>Concept Name</TableHead>
                                <TableHead align="right">Mentions</TableHead>
                                <TableHead align="right">Momentum Velocity</TableHead>
                                <TableHead align="center">Status</TableHead>
                            </TableRow>
                        )}
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
                                        <TableCell>
                                            <div className="flex items-center gap-2">
                                                <span
                                                    className={`transition-transform duration-200 ${
                                                        isExpanded ? 'rotate-90' : ''
                                                    }`}
                                                >
                                                    <svg
                                                        className="w-4 h-4 text-voxel-muted group-hover:text-voxel-ink"
                                                        fill="none"
                                                        viewBox="0 0 24 24"
                                                        stroke="currentColor"
                                                        aria-hidden="true"
                                                    >
                                                        <path
                                                            strokeLinecap="round"
                                                            strokeLinejoin="round"
                                                            strokeWidth={2}
                                                            d="M9 5l7 7-7 7"
                                                        />
                                                    </svg>
                                                </span>
                                                <span>{concept.concept_name}</span>
                                            </div>
                                        </TableCell>

                                        {activeTab === 'keep-an-eye' && concept.catalyst ? (
                                            <>
                                                <TableCell>
                                                    {concept.catalyst.catalyst_title}
                                                </TableCell>
                                                <TableCell align="right">
                                                    {concept.catalyst.target_date} (
                                                    {concept.catalyst.date_offset_label})
                                                </TableCell>
                                                <TableCell align="center">
                                                    {getStageBadge(concept.catalyst.stage)}
                                                </TableCell>
                                                <TableCell align="center">
                                                    {getImpactBadge(concept.catalyst.impact)}
                                                </TableCell>
                                            </>
                                        ) : (
                                            <>
                                                <TableCell align="right">
                                                    {concept.mention_count}
                                                </TableCell>
                                                <TableCell align="right">
                                                    {concept.velocity_score.toFixed(2)}
                                                </TableCell>
                                                <TableCell align="center">
                                                    {getVelocityBadge(concept.velocity_score)}
                                                </TableCell>
                                            </>
                                        )}
                                    </TableRow>

                                    {isExpanded && (
                                        <TableRow isHoverable={false} className="bg-voxel-trough">
                                            <TableCell
                                                colSpan={activeTab === 'keep-an-eye' ? 5 : 4}
                                                className="py-4"
                                            >
                                                <ConceptDetails
                                                    concept={concept}
                                                    fetchMemoriesFn={fetchMemoriesFn}
                                                    formatDate={formatDate}
                                                    getDurationDays={getDurationDays}
                                                    getStageBadge={getStageBadge}
                                                    getImpactBadge={getImpactBadge}
                                                />
                                            </TableCell>
                                        </TableRow>
                                    )}
                                </React.Fragment>
                            );
                        })}
                        {processedConcepts.length === 0 && (
                            <TableRow isHoverable={false}>
                                <TableCell
                                    colSpan={activeTab === 'keep-an-eye' ? 5 : 4}
                                    align="center"
                                    tone="muted"
                                    className="py-12"
                                >
                                    No concepts found matching your filters.
                                </TableCell>
                            </TableRow>
                        )}
                    </TableBody>
                </Table>
            </div>
        </div>
    );
}

interface ConceptDetailsProps {
    concept: Concept;
    fetchMemoriesFn: (conceptId: string) => Promise<ConceptMemory[]>;
    formatDate: (dateStr: string | null) => string;
    getDurationDays: (first: string | null, last: string | null) => number;
    getStageBadge: (stage: 'upcoming' | 'active' | 'digesting') => React.ReactNode;
    getImpactBadge: (impact: string) => React.ReactNode;
}

function ConceptDetails({
    concept,
    fetchMemoriesFn,
    formatDate,
    getDurationDays,
    getStageBadge,
    getImpactBadge,
}: ConceptDetailsProps) {
    const {
        data: memories,
        isLoading,
        error,
    } = useQuery({
        ...conceptsQueries.memories(concept.id, () => fetchMemoriesFn(concept.id)),
    });

    return (
        <div className="flex flex-col gap-6 bg-voxel-surface border border-voxel-bevel-hi rounded-none p-4 shadow-sm animate-fade-in min-w-0 max-w-full overflow-hidden">
            {/* Catalyst Radar Box if linked catalyst exists */}
            {concept.catalyst && (
                <div className="p-3.5 bg-amber-500/10 border border-amber-500/30 rounded-none flex flex-col gap-2">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                        <span className="text-sm font-bold text-accent flex items-center gap-1.5">
                            ⚡ Catalyst Radar: {concept.catalyst.catalyst_title}
                        </span>
                        <div className="flex items-center gap-2">
                            {getStageBadge(concept.catalyst.stage)}
                            {getImpactBadge(concept.catalyst.impact)}
                        </div>
                    </div>
                    <div className="flex flex-wrap items-center gap-4 text-xs font-normal text-voxel-muted font-mono">
                        <div>
                            <span className="font-bold text-voxel-muted">Target Date:</span>{' '}
                            {concept.catalyst.target_date} ({concept.catalyst.date_offset_label})
                        </div>
                        <div>
                            <span className="font-bold text-voxel-muted">Relevance:</span>{' '}
                            {Math.round(concept.catalyst.similarity * 100)}% Match
                        </div>
                        {concept.catalyst.related_tickers &&
                            concept.catalyst.related_tickers.length > 0 && (
                                <div>
                                    <span className="font-bold text-voxel-muted">Tickers:</span>{' '}
                                    {concept.catalyst.related_tickers.join(', ')}
                                </div>
                            )}
                    </div>
                    {concept.catalyst.memory_content && (
                        <p className="text-xs font-normal text-voxel-ink pt-1.5 border-t border-amber-500/20 m-0">
                            {concept.catalyst.memory_content}
                        </p>
                    )}
                </div>
            )}
            {/* Top row: Metrics */}
            <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,14rem),1fr))] gap-4 sm:gap-6 pb-4 border-b border-voxel-bevel-lo items-stretch">
                <div className="flex flex-col gap-1">
                    <span className="text-sm font-bold text-voxel-muted uppercase tracking-wider block">
                        Timeline Activity
                    </span>
                    <div className="text-xs font-normal text-voxel-ink">
                        <span className="font-bold text-voxel-muted">First Seen:</span>{' '}
                        {formatDate(concept.first_mention_at)}
                    </div>
                    <div className="text-xs font-normal text-voxel-ink">
                        <span className="font-bold text-voxel-muted">Last Seen:</span>{' '}
                        {formatDate(concept.last_mention_at)}
                    </div>
                </div>

                <div className="flex flex-col gap-1">
                    <span className="text-sm font-bold text-voxel-muted uppercase tracking-wider block">
                        Lifespan Duration
                    </span>
                    <div className="text-xs font-normal text-voxel-ink">
                        <span className="font-bold text-voxel-muted">Duration Active:</span>{' '}
                        {getDurationDays(concept.first_mention_at, concept.last_mention_at)} days
                    </div>
                </div>

                <div className="flex flex-col gap-1">
                    <span className="text-sm font-bold text-voxel-muted uppercase tracking-wider block">
                        Semantic Coordinates
                    </span>
                    <div className="text-xs font-normal text-voxel-muted font-mono">
                        X: {concept.pca_x?.toFixed(4) ?? 'N/A'}, Y:{' '}
                        {concept.pca_y?.toFixed(4) ?? 'N/A'}
                    </div>
                </div>
            </div>

            {/* Bottom Section: Related Memories */}
            <div className="flex flex-col gap-3 pt-2">
                <span className="text-sm font-bold text-zinc-400 uppercase tracking-wider block">
                    Sources & Related Memories
                </span>

                {isLoading && (
                    <div className="py-4 text-center text-xs font-normal text-voxel-muted animate-pulse">
                        Loading related memories...
                    </div>
                )}

                {error && (
                    <div className="py-4 text-center text-xs font-normal text-danger">
                        Failed to load related memories.
                    </div>
                )}

                {!isLoading && !error && (!memories || memories.length === 0) && (
                    <div className="py-4 text-center text-xs font-normal text-voxel-muted">
                        No related memories found.
                    </div>
                )}

                {!isLoading && !error && memories && memories.length > 0 && (
                    <div className="flex flex-col gap-3">
                        {memories.map((memory) => {
                            const matchPercentage = Math.round(memory.similarity * 100);
                            const impact = memory.metadata?.impact;

                            return (
                                <div
                                    key={memory.id}
                                    className="p-3 bg-voxel-trough border border-voxel-bevel-hi rounded-none flex flex-col md:flex-row md:items-start justify-between gap-4 transition-all hover:bg-voxel-elevated min-w-0 max-w-full"
                                >
                                    <div className="flex flex-col gap-1.5 flex-1 min-w-0">
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
                                                <span className="text-xs font-normal text-zinc-400 font-mono">
                                                    {formatDate(memory.created_at)}
                                                </span>
                                            )}
                                        </div>
                                        <p className="text-xs font-normal text-voxel-ink leading-relaxed break-words m-0">
                                            {memory.content}
                                        </p>
                                    </div>
                                    <div className="flex items-center self-end md:self-start flex-shrink-0">
                                        <Link
                                            to="/memories/chain/$memoryId"
                                            params={{ memoryId: memory.id }}
                                            className="text-sm text-accent hover:text-accent/80 font-bold flex items-center gap-1 transition-colors"
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
