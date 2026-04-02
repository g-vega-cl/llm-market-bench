import * as React from 'react'
import type { Memory } from './-MemoriesList'

interface MemoryCardProps {
  memory: Memory
  parentMemory?: Memory
}

export function MemoryCard({ memory, parentMemory }: MemoryCardProps) {
  const [isExpanded, setIsExpanded] = React.useState(false)
  const [selectedAsset, setSelectedAsset] = React.useState<any | null>(null)

  const typeColors: Record<string, string> = {
    consensus_event: 'bg-electric-blue-50 text-electric-blue-700 border-electric-blue-200 dark:bg-electric-blue-950/30 dark:text-electric-blue-300 dark:border-electric-blue-900',
    decision_reasoning: 'bg-deep-purple-50 text-deep-purple-700 border-deep-purple-200 dark:bg-deep-purple-950/30 dark:text-deep-purple-300 dark:border-deep-purple-900',
    post_mortem: 'bg-cyber-yellow-50 text-cyber-yellow-700 border-cyber-yellow-200 dark:bg-cyber-yellow-950/30 dark:text-cyber-yellow-300 dark:border-cyber-yellow-900',
  }

  const typeIcons: Record<string, React.ReactNode> = {
    consensus_event: (
      <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
        <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
      </svg>
    ),
    decision_reasoning: (
      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
      </svg>
    ),
    post_mortem: (
      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
      </svg>
    ),
  }

  const defaultTypeStyle = 'bg-zinc-50 text-zinc-700 border-zinc-200 dark:bg-zinc-900/50 dark:text-zinc-400 dark:border-zinc-800'
  const typeStyle = typeColors[memory.metadata?.type] || defaultTypeStyle
  const typeIcon = typeIcons[memory.metadata?.type] || typeIcons.decision_reasoning

  return (
    <div
      id={memory.id}
      className="group relative flex flex-col w-full bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-6 md:p-7 shadow-sm hover:shadow-xl hover:shadow-zinc-200/50 dark:hover:shadow-zinc-950/50 hover:border-zinc-300 dark:hover:border-zinc-700 transition-all duration-300 scroll-mt-32"
    >
      {/* Status Indicator Bar */}
      <div className={`absolute left-0 top-6 bottom-6 w-1 rounded-r-full ${
        memory.status === 'RESOLVED' ? 'bg-zinc-400' :
        memory.relationship_type === 'REVERSAL' ? 'bg-alert-red-500' :
        memory.relationship_type === 'UPDATE' ? 'bg-electric-blue-500' :
        memory.relationship_type === 'RESOLUTION' ? 'bg-neon-green-500' :
        'bg-transparent'
      }`} />

      {/* Header */}
      <div className="flex flex-wrap items-start gap-3 mb-5 pl-3">
        <div className="flex flex-wrap gap-2 items-center">
          <span className={`inline-flex flex-shrink-0 items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold uppercase tracking-wider border ${typeStyle}`}>
            {typeIcon}
            {(memory.metadata?.type || 'General Memory').replace('_', ' ')}
          </span>
          
          {memory.status && memory.status !== 'ACTIVE' && (
            <span className={`inline-flex flex-shrink-0 items-center px-2.5 py-1.5 rounded-lg text-[10px] font-black uppercase tracking-wider ${
              memory.status === 'RESOLVED' 
                ? 'bg-zinc-800 text-white dark:bg-zinc-700' 
                : 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300'
            }`}>
              {memory.status}
            </span>
          )}
          
          {memory.parent_id && (
            <span className="inline-flex flex-shrink-0 items-center px-2.5 py-1.5 rounded-lg text-[10px] font-black uppercase tracking-wider bg-electric-blue-50 text-electric-blue-700 dark:bg-electric-blue-950/30 dark:text-electric-blue-300 border border-electric-blue-200 dark:border-electric-blue-900">
              {memory.relationship_type || 'CHAINED'}
            </span>
          )}
        </div>
        
        <span className="text-xs text-zinc-400 dark:text-zinc-500 font-mono pl-3 whitespace-nowrap">
          {new Date(memory.created_at).toLocaleString('en-US', { 
            month: 'short', 
            day: 'numeric', 
            hour: '2-digit', 
            minute: '2-digit' 
          })}
        </span>
      </div>

      {/* Content */}
      <p className={`w-full text-lg md:text-xl text-zinc-800 dark:text-zinc-200 font-medium leading-relaxed mb-6 pl-3 ${
        memory.status === 'RESOLVED' ? 'opacity-50 line-through' : ''
      }`}>
        {memory.content}
      </p>

      {/* Metadata Tags */}
      {memory.metadata && Object.keys(memory.metadata).length > 0 && (
        <div className="flex flex-wrap gap-2 mb-5 pl-3">
          {memory.metadata.ticker && (
            <span className="inline-flex flex-shrink-0 items-center px-3 py-1.5 bg-electric-blue-50 dark:bg-electric-blue-950/30 text-electric-blue-700 dark:text-electric-blue-300 rounded-lg text-xs font-semibold border border-electric-blue-200 dark:border-electric-blue-900">
              <svg className="w-3.5 h-3.5 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
              </svg>
              {memory.metadata.ticker}
            </span>
          )}
          
          {memory.metadata.impact && (
            <span className={`inline-flex flex-shrink-0 items-center px-3 py-1.5 rounded-lg text-xs font-semibold border ${
              memory.metadata.impact === 'BULLISH' 
                ? 'bg-emerald-50 dark:bg-emerald-950/30 text-emerald-700 dark:text-emerald-300 border-emerald-200 dark:border-emerald-900' 
                : memory.metadata.impact === 'BEARISH' 
                  ? 'bg-rose-50 dark:bg-rose-950/30 text-rose-700 dark:text-rose-300 border-rose-200 dark:border-rose-900' 
                  : 'bg-zinc-50 dark:bg-zinc-900/50 text-zinc-700 dark:text-zinc-400 border-zinc-200 dark:border-zinc-800'
            }`}>
              {memory.metadata.impact === 'BULLISH' && (
                <svg className="w-3.5 h-3.5 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                </svg>
              )}
              {memory.metadata.impact === 'BEARISH' && (
                <svg className="w-3.5 h-3.5 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 17h8m0 0V9m0 8l-8-8-4 4-6-6" />
                </svg>
              )}
              Impact: {memory.metadata.impact}
            </span>
          )}
          
          {memory.metadata.model_name && (
            <span className="inline-flex flex-shrink-0 items-center px-3 py-1.5 bg-deep-purple-50 dark:bg-deep-purple-950/30 text-deep-purple-700 dark:text-deep-purple-300 rounded-lg text-xs font-semibold border border-deep-purple-200 dark:border-deep-purple-900">
              <svg className="w-3.5 h-3.5 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
              {memory.metadata.model_name}
            </span>
          )}
          
          {memory.metadata.is_regret !== undefined && (
            <span className={`inline-flex flex-shrink-0 items-center px-3 py-1.5 rounded-lg text-xs font-semibold border ${
              memory.metadata.is_regret 
                ? 'bg-amber-50 dark:bg-amber-950/30 text-amber-700 dark:text-amber-300 border-amber-200 dark:border-amber-900' 
                : 'bg-emerald-50 dark:bg-emerald-950/30 text-emerald-700 dark:text-emerald-300 border-emerald-200 dark:border-emerald-900'
            }`}>
              {memory.metadata.is_regret ? (
                <svg className="w-3.5 h-3.5 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              ) : (
                <svg className="w-3.5 h-3.5 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              )}
              {memory.metadata.is_regret ? 'Regret' : 'Success'}
            </span>
          )}
        </div>
      )}

      {/* Scenario Analysis / Profit Section */}
      {memory.metadata?.scenario_analysis && (
        <div className="w-full pl-3">
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="group/btn flex items-center gap-2.5 px-4 py-2.5 rounded-xl bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 text-xs font-bold uppercase tracking-wider hover:bg-zinc-800 dark:hover:bg-zinc-200 transition-all duration-200 shadow-md hover:shadow-lg"
          >
            <svg
              className={`w-4 h-4 transition-transform duration-300 ${isExpanded ? 'rotate-180' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M19 9l-7 7-7-7" />
            </svg>
            Profit Analysis
          </button>

          {isExpanded && (
            <div className="w-full mt-4 p-5 rounded-2xl bg-gradient-to-br from-zinc-50 to-white dark:from-zinc-900 dark:to-zinc-900/50 border border-zinc-200 dark:border-zinc-800 shadow-inner animate-in fade-in slide-in-from-top-2 duration-300">
              <div className="flex items-center gap-2.5 mb-4">
                <div className="p-2 rounded-lg bg-cyber-yellow-100 dark:bg-cyber-yellow-900/30 text-cyber-yellow-700 dark:text-cyber-yellow-300">
                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M3 3a1 1 0 000 2v8a2 2 0 002 2h2.586l-1.293 1.293a1 1 0 101.414 1.414L10 15.414l2.293 2.293a1 1 0 001.414-1.414L12.414 15H15a2 2 0 002-2V5a1 1 0 100-2H3zm11.707 4.707a1 1 0 00-1.414-1.414L10 9.586 8.707 8.293a1 1 0 00-1.414 0l-2 2a1 1 0 101.414 1.414L8 10.414l1.293 1.293a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                </div>
                <h4 className="text-xs font-black uppercase tracking-widest text-zinc-900 dark:text-zinc-100">Scenario Analysis & Trading Strategies</h4>
              </div>

              <div className="flex flex-col space-y-3">
                {memory.metadata.scenario_analysis
                  .split('**Investable Assets (via FMP):**')[0]
                  .split(/(Scenario [A-Z]:)/)
                  .filter(Boolean)
                  .map((part: string, i: number, arr: string[]) => {
                  if (part.match(/Scenario [A-Z]:/)) {
                    const content = arr[i + 1] || '';
                    const [outcome, tradingPlan] = content.split(/Trading Plan.*?:/);

                    return (
                      <div key={i} className="w-full bg-white dark:bg-zinc-800/50 p-4 rounded-xl border border-zinc-100 dark:border-zinc-800 shadow-sm">
                        <div className="text-[10px] font-black italic uppercase text-electric-blue-600 dark:text-electric-blue-400 mb-2">{part.trim()}</div>
                        <div className="text-sm font-bold text-zinc-800 dark:text-zinc-200 leading-tight mb-3">
                          {outcome.trim()}
                        </div>
                        {tradingPlan && (
                          <div className="mt-3 pt-3 border-t border-zinc-100 dark:border-zinc-700">
                            <span className="text-[10px] font-black uppercase tracking-tighter text-emerald-600 dark:text-emerald-400 block mb-1.5">Trading Plan:</span>
                            <p className="text-sm text-zinc-600 dark:text-zinc-400 leading-relaxed font-medium">
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
                <div className="w-full mt-5 pt-5 border-t border-zinc-200 dark:border-zinc-700">
                  <div className="flex items-center gap-2.5 mb-3">
                    <div className="p-2 rounded-lg bg-electric-blue-500 text-white shadow-sm">
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                      </svg>
                    </div>
                    <h5 className="text-[10px] font-black uppercase tracking-widest text-zinc-800 dark:text-zinc-200">Investable Assets</h5>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                    {memory.metadata.discovered_assets ? (
                      memory.metadata.discovered_assets.slice(0, 6).map((asset: any, idx: number) => (
                        <button
                          key={idx}
                          onClick={() => setSelectedAsset(asset)}
                          className="flex flex-col items-start justify-between p-3 rounded-xl bg-white dark:bg-zinc-800/50 border border-zinc-100 dark:border-zinc-800 group hover:border-electric-blue-300 dark:hover:border-electric-blue-700 hover:shadow-md transition-all duration-200 text-left w-full"
                        >
                          <div className="flex flex-col w-full">
                            <div className="flex items-center gap-2 mb-1.5">
                              <span className="text-sm font-black text-electric-blue-600 dark:text-electric-blue-400 tracking-tight">${asset.ticker}</span>
                              <span className="text-[10px] font-bold text-zinc-400 dark:text-zinc-500 uppercase">
                                {asset.name}
                              </span>
                            </div>
                            <span className="text-[10px] text-zinc-500 dark:text-zinc-500 line-clamp-2 font-medium">
                              {asset.reason}
                            </span>
                          </div>
                          <div className="flex items-center gap-1.5 mt-2 text-electric-blue-500 group-hover:text-electric-blue-600 dark:group-hover:text-electric-blue-400">
                            <span className="text-[9px] font-bold uppercase tracking-wider">View Analysis</span>
                            <svg className="w-3.5 h-3.5 transition-transform group-hover:translate-x-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                            </svg>
                          </div>
                        </button>
                      ))
                    ) : (
                      <div className="col-span-full p-4 rounded-xl bg-zinc-50 dark:bg-zinc-900/50 border border-dotted border-zinc-200 dark:border-zinc-800 text-center">
                        <p className="text-[10px] text-zinc-500 dark:text-zinc-500 font-medium italic">
                          FMP assets available for newly generated events.
                          Check the text analysis above for manual suggestions.
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
        <div className="w-full mt-5 pt-5 border-t border-zinc-100 dark:border-zinc-800 pl-3">
          <div className="flex items-start gap-2 text-electric-blue-700 dark:text-electric-blue-400">
            <svg className="w-4 h-4 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
            </svg>
            <div className="flex-1 min-w-0">
              <span className="text-[10px] font-bold uppercase tracking-tight block mb-1">
                {memory.relationship_type || 'Related to'}:
              </span>
              <a
                href={`#${memory.parent_id}`}
                className="text-sm text-zinc-600 dark:text-zinc-400 truncate block hover:text-electric-blue-600 dark:hover:text-electric-blue-400 hover:underline cursor-pointer"
                title="Click to view parent event"
              >
                {parentMemory?.content || 'Previous Event'}
              </a>
            </div>
          </div>
        </div>
      )}

      {/* Asset Detail Modal */}
      {selectedAsset && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-in fade-in duration-200"
          onClick={() => setSelectedAsset(null)}
        >
          <div
            className="relative w-full max-w-2xl bg-white dark:bg-zinc-900 rounded-2xl shadow-2xl border border-zinc-200 dark:border-zinc-800 animate-in zoom-in-95 duration-200"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="flex items-center justify-between p-6 border-b border-zinc-200 dark:border-zinc-800">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-electric-blue-500 text-white">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                  </svg>
                </div>
                <div>
                  <h3 className="text-xl font-bold text-zinc-900 dark:text-zinc-100">
                    ${selectedAsset.ticker}
                  </h3>
                  <p className="text-sm text-zinc-500 dark:text-zinc-400 uppercase font-medium">
                    {selectedAsset.name}
                  </p>
                </div>
              </div>
              <button
                onClick={() => setSelectedAsset(null)}
                className="p-2 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
              >
                <svg className="w-5 h-5 text-zinc-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Content */}
            <div className="p-6">
              <div className="flex items-center gap-2 mb-4">
                <div className="p-1.5 rounded bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300">
                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 2a1 1 0 011 1v1h1a1 1 0 110 2h-1v1h1a1 1 0 110 2h-1v1h1a1 1 0 110 2h-1v1a1 1 0 11-2 0v-1H7a1 1 0 110-2h1v-1H7a1 1 0 110-2h1V7H7a1 1 0 010-2h1V3a1 1 0 011-1z" clipRule="evenodd" />
                  </svg>
                </div>
                <h4 className="text-xs font-black uppercase tracking-widest text-zinc-900 dark:text-zinc-100">
                  Investment Thesis
                </h4>
              </div>

              <div className="prose prose-sm dark:prose-invert max-w-none">
                <p className="text-zinc-700 dark:text-zinc-300 leading-relaxed whitespace-pre-wrap">
                  {selectedAsset.reason}
                </p>
              </div>

              {/* Action Buttons */}
              <div className="flex gap-3 mt-6 pt-6 border-t border-zinc-200 dark:border-zinc-800">
                <a
                  href={`https://finance.yahoo.com/quote/${selectedAsset.ticker}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-electric-blue-600 hover:bg-electric-blue-700 text-white font-semibold rounded-xl transition-colors"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                  </svg>
                  View on Yahoo Finance
                </a>
                <button
                  onClick={() => setSelectedAsset(null)}
                  className="px-6 py-3 bg-zinc-100 dark:bg-zinc-800 hover:bg-zinc-200 dark:hover:bg-zinc-700 text-zinc-700 dark:text-zinc-300 font-semibold rounded-xl transition-colors"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
