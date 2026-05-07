import * as React from "react"
import { cn } from "../lib/cn"

/**
 * MetricTile pattern.
 *
 * A small stat card with an icon/emoji, label, and value.
 * Used for detail cards inside trade activity, portfolio views, etc.
 */

export interface MetricTileProps {
  icon?: React.ReactNode
  label: string
  value: React.ReactNode
  className?: string
}

export function MetricTile({ icon, label, value, className }: MetricTileProps) {
  return (
    <div
      className={cn(
        "p-3 bg-zinc-50 dark:bg-zinc-950/50 rounded-xl border border-zinc-100 dark:border-zinc-900 hover:border-accent/30 dark:hover:border-accent/50 transition-colors duration-300",
        className
      )}
    >
      <div className="flex items-center gap-1.5 mb-1">
        {icon && <span className="text-lg">{icon}</span>}
        <span className="text-[9px] font-black text-zinc-400 uppercase tracking-wider">{label}</span>
      </div>
      <div className="text-lg font-black text-zinc-900 dark:text-white text-display tabular-nums">
        {value}
      </div>
    </div>
  )
}
