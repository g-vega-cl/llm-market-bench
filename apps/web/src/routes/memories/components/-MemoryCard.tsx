import * as React from 'react'
import type { Memory } from './-MemoriesList'

interface MemoryCardProps {
  memory: Memory
  parentMemory?: Memory
}

export function MemoryCard({ memory, parentMemory }: MemoryCardProps) {
  const [isExpanded, setIsExpanded] = React.useState(false)

  return (
    <div
      id={memory.id}
      className="p-6 bg-white border border-zinc-200 rounded-xl shadow-sm hover:shadow-md transition-shadow duration-200 scroll-mt-24"
    >
      <div className="flex justify-between items-start mb-4">
        <div className="flex gap-2 items-center">
          <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-zinc-100 text-zinc-800 uppercase tracking-wider">
            {memory.metadata?.type?.replace('_', ' ') || 'General Memory'}
          </span>
          {memory.status && memory.status !== 'ACTIVE' && (
            <span className={`text-xs font-bold px-2 py-0.5 rounded-full uppercase tracking-tight ${memory.status === 'RESOLVED' ? 'bg-zinc-800 text-white' : 'bg-amber-100 text-amber-800'
              }`}>
              {memory.status}
            </span>
          )}
          {memory.parent_id && (
            <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-blue-100 text-blue-800 uppercase tracking-tight border border-blue-200">
              {memory.relationship_type || 'CHAINED'}
            </span>
          )}
        </div>
        <span className="text-xs text-zinc-500">
          {new Date(memory.created_at).toLocaleString()}
        </span>
      </div>

      <p className={`text-zinc-800 text-lg font-medium leading-relaxed mb-4 ${memory.status === 'RESOLVED' ? 'opacity-50 line-through' : ''
        }`}>
        {memory.content}
      </p>

      {memory.metadata && (
        <div className="flex flex-wrap gap-2 text-xs">
          {memory.metadata.ticker && (
            <span className="px-2 py-1 bg-blue-50 text-blue-700 rounded-md border border-blue-100">
              Ticker: {memory.metadata.ticker}
            </span>
          )}
          {memory.metadata.impact && (
            <span className={`px-2 py-1 rounded-md border ${memory.metadata.impact === 'BULLISH' ? 'bg-emerald-50 text-emerald-700 border-emerald-100' :
                memory.metadata.impact === 'BEARISH' ? 'bg-rose-50 text-rose-700 border-rose-100' :
                  'bg-zinc-50 text-zinc-700 border-zinc-100'
              }`}>
              Impact: {memory.metadata.impact}
            </span>
          )}
          {memory.metadata.model_name && (
            <span className="px-2 py-1 bg-purple-50 text-purple-700 rounded-md border border-purple-100">
              Model: {memory.metadata.model_name}
            </span>
          )}
          {memory.metadata.is_regret !== undefined && (
            <span className={`px-2 py-1 rounded-md border ${memory.metadata.is_regret ? 'bg-amber-50 text-amber-700 border-amber-100' : 'bg-emerald-50 text-emerald-700 border-emerald-100'
              }`}>
              {memory.metadata.is_regret ? 'Regret' : 'Success'}
            </span>
          )}
        </div>
      )}

      {memory.metadata?.scenario_analysis && (
        <div className="mt-4">
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="group flex items-center gap-2 px-3 py-1.5 rounded-lg bg-zinc-900 text-white text-xs font-bold uppercase tracking-wider hover:bg-zinc-800 transition-all duration-200 cursor-pointer shadow-sm hover:shadow-md"
          >
            <svg 
              className={`w-3.5 h-3.5 transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}`} 
              fill="none" 
              stroke="currentColor" 
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M19 9l-7 7-7-7" />
            </svg>
            How to Profit from this
          </button>
          
          {isExpanded && (
            <div className="mt-4 p-4 rounded-xl bg-gradient-to-br from-zinc-50 to-white border border-zinc-200 shadow-inner animate-in fade-in slide-in-from-top-2 duration-300">
              <div className="flex items-center gap-2 mb-3">
                <div className="p-1 rounded bg-amber-100 text-amber-700">
                  <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 2a1 1 0 011 1v1h1a1 1 0 110 2h-1v1h1a1 1 0 110 2h-1v1h1a1 1 0 110 2h-1v1a1 1 0 11-2 0v-1H7a1 1 0 110-2h1v-1H7a1 1 0 110-2h1V7H7a1 1 0 010-2h1V3a1 1 0 011-1z" clipRule="evenodd" />
                  </svg>
                </div>
                <h4 className="text-xs font-black uppercase tracking-widest text-zinc-900">Profit Analysis & Chains of Events</h4>
              </div>
              
              <div className="space-y-4">
                {memory.metadata.scenario_analysis
                  .split('**Investable Assets (via FMP):**')[0]
                  .split(/(Scenario [A-Z]:)/)
                  .filter(Boolean)
                  .map((part: string, i: number, arr: string[]) => {
                  if (part.match(/Scenario [A-Z]:/)) {
                    const content = arr[i + 1] || '';
                    const [outcome, tradingPlan] = content.split(/Trading Plan.*?:/);
                    
                    return (
                      <div key={i} className="bg-white p-3 rounded-lg border border-zinc-100 shadow-sm">
                        <div className="text-[10px] font-black italic uppercase text-blue-600 mb-1">{part.trim()}</div>
                        <div className="text-sm font-bold text-zinc-800 leading-tight mb-2">
                          {outcome.trim()}
                        </div>
                        {tradingPlan && (
                          <div className="mt-2 pt-2 border-t border-zinc-50">
                            <span className="text-[10px] font-black uppercase tracking-tighter text-emerald-600 block mb-1">Trading Plan (Profit Logic):</span>
                            <p className="text-xs text-zinc-600 leading-relaxed font-medium">
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
                <div className="mt-5 pt-4 border-t border-zinc-100">
                  <div className="flex items-center gap-2 mb-3">
                    <div className="p-1 rounded-md bg-blue-500 text-white shadow-sm">
                      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                      </svg>
                    </div>
                    <h5 className="text-[10px] font-black uppercase tracking-widest text-zinc-800">Investable Assets (via FMP Discovery)</h5>
                  </div>
                  
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {memory.metadata.discovered_assets ? (
                      memory.metadata.discovered_assets.slice(0, 6).map((asset: any, idx: number) => (
                        <div key={idx} className="flex items-center justify-between p-2.5 rounded-lg bg-white border border-zinc-100 group hover:border-blue-300 hover:shadow-sm transition-all duration-200">
                          <div className="flex flex-col min-w-0">
                            <div className="flex items-center gap-1.5">
                              <span className="text-xs font-black text-blue-600 tracking-tight">${asset.ticker}</span>
                              <span className="text-[10px] font-bold text-zinc-400 group-hover:text-zinc-500 transition-colors uppercase truncate">
                                {asset.name}
                              </span>
                            </div>
                            <span className="text-[9px] text-zinc-500 truncate mt-0.5 font-medium">{asset.reason}</span>
                          </div>
                          <div className="ml-2">
                            <svg className="w-3 h-3 text-zinc-300 group-hover:text-blue-400 transition-colors" fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M10.293 3.293a1 1 0 011.414 0l6 6a1 1 0 010 1.414l-6 6a1 1 0 01-1.414-1.414L14.586 11H3a1 1 0 110-2h11.586l-4.293-4.293a1 1 0 010-1.414z" clipRule="evenodd" />
                            </svg>
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="col-span-full p-3 rounded-lg bg-zinc-50 border border-dotted border-zinc-200 text-center">
                        <p className="text-[10px] text-zinc-500 font-medium italic">
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

      {memory.parent_id && (
        <div className="mt-4 pt-4 border-t border-zinc-100">
          <div className="flex items-center gap-2 text-blue-700">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
            </svg>
            <span className="text-xs font-bold uppercase tracking-tight">
              {memory.relationship_type || 'Related to'}:
            </span>
            <a
              href={`#${memory.parent_id}`}
              className="text-xs text-zinc-500 truncate max-w-md hover:underline hover:text-blue-600 cursor-pointer block"
              title="Click to view parent event"
            >
              {parentMemory?.content || 'Previous Event'}
            </a>
          </div>
        </div>
      )}
    </div>
  )
}
