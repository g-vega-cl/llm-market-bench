import * as React from "react"
import { cn } from "../lib/cn"
import { semanticTokens } from "../theme"

/**
 * StatPill pattern.
 *
 * A pill-shaped filter button with a colored dot indicator, label, and count.
 * Used for activity/stats filtering (e.g., BUY/SELL/REJECTED toggles).
 */

export interface StatPillProps {
  label: string
  value: number
  colorScheme?: "accent" | "success" | "danger" | "info" | "warning" | "neutral"
  isActive?: boolean
  onClick?: () => void
  className?: string
}

const dotColorValues: Record<string, string> = {
  accent: semanticTokens.color.accent,
  success: semanticTokens.color.success,
  danger: semanticTokens.color.danger,
  info: semanticTokens.color.info,
  warning: semanticTokens.color.warning,
  neutral: "#9ca3af",
}

export function StatPill({
  label,
  value,
  colorScheme = "neutral",
  isActive = false,
  onClick,
  className,
}: StatPillProps) {
  const dotColor = dotColorValues[colorScheme] ?? dotColorValues.neutral

  return (
    <button
      onClick={onClick}
      className={cn(
        "flex items-center gap-2 px-3 py-1.5 bg-white dark:bg-zinc-900 border rounded-full shadow-sm transition-all duration-300 cursor-pointer",
        isActive
          ? "border-zinc-900 dark:border-white shadow-md scale-105"
          : "border-zinc-200 dark:border-zinc-800 hover:shadow-md hover:scale-105",
        className
      )}
    >
      <div className="w-2 h-2 rounded-full shadow-lg" style={{ backgroundColor: dotColor }} />
      <span
        className={cn(
          "text-[10px] font-black uppercase tracking-wider",
          isActive ? "text-zinc-900 dark:text-white" : "text-zinc-400"
        )}
      >
        {label}
      </span>
      <span
        className={cn(
          "text-sm font-black tabular-nums",
          isActive ? "text-zinc-900 dark:text-white" : "text-zinc-500 dark:text-zinc-400"
        )}
      >
        {value}
      </span>
    </button>
  )
}
