import * as React from "react"
import { cn } from "../lib/cn"

/**
 * PageLayout primitive.
 *
 * Standard page wrapper with consistent padding and max-width.
 */

export interface PageLayoutProps {
  children: React.ReactNode
  className?: string
  maxWidth?: "sm" | "md" | "lg" | "xl" | "full"
  withPadding?: boolean
}

const maxWidthMap = {
  sm: "max-w-3xl",
  md: "max-w-5xl",
  lg: "max-w-7xl",
  xl: "max-w-[90rem]",
  full: "max-w-none",
}

export function PageLayout({
  children,
  className,
  maxWidth = "lg",
  withPadding = true,
}: PageLayoutProps) {
  return (
    <div className={cn("min-h-screen", className)}>
      <div
        className={cn(
          "mx-auto w-full",
          maxWidthMap[maxWidth],
          withPadding && "px-6 md:px-12 py-8"
        )}
      >
        {children}
      </div>
    </div>
  )
}
