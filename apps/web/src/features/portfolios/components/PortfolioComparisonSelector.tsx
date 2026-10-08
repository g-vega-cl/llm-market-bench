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
        // Reset select back to placeholder value
        e.target.value = '';
    };

    return (
        <div className="flex flex-col gap-3 p-3 bg-zinc-50 dark:bg-zinc-900/60 rounded-xl border border-zinc-200/80 dark:border-zinc-800/80">
            <div className="flex flex-wrap items-center justify-between gap-2 min-w-0">
                <div className="flex items-center gap-2 min-w-0">
                    <span className="text-xs font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">
                        Agents to Compare
                    </span>
                    <Badge
                        variant="soft"
                        size="xs"
                        colorScheme={selectedCount === maxSelected ? 'warning' : 'neutral'}
                    >
                        {selectedCount} / {maxSelected}
                    </Badge>
                    {selectedCount === maxSelected && (
                        <span className="text-xs text-zinc-400 dark:text-zinc-500 hidden sm:inline">
                            (Max reached)
                        </span>
                    )}
                </div>

                {onReset && (
                    <Button
                        variant="ghost"
                        colorScheme="neutral"
                        size="sm"
                        onClick={onReset}
                        className="text-xs py-1 px-2.5 h-auto text-zinc-500 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100"
                    >
                        Reset to Top 5
                    </Button>
                )}
            </div>

            <div className="flex flex-wrap items-center gap-2 min-w-0">
                {selectedIds.map((portfolioId) => {
                    const portfolio = availablePortfolios.find(
                        (p) => p.portfolioId === portfolioId,
                    );
                    const ownerName = portfolio ? formatOwnerName(portfolio.ownerId) : portfolioId;
                    const color = portfolioColors[portfolioId] || '#94a3b8';

                    return (
                        <span
                            key={portfolioId}
                            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium bg-white dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 shadow-sm transition-all"
                        >
                            <span
                                className="w-2 h-2 rounded-full shrink-0"
                                style={{ backgroundColor: color }}
                                aria-hidden="true"
                            />
                            <span className="capitalize text-zinc-700 dark:text-zinc-200 max-w-xs truncate">
                                {ownerName}
                            </span>
                            <button
                                type="button"
                                onClick={() => onRemove(portfolioId)}
                                aria-label={`Remove ${ownerName} from comparison`}
                                className="ml-0.5 text-zinc-400 hover:text-red-500 dark:hover:text-red-400 rounded p-0.5 hover:bg-zinc-100 dark:hover:bg-zinc-700/50 transition-colors focus:outline-none focus:ring-1 focus:ring-red-400"
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
                        </span>
                    );
                })}

                {selectedCount === 0 && (
                    <span className="text-xs text-zinc-500 dark:text-zinc-400 italic py-1">
                        No agents selected. Choose up to {maxSelected} below to compare performance.
                    </span>
                )}

                {unselectedPortfolios.length > 0 && (
                    <div className="relative inline-block">
                        <select
                            defaultValue=""
                            disabled={!canAdd}
                            onChange={handleSelectChange}
                            aria-label="Add agent to comparison"
                            className="bg-white dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 text-xs rounded-lg px-2.5 py-1 font-medium text-zinc-700 dark:text-zinc-200 focus:outline-none focus:ring-2 focus:ring-sky-500 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer transition-colors"
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
                    </div>
                )}
            </div>
        </div>
    );
}
