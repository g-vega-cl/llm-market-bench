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
    <div className="space-y-6">
      <div className="flex gap-2 mb-6">
        {['all', 'consensus_event', 'decision_reasoning', 'post_mortem'].map((type) => (
          <button
            key={type}
            onClick={() => setFilter(type)}
            className={`px-4 py-2 rounded-full text-sm font-medium transition-all duration-200 cursor-pointer ${
              filter === type
                ? 'bg-blue-600 text-white shadow-lg'
                : 'bg-zinc-100 text-zinc-600 hover:bg-zinc-200'
            }`}
          >
            {type.replace('_', ' ').toUpperCase()}
          </button>
        ))}
      </div>

      <div className="grid gap-4">
        {filteredMemories.map((memory) => (
          <MemoryCard
            key={memory.id}
            memory={memory}
            parentMemory={memory.parent_id ? memories.find(m => m.id === memory.parent_id) : undefined}
          />
        ))}

        {filteredMemories.length === 0 && (
          <div className="text-center py-12 text-zinc-500">
            No memories found for this category.
          </div>
        )}
      </div>
    </div>
  )
}
