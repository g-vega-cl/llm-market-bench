import * as React from "react"
import { cn } from "../lib/cn"

/**
 * Badge primitive.
 *
 * Variants: solid, soft, outline, dot
 * Sizes: sm, md
 * Color schemes: accent, success, danger, info, warning, neutral
 */

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: "solid" | "soft" | "outline" | "dot"
  size?: "sm" | "md"
  colorScheme?: "accent" | "success" | "danger" | "info" | "warning" | "neutral"
}

const badgeColors: Record<string, Record<string, string>> = {
  accent: {
    solid: "bg-accent text-white",
    soft: "bg-accent-light text-accent-dark",
    outline: "border border-accent text-accent",
    dot: "bg-accent",
  },
  success: {
    solid: "bg-success text-white",
    soft: "bg-success-light text-success-dark",
    outline: "border border-success text-success",
    dot: "bg-success",
  },
  danger: {
    solid: "bg-danger text-white",
    soft: "bg-danger-light text-danger-dark",
    outline: "border border-danger text-danger",
    dot: "bg-danger",
  },
  info: {
    solid: "bg-info text-white",
    soft: "bg-info-light text-info-dark",
    outline: "border border-info text-info",
    dot: "bg-info",
  },
  warning: {
    solid: "bg-warning text-white",
    soft: "bg-warning-light text-warning-dark",
    outline: "border border-warning text-warning",
    dot: "bg-warning",
  },
  neutral: {
    solid: "bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900",
    soft: "bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400",
    outline: "border border-zinc-200 dark:border-zinc-700 text-zinc-600 dark:text-zinc-400",
    dot: "bg-zinc-400",
  },
}

export const Badge = React.forwardRef<HTMLSpanElement, BadgeProps>(
  ({ variant = "soft", size = "md", colorScheme = "neutral", className, children, ...props }, ref) => {
    const base =
      "inline-flex items-center font-medium rounded-full"
    const sizeClasses = size === "sm" ? "px-2 py-0.5 text-[10px] uppercase tracking-wider" : "px-2.5 py-1 text-xs"
    const colorClasses = badgeColors[colorScheme]?.[variant] ?? badgeColors.neutral.soft

    if (variant === "dot") {
      return (
        <span ref={ref} className={cn("inline-flex items-center gap-1.5", className)} {...props}>
          <span className={cn("w-2 h-2 rounded-full", colorClasses)} />
          <span className="text-xs text-zinc-500">{children}</span>
        </span>
      )
    }

    return (
      <span ref={ref} className={cn(base, sizeClasses, colorClasses, className)} {...props}>
        {children}
      </span>
    )
  }
)

Badge.displayName = "Badge"
