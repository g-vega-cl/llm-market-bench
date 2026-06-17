import type { LLMLeaderboardRow } from '@llm-market-bench/database';
import {
    Badge,
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@llm-market-bench/ui-design-system';
import { useState } from 'react';
import { getModelDisplayInfo } from '../lib/model-helper';

interface LeaderboardTableProps {
    models: LLMLeaderboardRow[];
    selectedModels: string[];
    onToggleSelectModel: (modelName: string) => void;
}

type SortField =
    | 'composite_score'
    | 'return_pct'
    | 'win_rate'
    | 'verifier_approval_rate'
    | 'consistency_score';

type SortOrder = 'asc' | 'desc';

export function LeaderboardTable({
    models,
    selectedModels,
    onToggleSelectModel,
}: LeaderboardTableProps) {
    const [sortField, setSortField] = useState<SortField>('composite_score');
    const [sortOrder, setSortOrder] = useState<SortOrder>('desc');

    const handleSort = (field: SortField) => {
        if (sortField === field) {
            setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
        } else {
            setSortField(field);
            setSortOrder('desc');
        }
    };

    // Sort models on client side
    const sortedModels = [...models].sort((a, b) => {
        const valueA = a[sortField];
        const valueB = b[sortField];

        if (valueA < valueB) return sortOrder === 'asc' ? -1 : 1;
        if (valueA > valueB) return sortOrder === 'asc' ? 1 : -1;
        return 0;
    });

    const renderSortIndicator = (field: SortField) => {
        if (sortField !== field) return <span className="text-zinc-600 pl-1">↕</span>;
        return sortOrder === 'asc' ? (
            <span className="text-accent pl-1">▲</span>
        ) : (
            <span className="text-accent pl-1">▼</span>
        );
    };

    return (
        <div className="space-y-4 animate-slide-up" style={{ animationDelay: '100ms' }}>
            <Table containerClassName="border-white/10 dark:bg-zinc-950/40 backdrop-blur-md">
                <TableHeader className="bg-white/5 border-b border-white/10">
                    <TableRow isHoverable={false}>
                        <TableHead className="w-12 text-center">Compare</TableHead>
                        <TableHead className="w-16">Rank</TableHead>
                        <TableHead className="min-w-[180px]">Model</TableHead>
                        <TableHead
                            className="cursor-pointer select-none hover:text-white"
                            onClick={() => handleSort('composite_score')}
                        >
                            Score {renderSortIndicator('composite_score')}
                        </TableHead>
                        <TableHead
                            className="cursor-pointer select-none hover:text-white"
                            onClick={() => handleSort('return_pct')}
                        >
                            Return {renderSortIndicator('return_pct')}
                        </TableHead>
                        <TableHead
                            className="cursor-pointer select-none hover:text-white"
                            onClick={() => handleSort('win_rate')}
                        >
                            Win Rate {renderSortIndicator('win_rate')}
                        </TableHead>
                        <TableHead
                            className="cursor-pointer select-none hover:text-white"
                            onClick={() => handleSort('verifier_approval_rate')}
                        >
                            Approval {renderSortIndicator('verifier_approval_rate')}
                        </TableHead>
                        <TableHead
                            className="cursor-pointer select-none hover:text-white"
                            onClick={() => handleSort('consistency_score')}
                        >
                            Consistency {renderSortIndicator('consistency_score')}
                        </TableHead>
                    </TableRow>
                </TableHeader>
                <TableBody className="divide-white/5">
                    {sortedModels.map((model) => {
                        const isSelected = selectedModels.includes(model.model_name);
                        const isSelectionMaxed = selectedModels.length >= 2 && !isSelected;
                        const originalRank =
                            models.findIndex((m) => m.model_name === model.model_name) + 1;

                        return (
                            <LeaderboardTableRow
                                key={model.model_name}
                                model={model}
                                originalRank={originalRank}
                                isSelected={isSelected}
                                isSelectionMaxed={isSelectionMaxed}
                                onToggleSelectModel={onToggleSelectModel}
                            />
                        );
                    })}
                </TableBody>
            </Table>
            {selectedModels.length < 2 && (
                <p className="text-[11px] text-zinc-500 font-mono text-right italic">
                    Select up to 2 models to run side-by-side comparative diagnostics.
                </p>
            )}
        </div>
    );
}

interface LeaderboardTableRowProps {
    model: LLMLeaderboardRow;
    originalRank: number;
    isSelected: boolean;
    isSelectionMaxed: boolean;
    onToggleSelectModel: (modelName: string) => void;
}

function LeaderboardTableRow({
    model,
    originalRank,
    isSelected,
    isSelectionMaxed,
    onToggleSelectModel,
}: LeaderboardTableRowProps) {
    const info = getModelDisplayInfo(model.model_name);
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
            className={`transition-colors border-b border-white/5 ${isSelected ? 'bg-white/5' : ''}`}
        >
            <TableCell className="text-center">
                <input
                    type="checkbox"
                    checked={isSelected}
                    disabled={isSelectionMaxed}
                    onChange={() => onToggleSelectModel(model.model_name)}
                    className="h-4.5 w-4.5 rounded border-zinc-700 bg-zinc-800 text-accent focus:ring-accent accent-accent-hover disabled:opacity-40 cursor-pointer disabled:cursor-not-allowed"
                />
            </TableCell>
            <TableCell className="font-mono font-bold">
                <Badge colorScheme={badgeColor} variant="soft" size="xs">
                    #{originalRank}
                </Badge>
            </TableCell>
            <TableCell>
                <div className="flex items-center gap-2.5">
                    <span className="text-xl shrink-0">{info.emoji}</span>
                    <div className="truncate">
                        <div className="font-bold text-zinc-100 text-sm truncate">{info.name}</div>
                        <div className="text-[10px] text-zinc-500 font-mono tracking-wider truncate">
                            {model.model_name}
                        </div>
                    </div>
                </div>
            </TableCell>
            <TableCell className="font-mono font-black text-zinc-100 text-sm">
                {model.composite_score.toFixed(1)}%
            </TableCell>
            <TableCell className="font-mono font-bold text-sm">
                <span className={model.return_pct >= 0 ? 'text-success' : 'text-danger'}>
                    {model.return_pct >= 0 ? '+' : ''}
                    {model.return_pct.toFixed(2)}%
                </span>
            </TableCell>
            <TableCell className="font-mono text-zinc-300 text-sm">
                {model.win_rate.toFixed(1)}%
            </TableCell>
            <TableCell className="font-mono text-zinc-300 text-sm">
                {model.verifier_approval_rate.toFixed(1)}%
            </TableCell>
            <TableCell className="font-mono text-zinc-300 text-sm">
                {model.consistency_score.toFixed(1)}%
            </TableCell>
        </TableRow>
    );
}
