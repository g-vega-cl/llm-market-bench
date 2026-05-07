import * as React from 'react'
import { Badge, Card } from '@llm-market-bench/ui-design-system'

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

function getSeverity(severity: string): "critical" | "high" | "medium" | "low" {
  const map: Record<string, "critical" | "high" | "medium" | "low"> = {
    CRITICAL: 'critical',
    HIGH: 'high',
    MEDIUM: 'medium',
    LOW: 'low',
  }
  return map[severity] ?? 'medium'
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
    <Card variant="default" padding="md" className="border-zinc-700 bg-zinc-900/50">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-2">
            <Badge severity={getSeverity(audit.severity)} variant="outline" size="sm">
              {audit.severity}
            </Badge>
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
    </Card>
  )
}
