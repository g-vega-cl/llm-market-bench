import * as React from 'react'
import type { Memory } from './-MemoriesList'

interface MemoryCardProps {
  memory: Memory
  parentMemory?: Memory
}

export function MemoryCard({ memory, parentMemory }: MemoryCardProps) {
  return (
    <div className="card-vibrant">
      <div className="cluster justify-between mb-fluid-m">
        <div className="cluster gap-fluid-xs">
          <span className="text-[10px] font-black px-fluid-s py-1 rounded-full bg-zinc-100 dark:bg-zinc-800 text-zinc-500 uppercase tracking-widest border-2 border-zinc-200 dark:border-zinc-700">
            {memory.metadata?.type?.replace('_', ' ') || 'General Memory'}
          </span>
          {memory.status && memory.status !== 'ACTIVE' && (
            <span
              className={`text-[10px] font-black px-fluid-s py-1 rounded-full uppercase tracking-widest ${
                memory.status === 'RESOLVED'
                  ? 'bg-zinc-900 text-white border-2 border-zinc-900'
                  : 'bg-happy-yellow text-zinc-900 border-2 border-happy-yellow'
              }`}
            >
              {memory.status}
            </span>
          )}
          {memory.parent_id && (
            <span className="text-[10px] font-black px-fluid-s py-1 rounded-full bg-accent/10 text-accent uppercase tracking-widest border-2 border-accent/20">
              {memory.relationship_type || 'CHAINED'}
            </span>
          )}
        </div>
        <span className="text-[10px] font-bold text-zinc-400 uppercase tracking-widest">
          {new Date(memory.created_at).toLocaleDateString()}
        </span>
      </div>

      <p
        className={`text-fluid-lg font-bold text-zinc-800 dark:text-zinc-100 leading-snug mb-fluid-m tracking-tight ${
          memory.status === 'RESOLVED' ? 'opacity-40 grayscale' : ''
        }`}
      >
        {memory.content}
      </p>

      {memory.metadata && (
        <div className="cluster gap-fluid-xs">
          {memory.metadata.ticker && (
            <span className="px-fluid-s py-1 bg-accent/10 text-accent text-[10px] font-black rounded-lg border-2 border-accent/10 uppercase tracking-widest">
              {memory.metadata.ticker}
            </span>
          )}
          {memory.metadata.impact && (
            <span
              className={`px-fluid-s py-1 text-[10px] font-black rounded-lg border-2 uppercase tracking-widest ${
                memory.metadata.impact === 'BULLISH'
                  ? 'bg-brand/10 text-brand border-brand/10'
                  : memory.metadata.impact === 'BEARISH'
                    ? 'bg-happy-red/10 text-happy-red border-happy-red/10'
                    : 'bg-zinc-100 text-zinc-500 border-zinc-100'
              }`}
            >
              {memory.metadata.impact}
            </span>
          )}
          {memory.metadata.model_name && (
            <span className="px-fluid-s py-1 bg-happy-purple/10 text-happy-purple text-[10px] font-black rounded-lg border-2 border-happy-purple/10 uppercase tracking-widest">
              {memory.metadata.model_name}
            </span>
          )}
          {memory.metadata.is_regret !== undefined && (
            <span
              className={`px-fluid-s py-1 text-[10px] font-black rounded-lg border-2 uppercase tracking-widest ${
                memory.metadata.is_regret
                  ? 'bg-happy-yellow/10 text-happy-yellow border-happy-yellow/10'
                  : 'bg-brand/10 text-brand border-brand/10'
              }`}
            >
              {memory.metadata.is_regret ? 'Regret' : 'Success'}
            </span>
          )}
        </div>
      )}

      {memory.parent_id && (
        <div className="mt-fluid-m pt-fluid-m border-t-2 border-zinc-50 dark:border-zinc-800/50">
          <div className="flex items-center gap-fluid-s text-accent">
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={3}
                d="M13 7l5 5m0 0l-5 5m5-5H6"
              />
            </svg>
            <span className="text-[10px] font-black uppercase tracking-widest">
              {memory.relationship_type || 'Related to'}:
            </span>
            <p className="text-[10px] font-bold text-zinc-400 truncate max-w-md italic">
              {parentMemory?.content || 'Previous Event'}
            </p>
          </div>
        </div>
      )}
    </div>
  )
}
