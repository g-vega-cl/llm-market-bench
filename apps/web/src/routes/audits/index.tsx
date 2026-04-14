import { createFileRoute } from '@tanstack/react-router'
import { createServerFn, useServerFn } from '@tanstack/react-start'
import { fetchAudits } from './-queries'
import { queries } from '~/lib/queries'
import { useInfiniteQuery } from '@tanstack/react-query'
import * as React from 'react'

const getAudits = createServerFn({ method: 'GET' })
  .handler(async ({ data }: { data?: string }) => {
    return fetchAudits(data)
  })

export const Route = createFileRoute('/audits/')({
  component: AuditsPage,
})

function AuditsPage() {
  const getAuditsFn = useServerFn(getAudits)

  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetching,
    isFetchingNextPage,
    status,
    error
  } = useInfiniteQuery({
    ...queries.audits.list({ cursor: undefined, fetchFn: (pageParam) => getAuditsFn({ data: pageParam } as any) }),
  })

  const allAudits = React.useMemo(
    () => data?.pages.flatMap(page => page.data) || [],
    [data]
  )

  const severityOrder = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3 }
  const sortedAudits = [...allAudits].sort(
    (a, b) => severityOrder[a.severity as keyof typeof severityOrder] - severityOrder[b.severity as keyof typeof severityOrder]
  )

  const dbAudits = sortedAudits.filter(
    (a) => a.audit_type === 'DB_ANOMALY' || a.audit_type === 'DATA_QUALITY' || a.audit_type === 'CODE_ERROR'
  )
  const logAudits = sortedAudits.filter((a) => a.audit_type === 'SYSTEM_LOG')

  if (status === 'pending') {
    return (
      <div className="flex flex-col min-h-screen px-6 md:px-12 py-12 items-center justify-center">
        <div className="w-16 h-16 border-4 border-zinc-500 border-t-transparent rounded-full animate-spin mb-4" />
        <p className="text-zinc-400 text-lg">Loading audits...</p>
      </div>
    )
  }

  if (status === 'error') {
    return (
      <div className="flex flex-col min-h-screen px-6 md:px-12 py-12 items-center justify-center">
        <p className="text-red-400 text-lg mb-2">Failed to load audits</p>
        <p className="text-zinc-500 text-sm">{(error as Error).message}</p>
      </div>
    )
  }

  return (
    <div className="flex flex-col min-h-screen px-6 md:px-12 py-12">
      <div className="flex flex-col w-full">
        <header className="mb-12">
          <h1 className="text-4xl font-bold text-zinc-400 mb-4 tracking-tight">
            System Audits
          </h1>
          <p className="text-zinc-400 text-lg leading-relaxed">
            Database integrity checks, code error monitoring, and continuous improvement suggestions.
            Updated weekly.
          </p>
        </header>

        <div className="space-y-12">
          <section>
            <h2 className="text-xl font-semibold text-zinc-300 mb-6">
              Database Audits
              <span className="ml-3 text-sm font-normal text-zinc-500">
                ({dbAudits.length} findings)
              </span>
            </h2>
            {dbAudits.length === 0 ? (
              <p className="text-zinc-500 italic">No database anomalies found.</p>
            ) : (
              <div className="space-y-4">
                {dbAudits.map((audit) => (
                  <AuditCard key={audit.id} audit={audit} />
                ))}
              </div>
            )}
          </section>

          <section>
            <h2 className="text-xl font-semibold text-zinc-300 mb-6">
              System Log Analysis
              <span className="ml-3 text-sm font-normal text-zinc-500">
                ({logAudits.length} findings)
              </span>
            </h2>
            {logAudits.length === 0 ? (
              <p className="text-zinc-500 italic">No system log issues found.</p>
            ) : (
              <div className="space-y-4">
                {logAudits.map((audit) => (
                  <AuditCard key={audit.id} audit={audit} />
                ))}
              </div>
            )}
          </section>

          {hasNextPage && (
            <div className="pt-4 pb-2">
              <button
                onClick={() => fetchNextPage()}
                disabled={isFetchingNextPage}
                className="w-full py-4 px-6 rounded-xl bg-zinc-800 hover:bg-zinc-700 text-zinc-300 font-semibold text-sm transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isFetchingNextPage ? (
                  <span className="flex items-center justify-center gap-2">
                    <div className="w-4 h-4 border-2 border-zinc-400 border-t-transparent rounded-full animate-spin" />
                    Loading...
                  </span>
                ) : (
                  'Load More'
                )}
              </button>
            </div>
          )}

          {!hasNextPage && allAudits.length > 0 && (
            <div className="text-center py-4 text-zinc-500 text-xs uppercase tracking-widest">
              • End of audit findings •
            </div>
          )}

          {isFetching && !isFetchingNextPage && (
            <div className="text-center py-2">
              <div className="w-4 h-4 border-2 border-zinc-500 border-t-transparent rounded-full animate-spin mx-auto" />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function AuditCard({ audit }: { audit: any }) {
  const [expanded, setExpanded] = React.useState(false)

  const severityColors = {
    CRITICAL: 'bg-rose-500/20 text-rose-400 border-rose-500/30',
    HIGH: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
    MEDIUM: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
    LOW: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  }

  const typeLabels = {
    DB_ANOMALY: 'DB Anomaly',
    DATA_QUALITY: 'Data Quality',
    CODE_ERROR: 'Code Error',
    SYSTEM_LOG: 'System Log',
    IMPROVEMENT: 'Improvement',
  }

  return (
    <div className="border border-zinc-700 rounded-lg p-6 bg-zinc-900/50">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-2">
            <span
              className={`px-2 py-1 text-xs font-semibold rounded border ${severityColors[audit.severity as keyof typeof severityColors]}`}
            >
              {audit.severity}
            </span>
            <span className="text-xs text-zinc-500 uppercase tracking-wider">
              {typeLabels[audit.audit_type as keyof typeof typeLabels] || audit.audit_type}
            </span>
            <span className="text-xs text-zinc-600">
              {new Date(audit.created_at).toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'short',
                day: 'numeric',
              })}
            </span>
          </div>
          <h3 className="text-lg font-medium text-zinc-200 mb-2">{audit.title}</h3>
          <p className="text-zinc-400 text-sm">{audit.description}</p>
        </div>
      </div>

      {audit.suggestion && (
        <div className="mt-4 pt-4 border-t border-zinc-700">
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-sm text-zinc-400 hover:text-zinc-200 transition-colors"
          >
            {expanded ? 'Hide suggestion' : 'Show suggestion'}
          </button>
          {expanded && (
            <div className="mt-3 p-4 bg-zinc-800/50 rounded text-sm text-zinc-300 font-mono whitespace-pre-wrap">
              {typeof audit.suggestion === 'string' && audit.suggestion.startsWith('[')
                ? JSON.stringify(JSON.parse(audit.suggestion), null, 2)
                : audit.suggestion}
            </div>
          )}
        </div>
      )}
    </div>
  )
}