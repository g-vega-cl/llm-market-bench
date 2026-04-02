import { createFileRoute } from '@tanstack/react-router'
import { createServerFn, useServerFn } from '@tanstack/react-start'
import { fetchMemories } from './-queries'
import { MemoriesList } from './components/-MemoriesList'
import { useInfiniteQuery } from '@tanstack/react-query'
import { queries } from '~/lib/queries'
import * as React from 'react'
import { usePostHog } from '@posthog/react'

const getMemories = createServerFn({ method: 'GET' })
  .handler(async (opts) => {
    const cursor = (opts as any).data as string | undefined
    return fetchMemories(cursor)
  })

export const Route = createFileRoute('/memories/')({
  component: MemoriesPage,
})

function MemoriesPage() {
  const posthog = usePostHog()
  const getMemoriesFn = useServerFn(getMemories)

  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    status,
    error
  } = useInfiniteQuery({
    ...queries.memories.list({ cursor: undefined, fetchFn: (pageParam) => getMemoriesFn({ data: pageParam } as any) }),
  })

  const allMemories = React.useMemo(
    () => data?.pages.flatMap(page => page.data) || [],
    [data]
  )

  if (status === 'pending') {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <div className="relative">
          <div className="w-16 h-16 border-4 border-electric-blue-200 dark:border-electric-blue-900 rounded-full" />
          <div className="absolute inset-0 w-16 h-16 border-4 border-electric-blue-600 border-t-transparent rounded-full animate-spin" />
        </div>
      </div>
    )
  }

  if (status === 'error') {
    return (
      <div className="flex justify-center mt-24 px-6">
        <div className="w-full max-w-2xl p-8 bg-alert-red-50 dark:bg-alert-red-950/30 border border-alert-red-200 dark:border-alert-red-900 rounded-2xl">
          <div className="flex items-start gap-4">
            <div className="p-2 bg-alert-red-100 dark:bg-alert-red-900 rounded-lg">
              <svg className="w-6 h-6 text-alert-red-600 dark:text-alert-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div className="min-w-0 flex-1">
              <h3 className="text-lg font-semibold text-alert-red-800 dark:text-alert-red-300 mb-1">Failed to load memories</h3>
              <p className="text-alert-red-600 dark:text-alert-red-400 break-words">{(error as Error).message}</p>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col min-h-screen">
      {/* Hero Section */}
      <div className="relative overflow-hidden bg-gradient-to-br from-electric-blue-50 via-white to-deep-purple-50 dark:from-void-950 dark:via-void-900 dark:to-deep-purple-950/20">
        <div className="absolute inset-0 bg-[url('/grid.svg')] opacity-[0.02] dark:opacity-[0.05]" />

        {/* Decorative gradient orbs */}
        <div className="absolute top-0 right-0 w-[600px] h-[600px] bg-electric-blue-400/10 dark:bg-electric-blue-600/5 rounded-full blur-3xl -translate-y-1/2 translate-x-1/3" />
        <div className="absolute bottom-0 left-0 w-[400px] h-[400px] bg-deep-purple-400/10 dark:bg-deep-purple-600/5 rounded-full blur-3xl translate-y-1/3 -translate-x-1/4" />

        <div className="relative flex flex-col px-6 md:px-12 py-20 md:py-28">
          <div className="flex flex-col w-full max-w-5xl mx-auto">
            <div className="animate-slide-up">
              <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-electric-blue-100/60 dark:bg-electric-blue-900/40 border border-electric-blue-200 dark:border-electric-blue-800 mb-6">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-electric-blue-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-electric-blue-500"></span>
                </span>
                <span className="text-xs font-semibold text-electric-blue-700 dark:text-electric-blue-300 uppercase tracking-wider">AI Memory Bank</span>
              </div>

              <h1 className="text-5xl md:text-6xl lg:text-7xl font-bold text-zinc-900 dark:text-zinc-50 tracking-tight mb-6">
                Collective
                <span className="block text-gradient text-gradient-electric">Intelligence</span>
              </h1>

              <p className="text-xl text-zinc-600 dark:text-zinc-400 leading-relaxed">
                Explore the evolving consciousness of our AI systems. Market insights, strategic decisions, and lessons learned—stored in perpetuity.
              </p>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-4 gap-4 md:gap-8 mt-12 md:mt-16 pt-8 border-t border-zinc-200/60 dark:border-zinc-800/60">
              <div className="animate-slide-up animate-stagger-1">
                <div className="text-3xl md:text-4xl font-bold text-zinc-900 dark:text-zinc-50 mb-1">
                  {allMemories.length}
                </div>
                <div className="text-sm text-zinc-500 dark:text-zinc-500 font-medium">Total</div>
              </div>
              <div className="animate-slide-up animate-stagger-2">
                <div className="text-3xl md:text-4xl font-bold text-zinc-900 dark:text-zinc-50 mb-1">
                  {allMemories.filter(m => {
                    const type = m.metadata?.type
                    return type === 'consensus_event' || type === 'consensus-event' || type === 'Consensus Event'
                  }).length}
                </div>
                <div className="text-sm text-zinc-500 dark:text-zinc-500 font-medium">Events</div>
              </div>
              <div className="animate-slide-up animate-stagger-3">
                <div className="text-3xl md:text-4xl font-bold text-zinc-900 dark:text-zinc-50 mb-1">
                  {allMemories.filter(m => {
                    const type = m.metadata?.type
                    return type === 'decision_reasoning' || type === 'decision-reasoning' || type === 'Decision Reasoning'
                  }).length}
                </div>
                <div className="text-sm text-zinc-500 dark:text-zinc-500 font-medium">Decisions</div>
              </div>
              <div className="animate-slide-up animate-stagger-4">
                <div className="text-3xl md:text-4xl font-bold text-zinc-900 dark:text-zinc-50 mb-1">
                  {allMemories.filter(m => {
                    const type = m.metadata?.type
                    return type === 'post_mortem' || type === 'post-mortem' || type === 'Post Mortem'
                  }).length}
                </div>
                <div className="text-sm text-zinc-500 dark:text-zinc-500 font-medium">Post-Mortems</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex flex-col flex-1 px-6 md:px-12 py-12">
        <div className="flex flex-col w-full max-w-5xl mx-auto">
          <MemoriesList memories={allMemories || []} />

          {/* Load More Button */}
          {hasNextPage && (
            <div className="mt-16 flex justify-center">
              <button
                onClick={() => { fetchNextPage(); posthog.capture('memories_load_more_clicked') }}
                disabled={isFetchingNextPage}
                className="group relative px-8 py-4 bg-zinc-900 dark:bg-zinc-100 hover:bg-zinc-800 dark:hover:bg-zinc-200 disabled:bg-zinc-400 text-white dark:text-zinc-900 font-semibold rounded-xl transition-all duration-300 shadow-lg hover:shadow-xl hover:shadow-electric-blue-500/10 disabled:cursor-not-allowed"
              >
                <span className="flex items-center gap-2">
                  {isFetchingNextPage ? (
                    <>
                      <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                      </svg>
                      Loading...
                    </>
                  ) : (
                    <>
                      Discover More
                      <svg className="w-4 h-4 transition-transform group-hover:translate-y-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                      </svg>
                    </>
                  )}
                </span>
              </button>
            </div>
          )}

          {/* No More Data Indicator */}
          {!hasNextPage && allMemories && allMemories.length > 0 && (
            <div className="mt-16 flex justify-center">
              <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-zinc-100 dark:bg-zinc-900 text-zinc-500 dark:text-zinc-500 text-sm font-medium">
                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
                All memories explored
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
