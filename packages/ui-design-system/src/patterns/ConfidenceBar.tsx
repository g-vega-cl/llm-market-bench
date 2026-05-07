import * as React from "react"
import { cn } from "../lib/cn"
import { semanticTokens } from "../theme"

/**
 * ConfidenceBar pattern.
 *
 * A labelled progress bar showing a percentage value.
 * Used across features to display confidence scores, consensus strength, etc.
 *
 * textStyle: "default" for normal page backgrounds (zinc palette),
 *            "hero" for dark gradient hero sections (white/translucent palette).
 */

export interface ConfidenceBarProps {
  label: string
  value: number
  colorScheme?: "accent" | "success" | "danger" | "info" | "warning"
  textStyle?: "default" | "hero"
  className?: string
}

const barColorValues: Record<string, string> = {
  accent: semanticTokens.color.accent,
  success: semanticTokens.color.success,
  danger: semanticTokens.color.danger,
  info: semanticTokens.color.info,
  warning: semanticTokens.color.warning,
}

export function ConfidenceBar({ label, value, colorScheme = "accent", textStyle = "default", className }: ConfidenceBarProps) {
  const clampedValue = Math.max(0, Math.min(100, value))
  const barColor = barColorValues[colorScheme] ?? barColorValues.accent
  const isHero = textStyle === "hero"

  return (
    <div className={cn("flex items-center gap-2", className)}>
      <span className={cn(
        "text-[10px] font-black uppercase tracking-wider",
        isHero ? "text-white/70" : "text-zinc-400"
      )}>
        {label}
      </span>
      <div className={cn(
        "flex-1 h-2 rounded-full overflow-hidden shadow-inner max-w-[120px]",
        isHero ? "bg-white/10" : "bg-zinc-100 dark:bg-zinc-800"
      )}>
        <div
          className="h-full rounded-full transition-all duration-1000 shadow-lg"
          style={{ width: `${clampedValue}%`, backgroundColor: barColor }}
        />
      </div>
      <span className={cn(
        "text-xs font-bold tabular-nums",
        isHero ? "text-white" : "text-zinc-500 dark:text-zinc-300"
      )}>
        {clampedValue}%
      </span>
    </div>
  )
}
