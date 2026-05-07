import * as React from "react"
import { cn } from "../lib/cn"

/**
 * Badge primitive.
 *
 * Variants: solid, soft, outline, dot
 * Sizes: sm, md
 * Color schemes: accent, success, danger, info, warning, neutral
 * Severity schemes: critical, high, medium, low (overrides colorScheme)
 * Radius: full (rounded-full), lg (rounded-lg), md (rounded-md)
 */

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: "solid" | "soft" | "outline" | "dot"
  size?: "sm" | "md"
  colorScheme?: "accent" | "success" | "danger" | "info" | "warning" | "neutral"
  severity?: "critical" | "high" | "medium" | "low"
  radius?: "full" | "lg" | "md"
}

const badgeColors: Record<string, Record<string, string>> = {
  accent: {
    solid: "bg-accent text-white",
    soft: "bg-accent-light dark:bg-accent/20 text-accent-dark dark:text-accent",
    outline: "border border-accent/30 dark:border-accent/30 text-accent dark:text-accent",
    dot: "bg-accent",
  },
  success: {
    solid: "bg-success text-white",
    soft: "bg-success-light dark:bg-success/20 text-success-dark dark:text-success",
    outline: "border border-success/30 dark:border-success/30 text-success dark:text-success",
    dot: "bg-success",
  },
  danger: {
    solid: "bg-danger text-white",
    soft: "bg-danger-light dark:bg-danger/20 text-danger-dark dark:text-danger",
    outline: "border border-danger/30 dark:border-danger/30 text-danger dark:text-danger",
    dot: "bg-danger",
  },
  info: {
    solid: "bg-info text-white",
    soft: "bg-info-light dark:bg-info/20 text-info-dark dark:text-info",
    outline: "border border-info/30 dark:border-info/30 text-info dark:text-info",
    dot: "bg-info",
  },
  warning: {
    solid: "bg-warning text-white",
    soft: "bg-warning-light dark:bg-warning/20 text-warning-dark dark:text-warning",
    outline: "border border-warning/30 dark:border-warning/30 text-warning dark:text-warning",
    dot: "bg-warning",
  },
  neutral: {
    solid: "bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900",
    soft: "bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400",
    outline: "border border-zinc-200 dark:border-zinc-700 text-zinc-600 dark:text-zinc-400",
    dot: "bg-zinc-400",
  },
  critical: {
    solid: "bg-danger text-white",
    soft: "bg-danger/10 dark:bg-danger/20 text-danger dark:text-danger-light",
    outline: "border border-danger/20 dark:border-danger/30 text-danger dark:text-danger-light",
    dot: "bg-danger",
  },
  high: {
    solid: "bg-warning text-black",
    soft: "bg-warning/10 dark:bg-warning/20 text-warning-dark dark:text-warning",
    outline: "border border-warning/20 dark:border-warning/30 text-warning dark:text-warning",
    dot: "bg-warning",
  },
  medium: {
    solid: "bg-info text-white",
    soft: "bg-info/10 dark:bg-info/20 text-info-dark dark:text-info",
    outline: "border border-info/20 dark:border-info/30 text-info dark:text-info",
    dot: "bg-info",
  },
  low: {
    solid: "bg-accent text-white",
    soft: "bg-accent/10 dark:bg-accent/20 text-accent-dark dark:text-accent",
    outline: "border border-accent/20 dark:border-accent/30 text-accent dark:text-accent",
    dot: "bg-accent",
  },
}

const radiusMap: Record<string, string> = {
  full: "rounded-full",
  lg: "rounded-lg",
  md: "rounded-md",
}

export const Badge = React.forwardRef<HTMLSpanElement, BadgeProps>(
  ({ variant = "soft", size = "md", colorScheme, severity, radius = "full", className, children, ...props }, ref) => {
    const scheme = severity ?? colorScheme ?? "neutral"
    const base =
      "inline-flex items-center font-medium"
    const sizeClasses = size === "sm" ? "px-2 py-0.5 text-[10px] uppercase tracking-wider" : "px-2.5 py-1 text-xs"
    const colorClasses = badgeColors[scheme]?.[variant] ?? badgeColors.neutral.soft
    const radiusClasses = radiusMap[radius]

    if (variant === "dot") {
      return (
        <span ref={ref} className={cn("inline-flex items-center gap-1.5", className)} {...props}>
          <span className={cn("w-2 h-2 rounded-full", colorClasses)} />
          <span className="text-xs text-zinc-500">{children}</span>
        </span>
      )
    }

    return (
      <span ref={ref} className={cn(base, radiusClasses, sizeClasses, colorClasses, className)} {...props}>
        {children}
      </span>
    )
  }
)

Badge.displayName = "Badge"
