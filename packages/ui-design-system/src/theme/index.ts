/**
 * Design tokens for the LLM Market Bench design system.
 *
 * Tokens are grouped into semantic categories. Components should reference
 * semantic tokens (e.g. `color-accent`) rather than raw values so the theme
 * can be re-themed without touching component code.
 */

// ---------------------------------------------------------------------------
// Raw color palettes — single source of truth for physical colors
// ---------------------------------------------------------------------------
export const rawColors = {
  electricBlue: {
    50: "#eff6ff",
    100: "#dbeafe",
    200: "#bfdbfe",
    300: "#93c5fd",
    400: "#60a5fa",
    500: "#3b82f6",
    600: "#2563eb",
    700: "#1d4ed8",
    800: "#1e40af",
    900: "#1e3a8a",
    950: "#172554",
  },
  neonGreen: {
    50: "#f0fdf4",
    100: "#dcfce7",
    200: "#bbf7d0",
    300: "#86efac",
    400: "#4ade80",
    500: "#22c55e",
    600: "#16a34a",
    700: "#15803d",
    800: "#166534",
    900: "#14532d",
    950: "#052e16",
  },
  alertRed: {
    50: "#fef2f2",
    100: "#fee2e2",
    200: "#fecaca",
    300: "#fca5a5",
    400: "#f87171",
    500: "#ef4444",
    600: "#dc2626",
    700: "#b91c1c",
    800: "#991b1b",
    900: "#7f1d1d",
    950: "#450a0a",
  },
  deepPurple: {
    50: "#faf5ff",
    100: "#f3e8ff",
    200: "#e9d5ff",
    300: "#d8b4fe",
    400: "#c084fc",
    500: "#a855f7",
    600: "#9333ea",
    700: "#7e22ce",
    800: "#6b21a8",
    900: "#581c87",
    950: "#3b0764",
  },
  cyberYellow: {
    50: "#fefce8",
    100: "#fef9c3",
    200: "#fef08a",
    300: "#fde047",
    400: "#facc15",
    500: "#eab308",
    600: "#ca8a04",
    700: "#a16207",
    800: "#854d0e",
    900: "#713f12",
    950: "#422006",
  },
  void: {
    900: "#0F172A",
    950: "#020617",
  },
  steel: {
    400: "#94a3b8",
    500: "#64748b",
    600: "#475569",
  },
}

// ---------------------------------------------------------------------------
// Semantic tokens — what components should use directly
// ---------------------------------------------------------------------------
export const semanticTokens = {
  color: {
    accent: rawColors.electricBlue[500],
    accentHover: rawColors.electricBlue[600],
    accentLight: rawColors.electricBlue[100],
    accentDark: rawColors.electricBlue[950],

    success: rawColors.neonGreen[500],
    successLight: rawColors.neonGreen[100],
    successDark: rawColors.neonGreen[950],

    danger: rawColors.alertRed[500],
    dangerLight: rawColors.alertRed[100],
    dangerDark: rawColors.alertRed[950],

    info: rawColors.deepPurple[500],
    infoLight: rawColors.deepPurple[100],
    infoDark: rawColors.deepPurple[950],

    warning: rawColors.cyberYellow[500],
    warningLight: rawColors.cyberYellow[100],
    warningDark: rawColors.cyberYellow[950],

    void900: rawColors.void[900],
    void950: rawColors.void[950],

    steel400: rawColors.steel[400],
    steel500: rawColors.steel[500],
    steel600: rawColors.steel[600],
  },
  font: {
    display: "'Space Grotesk', system-ui, sans-serif",
    body: "'Satoshi', system-ui, sans-serif",
    mono: "'JetBrains Mono', monospace",
  },
  spacing: {
    pagePaddingX: "px-6 md:px-12",
    pagePaddingY: "py-8 md:py-12",
    sectionGap: "space-y-24",
  },
  radius: {
    sm: "rounded-md",
    md: "rounded-xl",
    lg: "rounded-2xl",
    full: "rounded-full",
  },
} as const

export type SemanticTokens = typeof semanticTokens
