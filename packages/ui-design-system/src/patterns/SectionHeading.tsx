import * as React from "react"
import { cn } from "../lib/cn"

/**
 * SectionHeading pattern.
 *
 * A section title with a gradient decorator bar and gradient text.
 * Used across 5 feature sections as a visual section divider.
 */

export interface SectionHeadingProps {
  gradient?: "electric" | "success" | "catalyst" | "ai" | "alert"
  children: React.ReactNode
  className?: string
}

const decoratorMap: Record<string, string> = {
  electric: "bg-gradient-to-b from-electric-blue-500 to-blue-600",
  success: "bg-gradient-to-b from-neon-green-500 to-emerald-600",
  catalyst: "bg-gradient-to-b from-cyber-yellow-500 to-amber-600",
  ai: "bg-gradient-to-b from-deep-purple-500 to-electric-blue-500",
  alert: "bg-gradient-to-b from-amber-500 to-orange-600",
}

const textGradientMap: Record<string, string> = {
  electric: "text-gradient-electric",
  success: "text-gradient-success",
  catalyst: "text-gradient-catalyst",
  ai: "text-gradient-electric",
  alert: "text-gradient-alert",
}

export function SectionHeading({ gradient = "electric", children, className }: SectionHeadingProps) {
  return (
    <h2 className={cn("text-3xl font-black text-zinc-900 dark:text-white flex items-center gap-4 text-display", className)}>
      <span className={cn("w-3 h-10 rounded-full shadow-lg", decoratorMap[gradient])} />
      <span className={cn("text-gradient", textGradientMap[gradient])}>{children}</span>
    </h2>
  )
}
