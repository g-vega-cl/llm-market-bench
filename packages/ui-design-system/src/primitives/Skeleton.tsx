import * as React from "react"
import { cn } from "../lib/cn"

/**
 * Skeleton placeholder primitive.
 *
 * Used for loading states. Can be a block (rect) or circle.
 */

export interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "rect" | "circle" | "text"
  width?: string | number
  height?: string | number
}

export const Skeleton = React.forwardRef<HTMLDivElement, SkeletonProps>(
  ({ variant = "rect", width, height, className, style, ...props }, ref) => {
    const base =
      "animate-pulse bg-zinc-200 dark:bg-zinc-800"

    const variantClasses = {
      rect: "rounded-md",
      circle: "rounded-full",
      text: "rounded-sm",
    }

    const sizeStyle: React.CSSProperties = {
      width: width ?? (variant === "text" ? "60%" : "100%"),
      height: height ?? (variant === "text" ? "1em" : undefined),
      ...style,
    }

    return (
      <div
        ref={ref}
        className={cn(base, variantClasses[variant], className)}
        style={sizeStyle}
        {...props}
      />
    )
  }
)

Skeleton.displayName = "Skeleton"
