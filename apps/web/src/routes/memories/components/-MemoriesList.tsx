import * as React from 'react'
import { MemoryCard } from './-MemoryCard'

export type Memory = {
  id: string
  content: string
  created_at: string
  metadata: any
  status?: 'ACTIVE' | 'RESOLVED' | 'SUPERSEDED'
  parent_id?: string
  relationship_type?: 'REVERSAL' | 'UPDATE' | 'RESOLUTION' | 'GENERAL'
}

interface MemoriesListProps {
  memories: Memory[]
}

export function MemoriesList({ memories }: MemoriesListProps) {
  const [filter, setFilter] = React.useState<string>('all')

  const filteredMemories = memories.filter((m) => {
    if (filter === 'all') return true
    return m.metadata?.type === filter
  })

  return (
    <div className="stack gap-fluid-l">
      <div className="cluster gap-fluid-s">
        {['all', 'consensus_event', 'decision_reasoning', 'post_mortem'].map((type) => (
          <button
            key={type}
            onClick={() => setFilter(type)}
            className={`btn-vibrant text-xs uppercase tracking-widest ${
              filter === type
                ? 'bg-accent text-white'
                : 'bg-zinc-100 text-zinc-500 hover:bg-zinc-200 dark:bg-zinc-800 dark:text-zinc-400'
            }`}
          >
            {type.replace('_', ' ')}
          </button>
        ))}
      </div>

      <div className="stack gap-fluid-m">
        {filteredMemories.map((memory) => (
          <MemoryCard
            key={memory.id}
            memory={memory}
            parentMemory={memory.parent_id ? memories.find(m => m.id === memory.parent_id) : undefined}
          />
        ))}

        {filteredMemories.length === 0 && (
          <div className="text-center py-fluid-2xl text-zinc-400 font-bold uppercase tracking-widest bg-zinc-50 dark:bg-zinc-900/50 rounded-3xl border-2 border-dashed border-zinc-200 dark:border-zinc-800">
            No memories found for this category.
          </div>
        )}
      </div>
    </div>
  )
}
