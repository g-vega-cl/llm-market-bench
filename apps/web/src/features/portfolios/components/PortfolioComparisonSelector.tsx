import { Badge, Button } from '@llm-market-bench/ui-design-system';
import type * as React from 'react';

export interface PortfolioOption {
    portfolioId: string;
    ownerId: string;
}

export interface PortfolioComparisonSelectorProps {
    availablePortfolios: PortfolioOption[];
    selectedIds: string[];
    portfolioColors: Record<string, string>;
    /** Optional percentage value per portfolioId, shown inside each selected chip. */
    values?: Record<string, number>;
    onAdd: (portfolioId: string) => void;
    onRemove: (portfolioId: string) => void;
    onReset?: () => void;
    maxSelected?: number;
}

function formatOwnerName(ownerId: string): string {
    return ownerId.replace(/-/g, ' ');
}

export function PortfolioComparisonSelector({
    availablePortfolios,
    selectedIds,
    portfolioColors,
    values,
    onAdd,
    onRemove,
    onReset,
    maxSelected = 5,
}: PortfolioComparisonSelectorProps) {
    const selectedCount = selectedIds.length;
    const canAdd = selectedCount < maxSelected;

    const unselectedPortfolios = availablePortfolios.filter(
        (p) => !selectedIds.includes(p.portfolioId),
    );

    const handleSelectChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
        const value = e.target.value;
        if (value && canAdd) {
            onAdd(value);
        }
        e.target.value = '';
    };

    return (
        <div className="voxel-trough flex flex-col gap-2 p-3">
            <div className="flex flex-wrap items-center justify-between gap-2 min-w-0">
                <div className="flex flex-wrap items-center gap-2 min-w-0">
                    <span className="text-xs font-bold uppercase tracking-wider text-boxel-muted whitespace-nowrap">
                        Agents to Compare
                    </span>
                    <Badge
                        variant="soft"
                        size="xs"
                        radius="none"
                        colorScheme={selectedCount === maxSelected ? 'warning' : 'neutral'}
                    >
                        {selectedCount} / {maxSelected}
                    </Badge>
                    {selectedCount === maxSelected && (
                        <span className="text-xs font-normal text-boxel-muted whitespace-nowrap">
                            (Max reached)
                        </span>
                    )}
                </div>

                <div className="flex flex-wrap items-center gap-2 min-w-0">
                    {unselectedPortfolios.length > 0 && (
                        <select
                            defaultValue=""
                            disabled={!canAdd}
                            onChange={handleSelectChange}
                            aria-label="Add agent to comparison"
                            className="bg-boxel-surface border border-boxel-bevel-hi text-xs rounded-none px-2.5 py-1 font-bold text-boxel-ink focus:outline-none focus:ring-1 focus:ring-accent disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer transition-colors"
                        >
                            <option value="" disabled>
                                {canAdd ? '+ Add Agent...' : `+ Add Agent (Max ${maxSelected})`}
                            </option>
                            {unselectedPortfolios.map((p) => (
                                <option key={p.portfolioId} value={p.portfolioId}>
                                    {formatOwnerName(p.ownerId)}
                                </option>
                            ))}
                        </select>
                    )}

                    {onReset && (
                        <Button
                            variant="ghost"
                            colorScheme="neutral"
                            size="sm"
                            rounded="none"
                            onClick={onReset}
                            className="text-xs py-1 px-2.5 h-auto text-boxel-muted hover:text-boxel-ink"
                        >
                            Reset to Top 5
                        </Button>
                    )}
                </div>
            </div>

            {selectedCount === 0 ? (
                <div className="h-9 flex items-center text-xs font-normal text-boxel-muted italic">
                    No agents selected. Choose up to {maxSelected} above to compare performance.
                </div>
            ) : (
                <div
                    data-testid="portfolio-selector-grid"
                    className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,11rem),1fr))] gap-2 items-stretch w-full min-w-0"
                >
                    {selectedIds.map((portfolioId) => {
                        const portfolio = availablePortfolios.find(
                            (p) => p.portfolioId === portfolioId,
                        );
                        const ownerName = portfolio
                            ? formatOwnerName(portfolio.ownerId)
                            : portfolioId;
                        const color = portfolioColors[portfolioId] || '#94a3b8';
                        const pct = values?.[portfolioId];

                        return (
                            <div
                                key={portfolioId}
                                data-testid="portfolio-selector-chip"
                                className="w-full min-w-0 h-9 px-2.5 flex items-center justify-between gap-2 rounded-none text-xs font-bold bg-boxel-surface border border-boxel-bevel-hi transition-colors"
                            >
                                <div className="flex items-center gap-1.5 min-w-0 flex-1">
                                    <span
                                        className="w-2 h-2 rounded-none shrink-0"
                                        style={{ backgroundColor: color }}
                                        aria-hidden="true"
                                    />
                                    <span
                                        data-testid="portfolio-chip-name"
                                        className="capitalize text-boxel-ink min-w-0 flex-1 truncate"
                                    >
                                        {ownerName}
                                    </span>
                                </div>
                                <div className="flex items-center gap-1.5 shrink-0">
                                    {pct !== undefined && (
                                        <span
                                            className={`font-bold font-mono tabular-nums whitespace-nowrap ${
                                                pct >= 0 ? 'text-success' : 'text-danger'
                                            }`}
                                        >
                                            {pct >= 0 ? '+' : ''}
                                            {pct.toFixed(2)}%
                                        </span>
                                    )}
                                    <button
                                        type="button"
                                        onClick={() => onRemove(portfolioId)}
                                        aria-label={`Remove ${ownerName} from comparison`}
                                        className="text-boxel-muted hover:text-danger rounded-none p-0.5 hover:bg-boxel-elevated transition-colors focus:outline-none focus:ring-1 focus:ring-danger shrink-0"
                                    >
                                        <svg
                                            className="w-3 h-3"
                                            fill="none"
                                            stroke="currentColor"
                                            viewBox="0 0 24 24"
                                            aria-hidden="true"
                                        >
                                            <path
                                                strokeLinecap="round"
                                                strokeLinejoin="round"
                                                strokeWidth="2"
                                                d="M6 18L18 6M6 6l12 12"
                                            />
                                        </svg>
                                    </button>
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
}
