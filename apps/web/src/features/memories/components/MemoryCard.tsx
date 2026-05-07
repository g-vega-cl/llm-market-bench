import * as React from 'react'
import { Card, Badge } from '@llm-market-bench/ui-design-system'
import type { Memory } from './MemoriesList'
import { Link } from '@tanstack/react-router'
import { extractPercentage } from '~/lib/parse-scenario-percentages'

interface MemoryCardProps {
  memory: Memory
  parentMemory?: Memory | null
}

export function MemoryCard({ memory, parentMemory }: MemoryCardProps) {
  const [isExpanded, setIsExpanded] = React.useState(false)
  const [selectedAsset, setSelectedAsset] = React.useState<any | null>(null)

  return (
    <Card
      variant="default"
      padding="md"
      id={memory.id}
      className="group w-full hover:border-zinc-300 dark:hover:border-zinc-700 transition-colors"
    >
      {/* Header */}
      <div className="flex flex-wrap items-start gap-3 mb-4">
        <div className="flex flex-wrap gap-2 items-center">
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
          
          {memory.status && memory.status !== 'ACTIVE' && (
            <Badge variant={memory.status === 'RESOLVED' ? 'solid' : 'soft'} colorScheme={memory.status === 'RESOLVED' ? 'neutral' : 'warning'} size="sm">
              {memory.status}
            </Badge>
          )}
          
          {memory.parent_id && (
            <Badge variant="soft" colorScheme="info" size="sm">
              {memory.relationship_type || 'Related'}
            </Badge>
          )}
        </div>
        
        <span className="text-xs text-zinc-400 font-mono">
          {memory.created_at ? new Date(memory.created_at).toLocaleString('en-US', { 
            month: 'short', 
            day: 'numeric',
            year: 'numeric',
            hour: '2-digit', 
            minute: '2-digit' 
          }) : '-'}
        </span>
      </div>

      {/* Content */}
      <p className={`text-base text-zinc-800 dark:text-zinc-200 leading-relaxed mb-4 ${
        memory.status === 'RESOLVED' ? 'opacity-60 line-through' : ''
      }`}>
        {memory.content}
      </p>

      {/* Metadata Tags */}
      {memory.metadata && Object.keys(memory.metadata).length > 0 && (
        <div className="flex flex-wrap gap-2 mb-4">
          {memory.metadata.ticker && (
            <Badge variant="soft" colorScheme="info" size="sm">
              ${memory.metadata.ticker}
            </Badge>
          )}
          
          {memory.metadata.impact && (
            <Badge variant="soft" colorScheme={memory.metadata.impact === 'BULLISH' ? 'success' : memory.metadata.impact === 'BEARISH' ? 'danger' : 'neutral'} size="sm">
              {memory.metadata.impact}
            </Badge>
          )}
          
          {memory.metadata.model_name && (
            <Badge variant="soft" colorScheme="neutral" size="sm">
              {memory.metadata.model_name}
            </Badge>
          )}
          
          {memory.metadata.is_regret !== undefined && (
            <Badge variant="soft" colorScheme={memory.metadata.is_regret ? 'warning' : 'success'} size="sm">
              {memory.metadata.is_regret ? 'Regret' : 'Success'}
            </Badge>
          )}
        </div>
      )}

      {/* Scenario Analysis / Profit Section */}
      {memory.metadata?.scenario_analysis && (
        <div className="mt-4 pt-4 border-t border-zinc-200 dark:border-zinc-800">
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="flex items-center gap-2 text-sm font-medium text-zinc-700 dark:text-zinc-300 hover:text-zinc-900 dark:hover:text-zinc-100 transition-colors"
          >
            <svg
              className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
            {isExpanded ? 'Hide Analysis' : 'Show Analysis'}
          </button>

          {isExpanded && (
            <div className="mt-4 p-4 rounded-md bg-zinc-50 dark:bg-zinc-800/50 border border-zinc-200 dark:border-zinc-800">
              <div className="flex items-center gap-2 mb-3">
                <h4 className="text-xs font-semibold text-zinc-900 dark:text-zinc-100 uppercase tracking-wide">
                  Scenario Analysis
                </h4>
              </div>

              <div className="flex flex-col space-y-3 text-sm text-zinc-700 dark:text-zinc-300">
                {memory.metadata.scenario_analysis
                  .split('**Investable Assets (via FMP):**')[0]
                  .split(/(Scenario [A-Z]:)/)
                  .filter(Boolean)
                  .map((part: string, i: number, arr: string[]) => {
                  if (part.match(/Scenario [A-Z]:/)) {
                    const content = arr[i + 1] || '';
                    const [outcome, tradingPlan] = content.split(/Trading Plan.*?:/);

                    const pct = extractPercentage(content) || extractPercentage(part);

                    return (
                      <div key={i} className="p-3 rounded bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800">
                        <div className="flex items-center gap-2 mb-2">
                          <span className="text-xs font-semibold text-blue-600 dark:text-blue-400">{part.trim()}</span>
                          {pct && (
                            <span className="inline-flex items-center px-1.5 py-0.5 text-[10px] font-semibold bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded tabular-nums">
                              {pct}
                            </span>
                          )}
                        </div>
                        <div className="text-sm leading-relaxed mb-2">
                          {outcome.trim()}
                        </div>
                        {tradingPlan && (
                          <div className="mt-2 pt-2 border-t border-zinc-100 dark:border-zinc-800">
                            <span className="text-xs font-semibold text-emerald-600 dark:text-emerald-400 block mb-1">Trading Plan:</span>
                            <p className="text-sm leading-relaxed text-zinc-600 dark:text-zinc-400">
                              {tradingPlan.trim()}
                            </p>
                          </div>
                        )}
                      </div>
                    );
                  }
                  return null;
                })}
              </div>

              {/* Assets Section */}
              {(memory.metadata.discovered_assets || memory.metadata.scenario_analysis.includes('Investable Assets')) && (
                <div className="mt-4 pt-4 border-t border-zinc-200 dark:border-zinc-800">
                  <div className="flex items-center gap-2 mb-3">
                    <h5 className="text-xs font-semibold text-zinc-900 dark:text-zinc-100 uppercase tracking-wide">
                      Investable Assets
                    </h5>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {memory.metadata.discovered_assets ? (
                      memory.metadata.discovered_assets.slice(0, 6).map((asset: any, idx: number) => (
                        <button
                          key={idx}
                          onClick={() => setSelectedAsset(asset)}
                          className="flex flex-col items-start justify-between p-3 rounded border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 hover:bg-zinc-50 dark:hover:bg-zinc-800/50 transition-colors text-left w-full"
                        >
                          <div className="flex flex-col w-full mb-2">
                            <div className="flex items-center gap-2">
                              <span className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">${asset.ticker}</span>
                              <span className="text-xs text-zinc-500">
                                {asset.name}
                              </span>
                            </div>
                            <span className="text-xs text-zinc-600 dark:text-zinc-400 line-clamp-2 mt-1">
                              {asset.reason}
                            </span>
                          </div>
                          <span className="text-xs font-medium text-blue-600 dark:text-blue-400">
                            View details →
                          </span>
                        </button>
                      ))
                    ) : (
                      <div className="col-span-full p-4 rounded border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900/50 text-center">
                        <p className="text-xs text-zinc-500">
                          FMP assets available for newly generated events.
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Parent Memory Link */}
      {memory.parent_id && (
        <div className="mt-4 pt-4 border-t border-zinc-200 dark:border-zinc-800">
          <div className="flex items-start gap-2 text-zinc-600 dark:text-zinc-400">
            <svg className="w-4 h-4 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
            </svg>
            <div className="flex-1 min-w-0">
              <span className="text-xs font-medium uppercase tracking-wide block mb-1">
                {memory.relationship_type || 'Update'}:
              </span>
              <Link
                to="/memories/chain/$memoryId"
                params={{ memoryId: memory.id }}
                className="text-sm text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100 hover:underline block"
                title="View full event chain"
              >
                <span>View event chain →</span>
              </Link>
            </div>
          </div>
        </div>
      )}

      {/* Asset Detail Modal */}
      {selectedAsset && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 md:p-6 bg-black/50"
          onClick={() => setSelectedAsset(null)}
        >
          <div
            className="relative w-full max-w-2xl max-h-[90vh] overflow-y-auto bg-white dark:bg-zinc-900 rounded-lg shadow-lg border border-zinc-200 dark:border-zinc-800"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-zinc-200 dark:border-zinc-800">
              <div className="flex items-center gap-3">
                <div>
                  <h3 className="text-base font-semibold text-zinc-900 dark:text-zinc-100">
                    ${selectedAsset.ticker}
                  </h3>
                  <p className="text-xs text-zinc-500 uppercase">
                    {selectedAsset.name}
                  </p>
                </div>
              </div>
              <button
                onClick={() => setSelectedAsset(null)}
                className="p-1.5 rounded hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
              >
                <svg className="w-4 h-4 text-zinc-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Content */}
            <div className="p-4 md:p-6">
              <div className="mb-3">
                <h4 className="text-xs font-semibold text-zinc-900 dark:text-zinc-100 uppercase tracking-wide mb-2">
                  Investment Thesis
                </h4>
                <div className="text-sm text-zinc-700 dark:text-zinc-300 leading-relaxed whitespace-pre-wrap max-h-[50vh] overflow-y-auto scrollbar-thin scrollbar-thumb-zinc-300 dark:scrollbar-thumb-zinc-700 scrollbar-track-transparent pr-2">
                  {selectedAsset.reason}
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex flex-col sm:flex-row gap-3 mt-4 pt-4 border-t border-zinc-200 dark:border-zinc-800">
                <a
                  href={`https://finance.yahoo.com/quote/${selectedAsset.ticker}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-zinc-900 dark:bg-zinc-100 hover:bg-zinc-800 dark:hover:bg-zinc-200 text-white dark:text-zinc-900 text-sm font-medium rounded transition-colors"
                >
                  View on Yahoo Finance
                </a>
                <button
                  onClick={() => setSelectedAsset(null)}
                  className="px-4 py-2 border border-zinc-200 dark:border-zinc-800 hover:bg-zinc-50 dark:hover:bg-zinc-800 text-zinc-700 dark:text-zinc-300 text-sm font-medium rounded transition-colors"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </Card>
  )
}
