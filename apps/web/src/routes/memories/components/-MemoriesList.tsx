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
  { id: 'all', label: 'All', icon: '◈' },
  { id: 'consensus_event', label: 'Events', icon: '●' },
  { id: 'decision_reasoning', label: 'Decisions', icon: '◆' },
  { id: 'post_mortem', label: 'Post-Mortems', icon: '▲' },
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
    setTimeout(() => {
      const element = document.getElementById(id)
      if (element) {
        element.scrollIntoView({ behavior: 'smooth', block: 'center' })
        element.classList.add('ring-2', 'ring-electric-blue-500', 'ring-offset-2')
        setTimeout(() => element.classList.remove('ring-2', 'ring-electric-blue-500', 'ring-offset-2'), 2000)
      }
    }, 100)
  }

  return (
    <div className="flex flex-col space-y-8">
      {/* Control Bar */}
      <div className="sticky top-4 z-20 -mx-6 md:-mx-12 px-6 md:px-12 py-4 bg-white/80 dark:bg-zinc-950/80 backdrop-blur-xl border-b border-zinc-200/60 dark:border-zinc-800/60">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          {/* Filter Pills */}
          <div className="flex flex-wrap gap-2">
            {FILTERS.map((type) => (
              <button
                key={type.id}
                onClick={() => setFilter(type.id)}
                className={`group flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold transition-all duration-300 cursor-pointer ${
                  filter === type.id
                    ? 'bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 shadow-lg shadow-zinc-900/20 dark:shadow-zinc-100/10 scale-105'
                    : 'bg-zinc-100 dark:bg-zinc-900 text-zinc-600 dark:text-zinc-400 hover:bg-zinc-200 dark:hover:bg-zinc-800 hover:text-zinc-900 dark:hover:text-zinc-200'
                }`}
              >
                <span className={`transition-transform duration-300 ${filter === type.id ? 'scale-110' : 'group-hover:scale-110'}`}>
                  {type.icon}
                </span>
                {type.label}
              </button>
            ))}
          </div>

          {/* View Toggle */}
          <button
            onClick={() => setShowFlow(!showFlow)}
            className={`group flex items-center gap-2.5 px-4 py-2.5 rounded-xl text-sm font-semibold transition-all duration-300 cursor-pointer border ${
              showFlow
                ? 'bg-electric-blue-600 text-white border-electric-blue-600 shadow-lg shadow-electric-blue-500/25'
                : 'bg-white dark:bg-zinc-900 text-zinc-700 dark:text-zinc-300 border-zinc-200 dark:border-zinc-800 hover:border-zinc-300 dark:hover:border-zinc-700'
            }`}
          >
            <svg className={`w-4 h-4 transition-transform duration-500 ${showFlow ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            <span>{showFlow ? 'Hide Flow' : 'Show Flow'}</span>
          </button>
        </div>
      </div>

      {/* Flow Visualization */}
      {showFlow && (
        <div className="w-full animate-scale-in">
          <MemoryFlow memories={filteredMemories} onSelect={handleMemorySelect} />
        </div>
      )}

      {/* Memory Cards */}
      <div className="flex flex-col space-y-6">
        {filteredMemories.map((memory, index) => (
          <div
            key={memory.id}
            className="animate-slide-up"
            style={{ animationDelay: `${index * 50}ms` }}
          >
            <MemoryCard
              memory={memory}
              parentMemory={memory.parent_id ? memories.find(m => m.id === memory.parent_id) : undefined}
            />
          </div>
        ))}

        {filteredMemories.length === 0 && (
          <div className="flex justify-center items-center py-20">
            <div className="flex flex-col items-center">
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-zinc-100 dark:bg-zinc-900 mb-4">
                <svg className="w-8 h-8 text-zinc-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                </svg>
              </div>
              <p className="text-zinc-500 dark:text-zinc-400 font-medium">
                No memories found in this category
              </p>
              <p className="text-zinc-400 dark:text-zinc-500 text-sm mt-1">
                Try selecting a different filter
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
