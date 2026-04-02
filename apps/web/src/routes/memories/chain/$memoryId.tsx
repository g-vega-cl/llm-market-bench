import { createFileRoute } from '@tanstack/react-router'
import { createServerFn, useServerFn } from '@tanstack/react-start'
import { fetchMemories } from '../../memories/-queries'
import { useSuspenseQuery } from '@tanstack/react-query'
import { queries } from '~/lib/queries'
import * as React from 'react'
import { Link } from '@tanstack/react-router'

const getEventChain = createServerFn({ method: 'GET' })
  .inputValidator((d: string) => d)
  .handler(async ({ data: memoryId }: { data: string }) => {
    // Fetch all memories and build the chain
    const allMemories: any[] = []
    let cursor: string | undefined
    
    // Fetch all memories (could optimize with specific query)
    while (true) {
      const result = await fetchMemories(cursor, 100)
      allMemories.push(...result.data)
      if (!result.hasMore) break
      cursor = result.nextCursor || undefined
    }
    
    // Build the chain starting from the given memory
    const chain: any[] = []
    let currentId = memoryId
    const memoryMap = new Map(allMemories.map(m => [m.id, m]))
    
    // Traverse backwards through the chain, INCLUDING the target memory
    while (currentId) {
      const memory = memoryMap.get(currentId)
      if (!memory) break
      chain.unshift(memory) // Add to beginning to maintain chronological order
      currentId = memory.parent_id
    }
    
    return { chain, targetMemory: memoryMap.get(memoryId) }
  })

export const Route = createFileRoute('/memories/chain/$memoryId')({
  loader: ({ params }) => getEventChain({ data: params.memoryId }),
  component: EventChainPage,
})

function EventChainPage() {
  const initialData = Route.useLoaderData()
  const getEventChainFn = useServerFn(getEventChain)
  const { memoryId } = Route.useParams()

  const { data } = useSuspenseQuery({
    queryKey: queries.eventChain.detail({ id: memoryId }).queryKey,
    queryFn: () => getEventChainFn({ data: memoryId } as any),
    initialData,
  })

  const { chain, targetMemory } = data

  if (!targetMemory) {
    return (
      <div className="flex flex-col min-h-screen px-6 md:px-12 py-12">
        <div className="flex flex-col w-full max-w-3xl mx-auto">
          <div className="text-center py-12">
            <p className="text-zinc-500 text-sm">Event not found</p>
            <Link 
              to="/memories" 
              className="inline-block mt-4 px-4 py-2 bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 text-sm font-medium rounded-md"
            >
              Back to Memories
            </Link>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col min-h-screen">
      {/* Header */}
      <div className="border-b border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950">
        <div className="flex flex-col px-6 md:px-12 py-6">
          <div className="flex flex-col w-full max-w-3xl mx-auto">
            <div className="flex items-center gap-3 mb-4">
              <Link 
                to="/memories"
                className="p-1.5 rounded hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
              >
                <svg className="w-4 h-4 text-zinc-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
              </Link>
              <h1 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">
                Event Chain
              </h1>
            </div>
            <p className="text-zinc-600 dark:text-zinc-400 text-sm">
              Chronological chain including the selected event
            </p>
          </div>
        </div>
      </div>

      {/* Timeline */}
      <div className="flex flex-col flex-1 px-6 md:px-12 py-8">
        <div className="flex flex-col w-full max-w-3xl mx-auto">
          <div className="flex flex-col space-y-0">
            {chain.map((memory, index) => (
              <div key={memory.id} className="relative">
                {/* Timeline line */}
                {index < chain.length - 1 && (
                  <div className="absolute left-6 top-14 bottom-0 w-px bg-zinc-200 dark:bg-zinc-800" />
                )}
                
                {/* Event card */}
                <div 
                  id={memory.id}
                  className={`relative border rounded-md p-5 mb-0 transition-colors ${
                    memory.id === targetMemory.id
                      ? 'border-zinc-900 dark:border-zinc-100 bg-zinc-50 dark:bg-zinc-800/50'
                      : 'border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 hover:border-zinc-300 dark:hover:border-zinc-700'
                  }`}
                >
                  {/* Step indicator */}
                  <div className="flex items-start gap-4 mb-3">
                    <div className={`flex-shrink-0 w-12 h-12 rounded-full flex items-center justify-center text-sm font-semibold ${
                      memory.id === targetMemory.id
                        ? 'bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900'
                        : 'bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400'
                    }`}>
                      {index + 1}
                    </div>
                    <div className="flex-1 min-w-0 pt-1">
                      <div className="flex flex-wrap items-center gap-2 mb-1">
                        <span className={`inline-flex px-2 py-0.5 rounded text-xs font-medium uppercase tracking-wide ${
                          memory.metadata?.type === 'consensus_event' 
                            ? 'bg-blue-50 dark:bg-blue-950/30 text-blue-700 dark:text-blue-300'
                            : memory.metadata?.type === 'decision_reasoning'
                              ? 'bg-purple-50 dark:bg-purple-950/30 text-purple-700 dark:text-purple-300'
                              : memory.metadata?.type === 'post_mortem'
                                ? 'bg-amber-50 dark:bg-amber-950/30 text-amber-700 dark:text-amber-300'
                                : 'bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400'
                        }`}>
                          {(memory.metadata?.type || 'Memory').replace(/_/g, ' ')}
                        </span>
                        <span className="text-xs text-zinc-400 font-mono">
                          {new Date(memory.created_at).toLocaleString('en-US', { 
                            month: 'short', 
                            day: 'numeric',
                            year: 'numeric',
                            hour: '2-digit', 
                            minute: '2-digit' 
                          })}
                        </span>
                      </div>
                      {memory.id === targetMemory.id && (
                        <span className="text-xs font-semibold text-zinc-900 dark:text-zinc-100">← You selected this event</span>
                      )}
                    </div>
                  </div>
                  
                  {/* Content */}
                  <p className="text-base text-zinc-800 dark:text-zinc-200 leading-relaxed pl-16">
                    {memory.content}
                  </p>
                  
                  {/* Metadata */}
                  {(memory.metadata?.ticker || memory.metadata?.impact) && (
                    <div className="flex flex-wrap gap-2 mt-3 pl-16">
                      {memory.metadata.ticker && (
                        <span className="inline-flex px-2 py-1 rounded text-xs font-medium bg-blue-50 dark:bg-blue-950/30 text-blue-700 dark:text-blue-300">
                          ${memory.metadata.ticker}
                        </span>
                      )}
                      {memory.metadata.impact && (
                        <span className={`inline-flex px-2 py-1 rounded text-xs font-medium ${
                          memory.metadata.impact === 'BULLISH' 
                            ? 'bg-emerald-50 dark:bg-emerald-950/30 text-emerald-700 dark:text-emerald-300' 
                            : memory.metadata.impact === 'BEARISH' 
                              ? 'bg-rose-50 dark:bg-rose-950/30 text-rose-700 dark:text-rose-300' 
                              : 'bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400'
                        }`}>
                          {memory.metadata.impact}
                        </span>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
          
          {/* Back button */}
          <div className="mt-8 flex justify-center">
            <Link 
              to="/memories"
              className="px-6 py-2.5 border border-zinc-200 dark:border-zinc-800 hover:bg-zinc-50 dark:hover:bg-zinc-800 text-zinc-700 dark:text-zinc-300 text-sm font-medium rounded-md transition-colors"
            >
              Back to All Memories
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
