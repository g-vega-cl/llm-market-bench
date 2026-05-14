import type { Memory } from '@llm-market-bench/database';
import { Button } from '@llm-market-bench/ui-design-system';
import * as React from 'react';
import { MemoryCard } from './MemoryCard';
import { MemoryFlow } from './MemoryFlow';

export type { Memory };

interface MemoriesListProps {
    memories: Memory[];
}

const FILTERS = [
    { id: 'all', label: 'All' },
    { id: 'consensus_event', label: 'Events' },
    { id: 'decision_reasoning', label: 'Decisions' },
    { id: 'post_mortem', label: 'Post-Mortems' },
];

export function MemoriesList({ memories }: MemoriesListProps) {
    const [filter, setFilter] = React.useState<string>('all');
    const [showFlow, setShowFlow] = React.useState(false);

    // Normalize type to handle different formats in the database
    const normalizeType = (type: string | undefined) => {
        if (!type) return '';
        return type.toLowerCase().replace(/[-_\s]+/g, '_');
    };

    const filteredMemories = memories.filter((m) => {
        if (filter === 'all') return true;
        const normalizedType = normalizeType(m.metadata?.type);
        const normalizedFilter = normalizeType(filter);
        return normalizedType === normalizedFilter;
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
