import type { Memory } from '@llm-market-bench/database';
import { Button } from '@llm-market-bench/ui-design-system';
import * as React from 'react';
import { MemoryCard } from './MemoryCard';
import { MemoryFlow } from './MemoryFlow';

export type { Memory };

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

interface MemoriesListProps {
    memories: Memory[];
    filter: string;
    onFilterChange: (filter: string) => void;
}

const FILTERS = [
    { id: 'all', label: 'All' },
    { id: 'MARKET_EVENT', label: 'Events' },
    { id: 'CALENDAR_EVENT', label: 'Calendar Events' },
    { id: 'POST_MORTEM', label: 'Post-Mortems' },
    { id: 'ACADEMIC_PAPER', label: 'Principles' },
];

export function MemoriesList({ memories, filter, onFilterChange }: MemoriesListProps) {
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
            <div className="sticky top-0 z-10 bg-white dark:bg-zinc-950 border-b border-zinc-200 dark:border-zinc-800 pb-4">
                <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                    {/* Filter Pills */}
                    <div className="flex flex-wrap gap-2">
                        {FILTERS.map((type) => (
                            <Button
                                key={type.id}
                                size="sm"
                                variant={filter === type.id ? 'solid' : 'soft'}
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
                        variant={showFlow ? 'solid' : 'outline'}
                        colorScheme="neutral"
                        onClick={() => setShowFlow(!showFlow)}
                    >
                        {showFlow ? 'Hide Flow' : 'Show Flow'}
                    </Button>
                </div>
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
