import { createFileRoute } from '@tanstack/react-router'
import { createServerFn, useServerFn } from '@tanstack/react-start'
import { fetchMemories } from './-queries'
import { MemoriesList } from './components/-MemoriesList'
import { useInfiniteQuery } from '@tanstack/react-query'
import { queries } from '~/lib/queries'
import * as React from 'react'

const getMemories = createServerFn({ method: 'GET' })
  .handler(async (opts) => {
    const cursor = (opts as any).data as string | undefined
    return fetchMemories(cursor)
  })

export const Route = createFileRoute('/memories/')({
  component: MemoriesPage,
})

function MemoriesPage() {
  const getMemoriesFn = useServerFn(getMemories)
  
  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    status,
    error
  } = useInfiniteQuery({
    ...queries.memories.list(undefined, (pageParam) => getMemoriesFn({ data: pageParam } as any)),
  })

  // Flatten all pages into a single array
  const allMemories = React.useMemo(
    () => data?.pages.flatMap(page => page.data) || [],
    [data]
  )

  if (status === 'pending') {
    return (
      <div className="max-w-5xl mx-auto p-6 md:p-12">
        <div className="flex items-center justify-center py-24">
          <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
        </div>
      </div>
    )
  }

  if (status === 'error') {
    return (
      <div className="max-w-5xl mx-auto p-6 md:p-12">
        <div className="p-6 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-2xl">
          <p className="text-red-600 dark:text-red-300">Failed to load memories: {(error as Error).message}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-5xl mx-auto p-6 md:p-12">
      <header className="mb-12">
        <h1 className="text-4xl font-bold text-zinc-400 mb-4 tracking-tight">
          AI Memories & Insights
        </h1>
        <p className="text-zinc-400 text-lg max-w-2xl">
          Explore the collective intelligence of our LLMs. From global market news to trade post-mortems,
          this is where the AI stores its long-term market perspective.
        </p>
      </header>

      <MemoriesList memories={allMemories || []} />

      {/* Load More Button */}
      {hasNextPage && (
        <div className="mt-8 flex justify-center">
          <button
            onClick={() => fetchNextPage()}
            disabled={isFetchingNextPage}
            className="px-8 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white font-semibold rounded-lg transition-colors"
          >
            {isFetchingNextPage ? 'Loading...' : 'Load More'}
          </button>
        </div>
      )}

      {/* No More Data Indicator */}
      {!hasNextPage && allMemories && allMemories.length > 0 && (
        <div className="mt-8 text-center text-zinc-500 text-sm">
          • End of memories •
        </div>
      )}
    </div>
  )
}
