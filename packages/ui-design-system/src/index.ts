/**
 * LLM Market Bench — UI Design System
 *
 * Public API. Import from here only.
 *
 * @example
 * import { Button, Card, Badge, PageLayout } from "@llm-market-bench/ui-design-system"
 */

// ---------------------------------------------------------------------------
// Theme
// ---------------------------------------------------------------------------
export { semanticTokens, rawColors } from "./theme"
export type { SemanticTokens } from "./theme"

// ---------------------------------------------------------------------------
// Primitives
// ---------------------------------------------------------------------------
export { Button, LoadingSpinner } from "./primitives/Button"
export type { ButtonProps, LoadingSpinnerProps } from "./primitives/Button"

export { Card, CardHeader, CardBody, CardFooter } from "./primitives/Card"
export type { CardProps, CardHeaderProps, CardBodyProps, CardFooterProps } from "./primitives/Card"

export { Badge } from "./primitives/Badge"
export type { BadgeProps } from "./primitives/Badge"

export { Input, Label, ErrorMessage } from "./primitives/Input"
export type { InputProps, LabelProps, ErrorMessageProps } from "./primitives/Input"

export { Select } from "./primitives/Select"
export type { SelectProps } from "./primitives/Select"

export { Skeleton } from "./primitives/Skeleton"
export type { SkeletonProps } from "./primitives/Skeleton"

export { ErrorBoundary } from "./primitives/ErrorBoundary"
export type { ErrorBoundaryProps } from "./primitives/ErrorBoundary"

// ---------------------------------------------------------------------------
// Patterns
// ---------------------------------------------------------------------------
export { EmptyState } from "./patterns/EmptyState"
export type { EmptyStateProps } from "./patterns/EmptyState"

export { LoadingBoundary } from "./patterns/LoadingBoundary"
export type { LoadingBoundaryProps } from "./patterns/LoadingBoundary"

export { ErrorCard } from "./patterns/ErrorCard"
export type { ErrorCardProps } from "./patterns/ErrorCard"

// ---------------------------------------------------------------------------
// Layouts
// ---------------------------------------------------------------------------
export { PageLayout } from "./layouts/PageLayout"
export type { PageLayoutProps } from "./layouts/PageLayout"

// ---------------------------------------------------------------------------
// Utilities
// ---------------------------------------------------------------------------
export { cn } from "./lib/cn"
