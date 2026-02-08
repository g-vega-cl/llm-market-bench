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

export function MemoriesList({ memories }: MemoriesListProps) {
  const [filter, setFilter] = React.useState<string>('all')
  const [view, setView] = React.useState<'list' | 'flow'>('list')

  const filteredMemories = memories.filter((m) => {
    if (filter === 'all') return true
    return m.metadata?.type === filter
  })

  const handleMemorySelect = (id: string) => {
    setView('list')
    setTimeout(() => {
      const element = document.getElementById(id)
      if (element) {
        element.scrollIntoView({ behavior: 'smooth' })
        element.classList.add('ring-2', 'ring-blue-500')
        setTimeout(() => element.classList.remove('ring-2', 'ring-blue-500'), 1500)
      }
    }, 100)
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-6">
        <div className="flex gap-2">
          {['all', 'consensus_event', 'decision_reasoning', 'post_mortem'].map((type) => (
            <button
              key={type}
              onClick={() => setFilter(type)}
              className={`px-4 py-2 rounded-full text-sm font-medium transition-all duration-200 cursor-pointer ${filter === type
                ? 'bg-blue-600 text-white shadow-lg'
                : 'bg-zinc-100 text-zinc-600 hover:bg-zinc-200'
                }`}
            >
              {type.replace('_', ' ').toUpperCase()}
            </button>
          ))}
        </div>

        <div className="flex gap-1 p-1 bg-zinc-100 rounded-lg border border-zinc-200">
          <button
            onClick={() => setView('list')}
            className={`px-3 py-1.5 rounded-md text-xs font-bold uppercase tracking-wide transition-all ${view === 'list' ? 'bg-white text-zinc-800 shadow-sm' : 'text-zinc-500 hover:text-zinc-700'
              }`}
          >
            List
          </button>
          <button
            onClick={() => setView('flow')}
            className={`px-3 py-1.5 rounded-md text-xs font-bold uppercase tracking-wide transition-all ${view === 'flow' ? 'bg-white text-zinc-800 shadow-sm' : 'text-zinc-500 hover:text-zinc-700'
              }`}
          >
            Flow
          </button>
        </div>
      </div>

      {view === 'flow' && (
        <MemoryFlow memories={filteredMemories} onSelect={handleMemorySelect} />
      )}

      {view === 'list' && (
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
      )}

      {/* 
        In Flow view, we might still want to see the list below, 
        or allow clicking nodes in Flow to jump to the list.
        Let's render the list even in Flow mode but maybe hidden or below?
        Proposed behavior: Flow View shows the graph. Clicking a node jumps to the list.
        So list should probably always be rendered if we want to jump to it?
        Or we switch view to 'list' when clicking a node?
        Currently: MemoryFlow onClick does `element.scrollIntoView`.
        Ideally, both can coexist, or Flow is a mode on top.
        
        Let's keep them separate "Tabs" for now as per "Flow View" request.
        However, for the "Scroll to" feature to work, the List items must be in the DOM.
        
        Modification: If Flow view is active, should we show the list?
        User asked for a "Flow View". 
        If I click a node in Flow view, where do I go? "Go see it in the page".
        So the list HAS to be there.
        
        Let's render the list ALWAYS, but hide it visually if in 'flow' mode?
        No, if I click in Flow view, I expect to see the details.
        Maybe Flow view is a "Header" visualization, and List is always below?
        
        "We need a "Flow" view where every event is linked..."
        
        Let's make "Flow" just show the graph AND the list below it, 
        OR change the toggle logic.
        
        If view === 'flow', show Graph + List.
        If view === 'list', show List only.
        
        Actually, let's keep the Toggle. If I click a node in Flow, it should open/reveal the card.
        But if the card is hidden because view='flow', it won't be found.
        
        Solution: When in 'flow' view, render the list as well but maybe filtered or just normally?
        The user might just want to see the graph.
        
        Let's assume "Flow View" is a full replacement visualization.
        BUT, the graph nodes are small. Where do I read the full text?
        In the tooltip I added.
        
        Wait, I added `scrollIntoView` logic in `MemoryFlow`. That requires the target element to exist.
        So if `view === 'flow'` hides the list, `scrollIntoView` fails.
        
        Fix: Always render the list, but maybe put the Flow graph at the top when enabled?
        Or, when in Flow view, show the Flow Graph AND the list.
        When in List view, just the list.
        
        Let's change the logic:
        Toggle Name: "Show Flow" vs "Hide Flow"?
        Or View: "List" | "Flow + List".
        
        Let's stick to "List" vs "Flow". 
        In "Flow", I'll render the Graph. If user clicks, I switch to List view and scroll? 
        That works.
        
        Let's modify `MemoryFlow` to accept an `onNodeClick` prop.
      */}
    </div>
  )
}
