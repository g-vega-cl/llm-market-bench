import * as React from "react"
import { cn } from "../lib/cn"

/**
 * Card primitive.
 *
 * Composable: Card, CardHeader, CardBody, CardFooter.
 */

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "elevated" | "outlined" | "ghost"
  padding?: "none" | "sm" | "md" | "lg"
}

const cardVariants = {
  default: "bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-sm",
  elevated: "bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-md",
  outlined: "bg-transparent border border-zinc-200 dark:border-zinc-800",
  ghost: "bg-transparent",
}

const paddingMap = {
  none: "",
  sm: "p-4",
  md: "p-6",
  lg: "p-8",
}

export const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ variant = "default", padding = "md", className, children, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          "rounded-xl transition-shadow",
          cardVariants[variant],
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
