import * as React from "react"
import { cn } from "../lib/cn"

/**
 * Card primitive.
 *
 * Composable: Card, CardHeader, CardBody, CardFooter.
 * Variants: default, elevated, outlined, ghost, glass
 * Gradient backgrounds: electric, success, alert, catalyst, ai
 * Accent borders: left or top with optional colorScheme
 */

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "elevated" | "outlined" | "ghost" | "glass"
  padding?: "none" | "sm" | "md" | "lg"
  gradient?: "electric" | "success" | "alert" | "catalyst" | "ai"
  accentBorder?: "none" | "left" | "top"
  accentBorderColor?: "accent" | "success" | "danger" | "info" | "warning"
}

const cardVariants = {
  default: "bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-sm",
  elevated: "bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-md",
  outlined: "bg-transparent border border-zinc-200 dark:border-zinc-800",
  ghost: "bg-transparent",
  glass: "bg-white/10 dark:bg-white/5 backdrop-blur-md border border-white/20 dark:border-white/10",
}

const gradientMap: Record<string, string> = {
  electric: "gradient-electric",
  success: "gradient-success",
  alert: "gradient-alert",
  catalyst: "gradient-catalyst",
  ai: "gradient-ai",
}

const accentBorderMap: Record<string, Record<string, string>> = {
  left: {
    accent: "border-l-4 border-l-accent",
    success: "border-l-4 border-l-success",
    danger: "border-l-4 border-l-danger",
    info: "border-l-4 border-l-info",
    warning: "border-l-4 border-l-warning",
  },
  top: {
    accent: "border-t-4 border-t-accent",
    success: "border-t-4 border-t-success",
    danger: "border-t-4 border-t-danger",
    info: "border-t-4 border-t-info",
    warning: "border-t-4 border-t-warning",
  },
}

const paddingMap = {
  none: "",
  sm: "p-4",
  md: "p-6",
  lg: "p-8",
}

export const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ variant = "default", padding = "md", gradient, accentBorder = "none", accentBorderColor = "accent", className, children, ...props }, ref) => {
    const variantClasses = cardVariants[variant]
    const gradientClasses = gradient ? gradientMap[gradient] : ""
    const accentBorderClasses = accentBorder !== "none"
      ? accentBorderMap[accentBorder]?.[accentBorderColor] ?? ""
      : ""

    return (
      <div
        ref={ref}
        className={cn(
          "rounded-xl transition-shadow",
          variantClasses,
          gradientClasses,
          accentBorderClasses,
          paddingMap[padding],
          className
        )}
        {...props}
      >
        {children}
      </div>
    )
  }
)

Card.displayName = "Card"

export interface CardHeaderProps extends React.HTMLAttributes<HTMLDivElement> {}

export const CardHeader = React.forwardRef<HTMLDivElement, CardHeaderProps>(
  ({ className, children, ...props }, ref) => {
    return (
      <div ref={ref} className={cn("flex items-center justify-between mb-4", className)} {...props}>
        {children}
      </div>
    )
  }
)
CardHeader.displayName = "CardHeader"

export interface CardBodyProps extends React.HTMLAttributes<HTMLDivElement> {}

export const CardBody = React.forwardRef<HTMLDivElement, CardBodyProps>(
  ({ className, children, ...props }, ref) => {
    return (
      <div ref={ref} className={cn("", className)} {...props}>
        {children}
      </div>
    )
  }
)
CardBody.displayName = "CardBody"

export interface CardFooterProps extends React.HTMLAttributes<HTMLDivElement> {}

export const CardFooter = React.forwardRef<HTMLDivElement, CardFooterProps>(
  ({ className, children, ...props }, ref) => {
    return (
      <div ref={ref} className={cn("flex items-center justify-end gap-2 mt-4 pt-4 border-t border-zinc-100 dark:border-zinc-800", className)} {...props}>
        {children}
      </div>
    )
  }
)
CardFooter.displayName = "CardFooter"
