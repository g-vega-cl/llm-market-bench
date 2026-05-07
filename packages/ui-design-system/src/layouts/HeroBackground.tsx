import * as React from "react"
import { cn } from "../lib/cn"

/**
 * HeroBackground layout.
 *
 * A gradient hero banner with dot-pattern overlay and animated blur orbs.
 * Used as the hero section on the Today and Market Overview pages.
 */

export interface HeroBackgroundProps {
  gradient?: "electric" | "success" | "alert" | "catalyst" | "ai"
  children: React.ReactNode
  className?: string
}

const gradientMap: Record<string, string> = {
  electric: "gradient-electric",
  success: "gradient-success",
  alert: "gradient-alert",
  catalyst: "gradient-catalyst",
  ai: "gradient-ai",
}

const overlayMap: Record<string, string> = {
  electric: "from-electric-blue-600/90 via-deep-purple-600/80 to-electric-blue-800/90",
  success: "from-neon-green-600/90 via-emerald-600/80 to-neon-green-800/90",
  alert: "from-alert-red-600/90 via-rose-600/80 to-alert-red-800/90",
  catalyst: "from-cyber-yellow-600/90 via-amber-600/80 to-cyber-yellow-800/90",
  ai: "from-deep-purple-600/90 via-electric-blue-600/80 to-deep-purple-800/90",
}

const orbColorMap: Record<string, { orb1: string; orb2: string }> = {
  electric: { orb1: "bg-electric-blue-400/20", orb2: "bg-deep-purple-400/20" },
  success: { orb1: "bg-neon-green-400/20", orb2: "bg-emerald-400/20" },
  alert: { orb1: "bg-alert-red-400/20", orb2: "bg-rose-400/20" },
  catalyst: { orb1: "bg-cyber-yellow-400/20", orb2: "bg-amber-400/20" },
  ai: { orb1: "bg-deep-purple-400/20", orb2: "bg-electric-blue-400/20" },
}

export function HeroBackground({
  gradient = "electric",
  children,
  className,
}: HeroBackgroundProps) {
  const orbs = orbColorMap[gradient]

  return (
    <div className={cn("relative overflow-hidden", gradientMap[gradient], className)}>
      <div className="absolute inset-0 opacity-10">
        <div
          className="absolute inset-0"
          style={{
            backgroundImage: `radial-gradient(circle at 2px 2px, white 1px, transparent 0)`,
            backgroundSize: "40px 40px",
          }}
        />
      </div>

      <div className={cn("absolute inset-0 bg-gradient-to-br", overlayMap[gradient])} />

      <div className={cn("absolute top-1/4 left-1/4 w-96 h-96 rounded-full blur-3xl animate-pulse", orbs.orb1)} />
      <div className={cn("absolute bottom-1/4 right-1/4 w-96 h-96 rounded-full blur-3xl animate-pulse animate-stagger-2", orbs.orb2)} />

      <div className="relative max-w-7xl mx-auto px-6 md:px-12 py-16 md:py-24">
        {children}
      </div>
    </div>
  )
}
