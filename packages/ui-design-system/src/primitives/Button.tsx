import * as React from "react"
import { cn } from "../lib/cn"

/**
 * Button primitive.
 *
 * Variants: solid, outline, ghost, soft
 * Sizes: sm, md, lg
 */

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "solid" | "outline" | "ghost" | "soft"
  size?: "sm" | "md" | "lg"
  colorScheme?: "accent" | "success" | "danger" | "info" | "warning" | "neutral"
  isLoading?: boolean
  leftIcon?: React.ReactNode
  rightIcon?: React.ReactNode
}

const colorSchemeMap: Record<string, Record<string, string>> = {
  accent: {
    solid: "bg-accent text-white hover:bg-accent-hover focus:ring-accent/40",
    outline: "border-2 border-accent text-accent hover:bg-accent/10 focus:ring-accent/40",
    ghost: "text-accent hover:bg-accent/10 focus:ring-accent/40",
    soft: "bg-accent-light text-accent-dark hover:bg-accent/20 focus:ring-accent/40",
  },
  success: {
    solid: "bg-success text-white hover:bg-success/80 focus:ring-success/40",
    outline: "border-2 border-success text-success hover:bg-success/10 focus:ring-success/40",
    ghost: "text-success hover:bg-success/10 focus:ring-success/40",
    soft: "bg-success-light text-success-dark hover:bg-success/20 focus:ring-success/40",
  },
  danger: {
    solid: "bg-danger text-white hover:bg-danger/80 focus:ring-danger/40",
    outline: "border-2 border-danger text-danger hover:bg-danger/10 focus:ring-danger/40",
    ghost: "text-danger hover:bg-danger/10 focus:ring-danger/40",
    soft: "bg-danger-light text-danger-dark hover:bg-danger/20 focus:ring-danger/40",
  },
  info: {
    solid: "bg-info text-white hover:bg-info/80 focus:ring-info/40",
    outline: "border-2 border-info text-info hover:bg-info/10 focus:ring-info/40",
    ghost: "text-info hover:bg-info/10 focus:ring-info/40",
    soft: "bg-info-light text-info-dark hover:bg-info/20 focus:ring-info/40",
  },
  warning: {
    solid: "bg-warning text-white hover:bg-warning/80 focus:ring-warning/40",
    outline: "border-2 border-warning text-warning hover:bg-warning/10 focus:ring-warning/40",
    ghost: "text-warning hover:bg-warning/10 focus:ring-warning/40",
    soft: "bg-warning-light text-warning-dark hover:bg-warning/20 focus:ring-warning/40",
  },
  neutral: {
    solid: "bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 hover:bg-zinc-800 dark:hover:bg-zinc-200 focus:ring-zinc-500/40",
    outline: "border-2 border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-100 hover:bg-zinc-100 dark:hover:bg-zinc-800 focus:ring-zinc-500/40",
    ghost: "text-zinc-900 dark:text-zinc-100 hover:bg-zinc-100 dark:hover:bg-zinc-800 focus:ring-zinc-500/40",
    soft: "bg-zinc-100 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 hover:bg-zinc-200 dark:hover:bg-zinc-700 focus:ring-zinc-500/40",
  },
}

const sizeMap = {
  sm: "px-3 py-1.5 text-sm",
  md: "px-4 py-2 text-sm",
  lg: "px-6 py-3 text-base",
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = "solid",
      size = "md",
      colorScheme = "accent",
      isLoading = false,
      leftIcon,
      rightIcon,
      className,
      children,
      disabled,
      ...props
    },
    ref
  ) => {
    const base =
      "inline-flex items-center justify-center gap-2 font-bold rounded-xl transition-all focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
    const colorClasses = colorSchemeMap[colorScheme]?.[variant] ?? colorSchemeMap.accent.solid
    const sizeClasses = sizeMap[size]

    return (
      <button
        ref={ref}
        className={cn(base, colorClasses, sizeClasses, className)}
        disabled={disabled || isLoading}
        {...props}
      >
        {isLoading && <LoadingSpinner size="sm" className="text-current" />}
        {!isLoading && leftIcon}
        {children}
        {!isLoading && rightIcon}
      </button>
    )
  }
)

Button.displayName = "Button"

/**
 * Loading spinner sub-component used internally.
 * Exported for standalone usage as well.
 */

export interface LoadingSpinnerProps extends React.SVGAttributes<SVGSVGElement> {
  size?: "xs" | "sm" | "md" | "lg"
}

export function LoadingSpinner({ size = "md", className, ...props }: LoadingSpinnerProps) {
  const sizeMapSvg = {
    xs: "w-3 h-3",
    sm: "w-4 h-4",
    md: "w-5 h-5",
    lg: "w-8 h-8",
  }

  return (
    <svg
      className={cn("animate-spin", sizeMapSvg[size], className)}
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
      {...props}
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
      />
    </svg>
  )
}
