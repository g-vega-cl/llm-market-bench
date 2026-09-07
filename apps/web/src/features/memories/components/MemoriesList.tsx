import type { Memory } from '@llm-market-bench/database';
import { Button, Card, Select } from '@llm-market-bench/ui-design-system';
import * as React from 'react';
import { MemoryCard } from './MemoryCard';
import { MemoryFlow } from './MemoryFlow';

export type { Memory };

export type MemorySortOption = 'newest' | 'importance_desc' | 'importance_asc' | 'oldest';
export type DatePresetOption = 'all' | '7d' | '30d' | '90d';

// biome-ignore lint/suspicious/noExplicitAny: backward-compatible metadata check
function getFallbackCategory(content: string, meta: Record<string, any>): string | null {
    if (meta.type === 'decision_reasoning' || content.startsWith('DECISION REASONING:')) {
        return 'decision_reasoning';
    }
    if (meta.type === 'post_mortem' || meta.analysis_window || content.includes('POST-ANALYSIS')) {
        return 'POST_MORTEM';
    }
    if (
        meta.source_type === 'academic_paper' ||
        content.startsWith('EMPIRICAL ASSET PRICING PRINCIPLE:')
    ) {
        return 'ACADEMIC_PAPER';
    }
    if (meta.is_calendar_event || content.startsWith('[CALENDAR EVENT]')) {
        return 'CALENDAR_EVENT';
    }
    if (meta.type === 'consensus_event') {
        return 'MARKET_EVENT';
    }
    return null;
}

export function getMemoryCategory(m: Memory): string {
    const memType = m.memory_type || '';

    // Direct matches for unified types
    if (memType === 'MARKET_EVENT') return 'MARKET_EVENT';
    if (memType === 'CALENDAR_EVENT') return 'CALENDAR_EVENT';
    if (memType === 'POST_MORTEM') return 'POST_MORTEM';
    if (memType === 'ACADEMIC_PAPER') return 'ACADEMIC_PAPER';

    const fallback = getFallbackCategory(m.content || '', m.metadata || {});
    if (fallback) return fallback;

    if (memType === 'LESSON_LEARNED') return 'LESSON_LEARNED';
    return memType || 'other';
}

export interface MemoriesListProps {
    memories: Memory[];
    filter: string;
    onFilterChange: (filter: string) => void;
    sortBy?: MemorySortOption;
    onSortChange?: (sort: MemorySortOption) => void;
    datePreset?: DatePresetOption;
    onDatePresetChange?: (preset: DatePresetOption) => void;
    onlyHighImpact?: boolean;
    onHighImpactToggle?: () => void;
}

const FILTERS = [
    { id: 'all', label: 'All' },
    { id: 'MARKET_EVENT', label: 'Events' },
    { id: 'CALENDAR_EVENT', label: 'Calendar Events' },
    { id: 'POST_MORTEM', label: 'Post-Mortems' },
    { id: 'ACADEMIC_PAPER', label: 'Principles' },
    { id: 'RESOLVED', label: 'Resolved' },
];

const SORT_OPTIONS = [
    { value: 'newest', label: 'Newest First' },
    { value: 'importance_desc', label: 'Highest Importance' },
    { value: 'importance_asc', label: 'Lowest Importance' },
    { value: 'oldest', label: 'Oldest First' },
];

const DATE_PRESETS: { id: DatePresetOption; label: string }[] = [
    { id: 'all', label: 'All Time' },
    { id: '7d', label: '7D' },
    { id: '30d', label: '30D' },
    { id: '90d', label: '90D' },
];

export function MemoriesList({
    memories,
    filter,
    onFilterChange,
    sortBy = 'newest',
    onSortChange,
    datePreset = 'all',
    onDatePresetChange,
    onlyHighImpact = false,
    onHighImpactToggle,
}: MemoriesListProps) {
    const [showFlow, setShowFlow] = React.useState(false);

    const handleMemorySelect = (id: string) => {
        setShowFlow(false);
        const element = document.getElementById(id);
        if (element) {
            element.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    };

    return (
        <div className="flex flex-col space-y-6">
            {/* Control Bar */}
            <div className="sticky top-4 z-10 mb-6">
                <Card variant="glass" padding="sm" className="flex flex-col gap-3">
                    {/* Filter Pills & View Toggle */}
                    <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                        <div className="flex flex-wrap gap-2">
                            {FILTERS.map((type) => (
                                <Button
                                    key={type.id}
                                    size="sm"
                                    variant={filter === type.id ? 'solid' : 'ghost'}
                                    colorScheme="neutral"
                                    onClick={() => onFilterChange(type.id)}
                                >
                                    {type.label}
                                </Button>
                            ))}
                        </div>

                        {/* View Toggle */}
                        <Button
                            size="sm"
                            variant={showFlow ? 'solid' : 'ghost'}
                            colorScheme="neutral"
                            onClick={() => setShowFlow(!showFlow)}
                        >
                            {showFlow ? 'Hide Flow' : 'Show Flow'}
                        </Button>
                    </div>

                    {/* Controls Sub-Bar: Date Presets, High Impact, Sort Select */}
                    <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 pt-2 border-t border-zinc-200/50 dark:border-white/5">
                        {/* Date Presets */}
                        <div className="flex items-center gap-1.5 flex-wrap">
                            <span className="text-xs font-semibold uppercase tracking-wider text-zinc-400 dark:text-zinc-500 mr-1">
                                Date:
                            </span>
                            {DATE_PRESETS.map((dp) => (
                                <Button
                                    key={dp.id}
                                    size="sm"
                                    variant={datePreset === dp.id ? 'solid' : 'ghost'}
                                    colorScheme="neutral"
                                    onClick={() => onDatePresetChange?.(dp.id)}
                                >
                                    {dp.label}
                                </Button>
                            ))}
                        </div>

                        {/* Sort & Impact Controls */}
                        <div className="flex items-center gap-2 w-full sm:w-auto justify-between sm:justify-end">
                            <Button
                                size="sm"
                                variant={onlyHighImpact ? 'solid' : 'ghost'}
                                colorScheme={onlyHighImpact ? 'accent' : 'neutral'}
                                onClick={onHighImpactToggle}
                                title="Filter to memories with importance score 8 or higher"
                            >
                                8+ Impact 🔥
                            </Button>

                            <div className="w-44">
                                <Select
                                    aria-label="Sort by"
                                    value={sortBy}
                                    onChange={(e) =>
                                        onSortChange?.(e.target.value as MemorySortOption)
                                    }
                                    options={SORT_OPTIONS}
                                />
                            </div>
                        </div>
                    </div>
                </Card>
            </div>

            {/* Flow Visualization */}
            {showFlow && (
                <div className="w-full">
                    <MemoryFlow memories={memories} onSelect={handleMemorySelect} />
                </div>
            )}

            {/* Memory Cards */}
            <div className="flex flex-col space-y-4">
                {memories.map((memory) => (
                    <div key={memory.id}>
                        <MemoryCard memory={memory} />
                    </div>
                ))}

                {memories.length === 0 && (
                    <div className="flex justify-center items-center py-12">
                        <p className="text-zinc-500 text-sm">No memories found in this category</p>
                    </div>
                )}
            </div>
        </div>
    );
}
