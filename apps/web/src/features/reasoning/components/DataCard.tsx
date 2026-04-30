import * as React from 'react'

export function DataCard({ item }: { item: any }) {
  if (typeof item !== 'object' || item === null) {
    return (
      <div className="p-3 md:p-4 border border-gray-200 dark:border-gray-800 rounded-xl md:rounded-2xl bg-gray-50/50 dark:bg-gray-900/50 font-mono text-[11px] md:text-xs">
        {String(item)}
      </div>
    )
  }

  const entries = Object.entries(item)
  const longTextFields = entries.filter(
    ([k, v]) => typeof v === 'string' && (v.length > 60 || k.includes('reasoning') || k.includes('summary'))
  )
  const shortFields = entries.filter(([k, v]) => !longTextFields.find(([lk]) => lk === k))

  return (
    <div className="p-5 md:p-8 rounded-2xl md:rounded-[2.5rem] border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900/40 shadow-sm hover:shadow-xl hover:border-blue-500/30 transition-all duration-300 group/card">
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4 md:gap-6">
        {shortFields.map(([k, v]) => (
          <div key={k} className="space-y-0.5 md:space-y-1">
            <h6 className="text-[8px] md:text-[9px] font-black uppercase tracking-widest text-gray-400 group-hover/card:text-blue-500/60 transition-colors">
              {k.replace(/_/g, ' ')}
            </h6>
            <div className="text-[12px] md:text-[13px] font-bold text-gray-900 dark:text-gray-100 break-words">
              {typeof v === 'boolean' ? (
                <span
                  className={`px-1.5 md:px-2 py-0.5 rounded-md text-[9px] md:text-[10px] ${
                    v ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600' : 'bg-rose-100 dark:bg-rose-900/30 text-rose-600'
                  }`}
                >
                  {v ? 'YES' : 'NO'}
                </span>
              ) : (
                String(v)
              )}
            </div>
          </div>
        ))}
      </div>
      {longTextFields.length > 0 && (
        <div className="mt-5 md:mt-8 space-y-4 md:space-y-6 pt-4 md:pt-6 border-t border-gray-100 dark:border-gray-800/50">
          {longTextFields.map(([k, v]) => (
            <div key={k} className="space-y-2 md:space-y-3">
              <h6 className="text-[8px] md:text-[9px] font-black uppercase tracking-widest text-gray-400 group-hover/card:text-blue-500/60 transition-colors">
                {k.replace(/_/g, ' ')}
              </h6>
              <div className="text-[12px] md:text-[13px] leading-relaxed text-gray-600 dark:text-gray-400 whitespace-pre-wrap font-light bg-gray-50/50 dark:bg-gray-950/30 p-3 md:p-4 rounded-xl md:rounded-2xl border border-gray-100 dark:border-gray-800/50">
                {String(v)}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
