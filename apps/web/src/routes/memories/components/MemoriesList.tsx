import * as React from 'react'

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
            className={`px-4 py-2 rounded-full text-sm font-medium transition-all duration-200 ${
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
          <div
            key={memory.id}
            className="p-6 bg-white border border-zinc-200 rounded-xl shadow-sm hover:shadow-md transition-shadow duration-200"
          >
            <div className="flex justify-between items-start mb-4">
              <div className="flex gap-2 items-center">
                <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-zinc-100 text-zinc-800 uppercase tracking-wider">
                  {memory.metadata?.type?.replace('_', ' ') || 'General Memory'}
                </span>
                {memory.status && memory.status !== 'ACTIVE' && (
                  <span className={`text-xs font-bold px-2 py-0.5 rounded-full uppercase tracking-tight ${
                    memory.status === 'RESOLVED' ? 'bg-zinc-800 text-white' : 'bg-amber-100 text-amber-800'
                  }`}>
                    {memory.status}
                  </span>
                )}
                {memory.parent_id && (
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-blue-100 text-blue-800 uppercase tracking-tight border border-blue-200">
                    {memory.relationship_type || 'CHAINED'}
                  </span>
                )}
              </div>
              <span className="text-xs text-zinc-500">
                {new Date(memory.created_at).toLocaleString()}
              </span>
            </div>
            
            <p className={`text-zinc-800 text-lg font-medium leading-relaxed mb-4 ${
              memory.status === 'RESOLVED' ? 'opacity-50 line-through' : ''
            }`}>
              {memory.content}
            </p>

            {memory.metadata && (
              <div className="flex flex-wrap gap-2 text-xs">
                {memory.metadata.ticker && (
                   <span className="px-2 py-1 bg-blue-50 text-blue-700 rounded-md border border-blue-100">
                     Ticker: {memory.metadata.ticker}
                   </span>
                )}
                {memory.metadata.impact && (
                   <span className={`px-2 py-1 rounded-md border ${
                     memory.metadata.impact === 'BULLISH' ? 'bg-emerald-50 text-emerald-700 border-emerald-100' : 
                     memory.metadata.impact === 'BEARISH' ? 'bg-rose-50 text-rose-700 border-rose-100' : 
                     'bg-zinc-50 text-zinc-700 border-zinc-100'
                   }`}>
                     Impact: {memory.metadata.impact}
                   </span>
                )}
                {memory.metadata.model_name && (
                   <span className="px-2 py-1 bg-purple-50 text-purple-700 rounded-md border border-purple-100">
                     Model: {memory.metadata.model_name}
                   </span>
                )}
                {memory.metadata.is_regret !== undefined && (
                   <span className={`px-2 py-1 rounded-md border ${
                     memory.metadata.is_regret ? 'bg-amber-50 text-amber-700 border-amber-100' : 'bg-emerald-50 text-emerald-700 border-emerald-100'
                   }`}>
                     {memory.metadata.is_regret ? 'Regret' : 'Success'}
                   </span>
                )}
              </div>
            )}

            {memory.parent_id && (
              <div className="mt-4 pt-4 border-t border-zinc-100">
                <div className="flex items-center gap-2 text-blue-700">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                  </svg>
                  <span className="text-xs font-bold uppercase tracking-tight">
                    {memory.relationship_type || 'Related to'}:
                  </span>
                  <p className="text-xs text-zinc-500 truncate max-w-md">
                    {memories.find(m => m.id === memory.parent_id)?.content || 'Previous Event'}
                  </p>
                </div>
              </div>
            )}
          </div>
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
