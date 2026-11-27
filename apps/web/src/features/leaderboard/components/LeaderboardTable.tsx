import type { LLMLeaderboardRow } from '@llm-market-bench/database';
import {
    Badge,
    Button,
    Card,
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@llm-market-bench/ui-design-system';
import { Link } from '@tanstack/react-router';
import type { LeaderboardSortDir, LeaderboardSortField } from '../api/fetch-leaderboard';
import { formatUpDays, formatWinRate, getLeaderboardDisplayInfo } from '../lib/model-helper';

export const LEADERBOARD_PAGE_SIZE = 10;

interface LeaderboardTableProps {
    models: LLMLeaderboardRow[];
    selectedModels: string[];
    currentPage: number;
    pageSize?: number;
    totalCount: number;
    sortField: LeaderboardSortField;
    sortOrder: LeaderboardSortDir;
    isFetching?: boolean;
    onSortChange: (field: LeaderboardSortField) => void;
    onPageChange: (page: number) => void;
    onToggleSelectModel: (modelName: string) => void;
}

export function LeaderboardTable({
    models,
    selectedModels,
    currentPage,
    pageSize = LEADERBOARD_PAGE_SIZE,
    totalCount,
    sortField,
    sortOrder,
    isFetching = false,
    onSortChange,
    onPageChange,
    onToggleSelectModel,
}: LeaderboardTableProps) {
    const totalPages = Math.max(1, Math.ceil(totalCount / pageSize));
    const safePage = Math.min(Math.max(currentPage, 1), totalPages);
    const startIdx = (safePage - 1) * pageSize;
    const endIdx = Math.min(startIdx + models.length, totalCount);

    const renderSortIndicator = (field: LeaderboardSortField) => {
        if (sortField !== field) return <span className="text-voxel-muted pl-1">↕</span>;
        return sortOrder === 'asc' ? (
            <span className="text-accent pl-1">▲</span>
        ) : (
            <span className="text-accent pl-1">▼</span>
        );
    };

    return (
        <Card variant="default" padding="md" className="scene-scrim flex flex-col gap-4 min-w-0">
            <div className="flex flex-wrap justify-between items-center gap-2">
                <h2 className="text-sm font-bold text-voxel-ink uppercase tracking-wider">
                    Standings{' '}
                    {isFetching ? (
                        <span className="text-xs font-normal text-voxel-muted font-mono">
                            (updating...)
                        </span>
                    ) : null}
                </h2>
            </div>
            <Table containerClassName="border-voxel-bevel-hi bg-voxel-trough">
                <TableHeader className="bg-voxel-surface border-b border-voxel-bevel-hi">
                    <TableRow isHoverable={false}>
                        <TableHead className="w-12 text-center">Compare</TableHead>
                        <TableHead className="w-16">Rank</TableHead>
                        <TableHead>Competitor</TableHead>
                        <TableHead
                            align="right"
                            className="cursor-pointer select-none hover:text-voxel-ink"
                            onClick={() => onSortChange('composite_score')}
                        >
                            Score {renderSortIndicator('composite_score')}
                        </TableHead>
                        <TableHead
                            align="right"
                            className="cursor-pointer select-none hover:text-voxel-ink"
                            onClick={() => onSortChange('return_pct')}
                        >
                            Return {renderSortIndicator('return_pct')}
                        </TableHead>
                        <TableHead
                            align="right"
                            className="cursor-pointer select-none hover:text-voxel-ink"
                            onClick={() => onSortChange('win_rate')}
                        >
                            Win Rate {renderSortIndicator('win_rate')}
                        </TableHead>
                        <TableHead
                            align="right"
                            className="cursor-pointer select-none hover:text-voxel-ink"
                            onClick={() => onSortChange('consistency_score')}
                        >
                            Up Days {renderSortIndicator('consistency_score')}
                        </TableHead>
                    </TableRow>
                </TableHeader>
                <TableBody className="divide-white/5">
                    {models.map((model, idx) => {
                        const isSelected = selectedModels.includes(model.model_name);
                        const isSelectionMaxed = selectedModels.length >= 2 && !isSelected;
                        const displayRank = model.rank ?? startIdx + idx + 1;

                        return (
                            <LeaderboardTableRow
                                key={model.model_name}
                                model={model}
                                originalRank={displayRank}
                                isSelected={isSelected}
                                isSelectionMaxed={isSelectionMaxed}
                                onToggleSelectModel={onToggleSelectModel}
                            />
                        );
                    })}
                </TableBody>
            </Table>

            <div className="flex flex-wrap items-center justify-between gap-4 min-w-0">
                <p className="text-xs font-normal text-voxel-muted font-mono">
                    {totalCount > 0 && models.length > 0
                        ? `Showing ${startIdx + 1}–${endIdx} of ${totalCount}`
                        : 'No competitors match this filter'}
                </p>

                {totalPages > 1 ? (
                    <nav
                        aria-label="Leaderboard pages"
                        className="flex flex-wrap items-center gap-2"
                    >
                        <Button
                            type="button"
                            size="sm"
                            variant="outline"
                            colorScheme="neutral"
                            aria-disabled={safePage <= 1}
                            onClick={() => {
                                if (safePage > 1) onPageChange(safePage - 1);
                            }}
                        >
                            ← Prev
                        </Button>
                        <span
                            role="status"
                            className="text-xs font-normal font-mono text-voxel-muted px-2"
                        >
                            Page {safePage} of {totalPages}
                        </span>
                        <Button
                            type="button"
                            size="sm"
                            variant="outline"
                            colorScheme="neutral"
                            aria-disabled={safePage >= totalPages}
                            onClick={() => {
                                if (safePage < totalPages) onPageChange(safePage + 1);
                            }}
                        >
                            Next →
                        </Button>
                    </nav>
                ) : null}

                {selectedModels.length < 2 ? (
                    <p className="text-xs font-normal text-voxel-muted font-mono italic ml-auto">
                        Select up to 2 competitors to run side-by-side diagnostics.
                    </p>
                ) : null}
            </div>
        </Card>
    );
}

interface LeaderboardTableRowProps {
    model: LLMLeaderboardRow;
    originalRank: number;
    isSelected: boolean;
    isSelectionMaxed: boolean;
    onToggleSelectModel: (modelName: string) => void;
}

function CompetitorCell({
    model,
    info,
}: {
    model: LLMLeaderboardRow;
    info: ReturnType<typeof getLeaderboardDisplayInfo>;
}) {
    const titleNode = model.recipe_id ? (
        <Link
            to="/recipes/$recipeId"
            params={{ recipeId: model.recipe_id }}
            className="font-bold text-voxel-ink text-sm hover:text-accent underline decoration-voxel-bevel-hi underline-offset-4 truncate"
        >
            {info.name}
        </Link>
    ) : model.portfolio_id ? (
        <Link
            to="/portfolios/$portfolioId"
            params={{ portfolioId: model.portfolio_id }}
            className="font-bold text-voxel-ink text-sm hover:text-accent underline decoration-voxel-bevel-hi underline-offset-4 truncate"
        >
            {info.name}
        </Link>
    ) : (
        <span className="font-bold text-voxel-ink text-sm truncate">{info.name}</span>
    );

    return (
        <div className="flex flex-col gap-0.5 min-w-0">
            <div className="flex flex-wrap items-center gap-2 min-w-0">
                <Badge colorScheme={info.badgeColor} variant="soft" size="xs">
                    {info.categoryLabel}
                </Badge>
                {titleNode}
            </div>
            <div className="text-xs font-normal text-voxel-muted font-mono tracking-wider truncate">
                {info.subtitle}
            </div>
        </div>
    );
}

function LeaderboardTableRow({
    model,
    originalRank,
    isSelected,
    isSelectionMaxed,
    onToggleSelectModel,
}: LeaderboardTableRowProps) {
    const info = getLeaderboardDisplayInfo(model);
    const badgeColor =
        originalRank === 1
            ? 'success'
            : originalRank === 2
              ? 'accent'
              : originalRank === 3
                ? 'warning'
                : 'neutral';

    return (
        <TableRow
            className={`transition-colors border-b border-voxel-bevel-lo ${isSelected ? 'bg-voxel-elevated' : ''}`}
        >
            <TableCell align="center">
                <input
                    type="checkbox"
                    aria-label={`Select ${info.name} for comparison`}
                    checked={isSelected}
                    disabled={isSelectionMaxed}
                    onChange={() => onToggleSelectModel(model.model_name)}
                    className="h-4.5 w-4.5 rounded-none border-zinc-700 bg-zinc-800 text-accent focus:ring-accent accent-accent-hover disabled:opacity-40 cursor-pointer disabled:cursor-not-allowed"
                />
            </TableCell>
            <TableCell className="font-mono tabular-nums">
                <Badge colorScheme={badgeColor} variant="soft" size="xs">
                    #{originalRank}
                </Badge>
            </TableCell>
            <TableCell className="min-w-0">
                <CompetitorCell model={model} info={info} />
            </TableCell>
            <TableCell align="right" className="font-mono tabular-nums">
                {model.composite_score.toFixed(1)}%
            </TableCell>
            <TableCell align="right" className="font-mono tabular-nums">
                <span className={model.return_pct >= 0 ? 'text-success' : 'text-danger'}>
                    {model.return_pct >= 0 ? '+' : ''}
                    {model.return_pct.toFixed(2)}%
                </span>
            </TableCell>
            <TableCell align="right" tone="muted" className="font-mono tabular-nums">
                {formatWinRate(model.win_rate)}
            </TableCell>
            <TableCell
                align="right"
                tone="muted"
                className="font-mono tabular-nums whitespace-nowrap"
            >
                {formatUpDays(model.up_days, model.active_days, model.consistency_score)}
            </TableCell>
        </TableRow>
    );
}
