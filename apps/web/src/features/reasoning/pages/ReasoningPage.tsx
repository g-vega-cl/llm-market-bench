import * as React from 'react'
import { useInfiniteQuery } from '@tanstack/react-query'
import { usePostHog } from '@posthog/react'
import { reasoningQueries } from '../queries/options'
import { HumanFriendlyPrompt } from '../components/HumanFriendlyPrompt'
import { HumanFriendlyResponse } from '../components/HumanFriendlyResponse'

interface ReasoningPageProps {
  fetchFn: (cursor: string | undefined) => Promise<any>
}

export function ReasoningPage({ fetchFn }: ReasoningPageProps) {
  const posthog = usePostHog()
  const [activeTab, setActiveTab] = React.useState<string>('ALL')
  const [selectedLogId, setSelectedLogId] = React.useState<string | null>(null)

  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetching,
    isFetchingNextPage,
    status,
    error
  } = useInfiniteQuery({
    ...reasoningQueries.list({ fetchFn }),
  })

  // Flatten all pages into a single array
  const allLogs = React.useMemo(
    () => data?.pages.flatMap(page => page.data) || [],
    [data]
  )

  // Filter by category client-side (could also be done server-side)
  const categories = ['ALL', ...new Set(allLogs?.map((l) => l.task_type) || [])]
  const filteredLogs = activeTab === 'ALL'
    ? allLogs
    : allLogs?.filter((l) => l.task_type === activeTab)

  const selectedLog = allLogs?.find((l) => l.id === selectedLogId)

  // Handle loading and error states
  if (status === 'pending') {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-950 flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-gray-500 dark:text-gray-400 text-lg">Loading reasoning traces...</p>
        </div>
      </div>
    )
  }

  if (status === 'error') {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-950 flex items-center justify-center">
        <div className="text-center p-8">
          <p className="text-red-500 text-lg mb-4">Failed to load reasoning logs</p>
          <p className="text-gray-500 dark:text-gray-400 text-sm">{(error as Error).message}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 text-gray-900 dark:text-gray-100 p-4 md:p-12 animate-slow-fade">
      <header className="mb-6 md:mb-12">
        <h1 className="text-3xl md:text-5xl font-extrabold mb-3 md:mb-4 tracking-tighter bg-gradient-to-r from-blue-500 to-teal-400 bg-clip-text text-transparent">
          LLM Research Audit Trail
        </h1>
        <p className="text-gray-500 dark:text-gray-400 text-sm md:text-xl max-w-3xl leading-relaxed font-light">
          The ultimate source of truth for agent cognition. Every tool call, every prompt, and every internal "thought" trace is captured here for deep research and auditing.
        </p>
      </header>

      {/* Tabs - Horizontal scroll on mobile */}
      <div className="mb-6 md:mb-8 overflow-x-auto -mx-4 px-4 md:mx-0 md:px-0 scrollbar-hide">
        <div className="flex gap-2 p-1.5 bg-gray-100 dark:bg-gray-900/50 rounded-2xl w-fit border border-gray-200 dark:border-gray-800 backdrop-blur-xl min-w-max">
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => { setActiveTab(cat); posthog.capture('reasoning_category_filtered', { category: cat }) }}
              className={`px-4 md:px-6 py-2.5 rounded-xl text-[10px] md:text-xs font-bold uppercase tracking-widest transition-all duration-300 whitespace-nowrap min-h-[44px] ${
                activeTab === cat
                  ? 'bg-white dark:bg-blue-600 shadow-xl text-blue-600 dark:text-white border-b-2 border-blue-500 dark:border-blue-400'
                  : 'text-gray-500 hover:text-gray-800 dark:hover:text-gray-300'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      {/* Mobile: Single panel view with back navigation */}
      <div className="lg:grid lg:grid-cols-12 lg:gap-8 flex flex-col">
        {/* Mobile: Back button when trace is selected */}
        {selectedLog && (
          <div className="lg:hidden mb-4">
            <button
              onClick={() => setSelectedLogId(null)}
              className="flex items-center gap-2 px-4 py-3 rounded-xl bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 text-sm font-medium hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors min-h-[44px]"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
              Back to traces
            </button>
          </div>
        )}

        {/* Logs List - Hidden on mobile when trace selected */}
        <div className={`${selectedLog ? 'hidden lg:block' : 'block'} lg:col-span-4 space-y-3 md:space-y-4 max-h-[50vh] md:max-h-[75vh] overflow-y-auto pr-2 md:pr-4 scrollbar-thin scrollbar-thumb-blue-500/20 scrollbar-track-transparent`}>
          {filteredLogs?.map((log) => (
            <div
              key={log.id}
              onClick={() => { setSelectedLogId(log.id); posthog.capture('reasoning_trace_selected', { trace_id: log.id, task_type: log.task_type, model_provider: log.model_provider, model_name: log.model_name }) }}
              className={`p-4 md:p-5 rounded-2xl md:rounded-3xl border transition-all cursor-pointer group hover:shadow-2xl hover:-translate-y-1 ${
                selectedLogId === log.id
                  ? 'border-blue-500 bg-blue-50/50 dark:bg-blue-900/20 shadow-2xl ring-1 ring-blue-500/50'
                  : 'border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900/40 hover:border-blue-300 dark:hover:border-blue-700 shadow-sm'
              }`}
            >
              <div className="flex justify-between items-start mb-2 md:mb-3">
                <span className="px-2 md:px-3 py-0.5 md:py-1 rounded-full text-[9px] md:text-[10px] uppercase font-black tracking-widest bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400 border border-gray-200 dark:border-gray-700">
                  {log.task_type}
                </span>
                <span className="text-[9px] md:text-[10px] text-gray-400 font-mono italic">
                  {log.created_at ? new Date(log.created_at).toLocaleTimeString() : '-'}
                </span>
              </div>
              <h3 className="font-bold text-gray-800 dark:text-gray-100 text-base md:text-lg leading-tight group-hover:text-blue-500 transition-colors">
                {log.metadata?.ticker || 'Global Analysis'}
              </h3>
              <div className="flex items-center gap-2 mt-1.5 md:mt-2">
                <div className="w-1.5 h-1.5 rounded-full bg-blue-500 shadow-[0_0_8px_rgba(59,130,246,0.5)]" />
                <p className="text-[10px] md:text-[11px] font-medium text-gray-500 dark:text-gray-500 tracking-wide uppercase">
                  {log.model_provider} • {log.model_name}
                </p>
              </div>
            </div>
          ))}
          {(!filteredLogs || filteredLogs.length === 0) && (
            <div className="text-center py-8 md:py-12 p-6 md:p-8 border-2 border-dashed border-gray-200 dark:border-gray-800 rounded-2xl md:rounded-3xl text-gray-400 italic">
              No logs found for this category.
            </div>
          )}

          {/* Load More Button */}
          {hasNextPage && (
            <div className="pt-3 md:pt-4 pb-1 md:pb-2">
              <button
                onClick={() => { fetchNextPage(); posthog.capture('reasoning_load_more_clicked') }}
                disabled={isFetchingNextPage}
                className="w-full py-3 md:py-4 px-4 md:px-6 rounded-xl md:rounded-2xl bg-gradient-to-r from-blue-500 to-teal-400 text-white font-bold text-xs md:text-sm uppercase tracking-widest shadow-lg hover:shadow-xl transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed hover:-translate-y-0.5 active:translate-y-0 min-h-[44px]"
              >
                {isFetchingNextPage ? (
                  <span className="flex items-center justify-center gap-2">
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    Loading...
                  </span>
                ) : (
                  'Load More'
                )}
              </button>
            </div>
          )}

          {/* No More Data Indicator */}
          {!hasNextPage && filteredLogs && filteredLogs.length > 0 && (
            <div className="text-center py-3 md:py-4 text-gray-400 dark:text-gray-500 text-[10px] md:text-xs uppercase tracking-widest">
              • End of reasoning traces •
            </div>
          )}

          {/* Global Loading Indicator */}
          {isFetching && !isFetchingNextPage && (
            <div className="text-center py-2">
              <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto" />
            </div>
          )}
        </div>

        {/* Trace Viewer - Full width on mobile when selected */}
        <div className={`${selectedLog ? 'block' : 'hidden lg:block'} lg:col-span-8 bg-white dark:bg-gray-900/60 rounded-2xl md:rounded-[2.5rem] border border-gray-200 dark:border-gray-800 p-6 md:p-10 shadow-3xl backdrop-blur-3xl relative overflow-hidden max-h-[80vh] md:h-[75vh] flex flex-col group/viewer`}>
          {/* Decorative Background Glow */}
          <div className="absolute top-0 right-0 w-32 md:w-64 h-32 md:h-64 bg-blue-500/5 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2 pointer-events-none" />

          {!selectedLog ? (
            <div className="h-full flex flex-col items-center justify-center text-gray-400 space-y-3 md:space-y-4">
              <div className="w-12 md:w-16 h-12 md:h-16 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center animate-pulse">
                <div className="w-6 md:w-8 h-6 md:h-8 rounded bg-gray-200 dark:bg-gray-700" />
              </div>
              <p className="italic font-light text-sm md:text-lg text-center px-4">Select a reasoning trace to inspect the thinking process.</p>
            </div>
          ) : (
            <>
              {/* Sticky Header on Desktop */}
              <div className="flex justify-between items-start mb-6 md:mb-8 pb-4 md:pb-8 border-b border-gray-100 dark:border-gray-800/50 sticky top-0 bg-white dark:bg-gray-900/60 z-10 -mx-6 md:-mx-10 px-6 md:px-10 pt-6 md:pt-0">
                <div>
                  <div className="flex items-center gap-2 md:gap-3 mb-1.5 md:mb-2 flex-wrap">
                    <h2 className="text-xl md:text-3xl font-black text-gray-900 dark:text-white tracking-tight">
                      {selectedLog.metadata?.ticker || selectedLog.task_type}
                    </h2>
                    <span className="px-2 md:px-3 py-0.5 md:py-1 rounded-lg bg-blue-500/10 text-blue-500 text-[9px] md:text-[10px] uppercase font-black tracking-widest border border-blue-500/20">
                      Audit Mode
                    </span>
                  </div>
                  <p className="text-[10px] md:text-xs text-gray-400 font-mono tracking-tighter bg-gray-100 dark:bg-gray-800/50 px-1.5 md:px-2 py-0.5 md:py-1 rounded-md w-fit">
                    UUID: {selectedLog.id} • {selectedLog.created_at ? new Date(selectedLog.created_at).toLocaleString() : '-'}
                  </p>
                </div>
              </div>

              <div className="flex-1 overflow-y-auto space-y-6 md:space-y-10 pr-3 md:pr-6 scrollbar-thin scrollbar-thumb-gray-800 scrollbar-track-transparent">
                {/* Conversation Trace */}
                <HumanFriendlyPrompt prompt={selectedLog.prompt} />

                {/* Final Response */}
                <HumanFriendlyResponse response={selectedLog.response} />
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
