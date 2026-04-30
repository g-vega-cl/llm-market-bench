import * as React from 'react'

interface AuditCardProps {
  audit: {
    id: string
    title: string
    description: string
    severity: string
    audit_type: string
    suggestion: string | null
    created_at: string
  }
}

const severityColors: Record<string, string> = {
  CRITICAL: 'bg-rose-500/20 text-rose-400 border-rose-500/30',
  HIGH: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
  MEDIUM: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  LOW: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
}

const typeLabels: Record<string, string> = {
  DB_ANOMALY: 'DB Anomaly',
  DATA_QUALITY: 'Data Quality',
  CODE_ERROR: 'Code Error',
  SYSTEM_LOG: 'System Log',
  IMPROVEMENT: 'Improvement',
}

export function AuditCard({ audit }: AuditCardProps) {
  const [expanded, setExpanded] = React.useState(false)

  return (
    <div className="border border-zinc-700 rounded-lg p-6 bg-zinc-900/50">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-2">
            <span className={`px-2 py-1 text-xs font-semibold rounded border ${severityColors[audit.severity]}`}>
              {audit.severity}
            </span>
            <span className="text-xs text-zinc-500 uppercase tracking-wider">
              {typeLabels[audit.audit_type] || audit.audit_type}
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
