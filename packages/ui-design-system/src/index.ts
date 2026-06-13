/**
 * LLM Market Bench — UI Design System
 *
 * Public API. Import from here only.
 *
 * @example
 * import { Button, Card, Badge, PageLayout } from "@llm-market-bench/ui-design-system"
 */

export { GlobalBackground } from './layouts/GlobalBackground';
export type { HeroBackgroundProps } from './layouts/HeroBackground';
export { HeroBackground } from './layouts/HeroBackground';
export type { PageLayoutProps } from './layouts/PageLayout';
// ---------------------------------------------------------------------------
// Layouts
// ---------------------------------------------------------------------------
export { PageLayout } from './layouts/PageLayout';
// ---------------------------------------------------------------------------
// Utilities
// ---------------------------------------------------------------------------
export { cn } from './lib/cn';
export type { ConfidenceBarProps } from './patterns/ConfidenceBar';
export { ConfidenceBar } from './patterns/ConfidenceBar';
export type { EmptyStateProps } from './patterns/EmptyState';
// ---------------------------------------------------------------------------
// Patterns
// ---------------------------------------------------------------------------
export { EmptyState } from './patterns/EmptyState';
export type { ErrorCardProps } from './patterns/ErrorCard';
export { ErrorCard } from './patterns/ErrorCard';
export type { LoadingBoundaryProps } from './patterns/LoadingBoundary';
export { LoadingBoundary } from './patterns/LoadingBoundary';
export type { MetricTileProps } from './patterns/MetricTile';
export { MetricTile } from './patterns/MetricTile';
export type { SectionHeadingProps } from './patterns/SectionHeading';
export { SectionHeading } from './patterns/SectionHeading';
export type { StatPillProps } from './patterns/StatPill';
export { StatPill } from './patterns/StatPill';
export type { SubHeadingProps } from './patterns/SubHeading';
export { SubHeading } from './patterns/SubHeading';
export type { BadgeProps } from './primitives/Badge';
export { Badge } from './primitives/Badge';
export type { ButtonProps, LoadingSpinnerProps } from './primitives/Button';
// ---------------------------------------------------------------------------
// Primitives
// ---------------------------------------------------------------------------
export { Button, LoadingSpinner } from './primitives/Button';
export type { CardProps } from './primitives/Card';
export { Card } from './primitives/Card';
export type { InputProps, LabelProps } from './primitives/Input';
export { Input, Label } from './primitives/Input';
export type {
    TableCellProps,
    TableHeadProps,
    TableProps,
} from './primitives/Table';
export {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from './primitives/Table';
