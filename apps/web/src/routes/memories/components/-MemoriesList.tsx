import * as React from 'react'
import { MemoryCard } from './-MemoryCard'
import { MemoryFlow } from './-MemoryFlow'

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

const FILTERS = [
  { id: 'all', label: 'All' },
  { id: 'consensus_event', label: 'Events' },
  { id: 'decision_reasoning', label: 'Decisions' },
  { id: 'post_mortem', label: 'Post-Mortems' },
]

export function MemoriesList({ memories }: MemoriesListProps) {
  const [filter, setFilter] = React.useState<string>('all')
  const [showFlow, setShowFlow] = React.useState(false)

  // Normalize type to handle different formats in the database
  const normalizeType = (type: string | undefined) => {
    if (!type) return ''
    return type.toLowerCase().replace(/[-_\s]+/g, '_')
  }

  const filteredMemories = memories.filter((m) => {
    if (filter === 'all') return true
    const normalizedType = normalizeType(m.metadata?.type)
    const normalizedFilter = normalizeType(filter)
    return normalizedType === normalizedFilter
  })

  const handleMemorySelect = (id: string) => {
    setShowFlow(false)
    const element = document.getElementById(id)
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }
  }

  return (
    <div className="flex flex-col space-y-6">
      {/* Control Bar */}
      <div className="sticky top-0 z-10 bg-white dark:bg-zinc-950 border-b border-zinc-200 dark:border-zinc-800 pb-4">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          {/* Filter Pills */}
          <div className="flex flex-wrap gap-2">
            {FILTERS.map((type) => (
              <button
                key={type.id}
                onClick={() => setFilter(type.id)}
                className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                  filter === type.id
                    ? 'bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900'
                    : 'bg-zinc-100 dark:bg-zinc-900 text-zinc-600 dark:text-zinc-400 hover:bg-zinc-200 dark:hover:bg-zinc-800'
                }`}
              >
                {type.label}
              </button>
            ))}
          </div>

          {/* View Toggle */}
          <button
            onClick={() => setShowFlow(!showFlow)}
            className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors border ${
              showFlow
                ? 'bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 border-zinc-900 dark:border-zinc-100'
                : 'bg-white dark:bg-zinc-900 text-zinc-700 dark:text-zinc-300 border-zinc-200 dark:border-zinc-800 hover:bg-zinc-50 dark:hover:bg-zinc-800'
            }`}
          >
            {showFlow ? 'Hide Flow' : 'Show Flow'}
          </button>
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
            <MemoryCard
              memory={memory}
              parentMemory={memory.parent_id ? memories.find(m => m.id === memory.parent_id) : null}
            />
          </div>
        ))}

        {filteredMemories.length === 0 && (
          <div className="flex justify-center items-center py-12">
            <p className="text-zinc-500 text-sm">
              No memories found in this category
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
