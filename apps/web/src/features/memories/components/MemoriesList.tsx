import type { Memory } from '@llm-market-bench/database';
import { Button } from '@llm-market-bench/ui-design-system';
import * as React from 'react';
import { MemoryCard } from './MemoryCard';
import { MemoryFlow } from './MemoryFlow';

export type { Memory };
export function getMemoryCategory(m: Memory): string {
    const content = m.content || '';
    const meta = m.metadata || {};
    const memType = m.memory_type || '';

    if (meta.type === 'decision_reasoning' || content.startsWith('DECISION REASONING:')) {
        return 'decision_reasoning';
    }
    if (meta.type === 'post_mortem' || meta.analysis_window || content.includes('POST-ANALYSIS')) {
        return 'post_mortem';
    }
    if (
        meta.source_type === 'academic_paper' ||
        content.startsWith('EMPIRICAL ASSET PRICING PRINCIPLE:')
    ) {
        return 'academic_paper';
    }
    if (
        meta.is_calendar_event ||
        memType === 'CALENDAR_EVENT' ||
        content.startsWith('[CALENDAR EVENT]')
    ) {
        return 'calendar_event';
    }
    if (memType === 'LESSON_LEARNED') {
        return 'lesson_learned';
    }
    if (meta.type === 'consensus_event' || memType === 'MARKET_EVENT') {
        return 'consensus_event';
    }
    return 'other';
}

interface MemoriesListProps {
    memories: Memory[];
}

const FILTERS = [
    { id: 'all', label: 'All' },
    { id: 'consensus_event', label: 'Events' },
    { id: 'calendar_event', label: 'Calendar Events' },
    { id: 'decision_reasoning', label: 'Decisions' },
    { id: 'post_mortem', label: 'Post-Mortems' },
    { id: 'academic_paper', label: 'Principles' },
    { id: 'lesson_learned', label: 'Lessons' },
];

export function MemoriesList({ memories }: MemoriesListProps) {
    const [filter, setFilter] = React.useState<string>('all');
    const [showFlow, setShowFlow] = React.useState(false);

    const filteredMemories = memories.filter((m) => {
        if (filter === 'all') return true;
        return getMemoryCategory(m) === filter;
    });

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
                                onClick={() => setFilter(type.id)}
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
                    <MemoryFlow memories={filteredMemories} onSelect={handleMemorySelect} />
                </div>
            )}

            {/* Memory Cards */}
            <div className="flex flex-col space-y-4">
                {filteredMemories.map((memory) => (
                    <div key={memory.id}>
                        <MemoryCard memory={memory} />
                    </div>
                ))}

                {filteredMemories.length === 0 && (
                    <div className="flex justify-center items-center py-12">
                        <p className="text-zinc-500 text-sm">No memories found in this category</p>
                    </div>
                )}
            </div>
        </div>
    );
}
