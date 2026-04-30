import * as React from "react"
import { cn } from "../lib/cn"
import { Button } from "../primitives/Button"

/**
 * EmptyState pattern.
 *
 * Used when a page or list has no data to display.
 */

export interface EmptyStateProps {
  emoji?: string
  title: string
  subtitle?: string
  actions?: Array<{
    label: string
    href?: string
    onClick?: () => void
    variant?: React.ComponentProps<typeof Button>["variant"]
  }>
  className?: string
}

export function EmptyState({ emoji, title, subtitle, actions, className }: EmptyStateProps) {
  return (
    <div className={cn("flex flex-col items-center justify-center py-16 md:py-24 text-center", className)}>
      {emoji && (
        <div className="relative mb-8">
          <div className="w-32 h-32 md:w-40 md:h-40 rounded-full flex items-center justify-center bg-gradient-to-br from-accent-light to-info-light dark:from-accent-dark/30 dark:to-info-dark/30">
            <span className="text-6xl md:text-7xl">{emoji}</span>
          </div>
        </div>
      )}
      <h2 className="text-2xl md:text-3xl font-black text-zinc-900 dark:text-white mb-3 tracking-tight">
        {title}
      </h2>
      {subtitle && (
        <p className="text-zinc-500 dark:text-zinc-400 max-w-md mb-8 text-base">
          {subtitle}
        </p>
      )}
      {actions && actions.length > 0 && (
        <div className="flex gap-4 flex-wrap justify-center">
          {actions.map((action, i) =>
            action.href ? (
              <a key={i} href={action.href}>
                <Button variant={i === 0 ? "solid" : "outline"}>{action.label}</Button>
              </a>
            ) : (
              <Button key={i} variant={i === 0 ? "solid" : "outline"} onClick={action.onClick}>
                {action.label}
              </Button>
            )
          )}
        </div>
      )}
    </div>
  )
}
