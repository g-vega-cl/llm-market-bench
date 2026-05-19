import type { PromptExperiment } from '@llm-market-bench/database';
import {
    Badge,
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@llm-market-bench/ui-design-system';

interface ExperimentListProps {
    experiments: PromptExperiment[];
    onSelect: (experiment: PromptExperiment) => void;
    selectedId?: string;
}

export function ExperimentList({ experiments, onSelect, selectedId }: ExperimentListProps) {
    return (
        <Table>
            <TableHeader>
                <TableRow isHoverable={false}>
                    <TableHead>Variant</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Score</TableHead>
                    <TableHead>Period</TableHead>
                    <TableHead>Status</TableHead>
                </TableRow>
            </TableHeader>
            <TableBody>
                {experiments.map((exp) => {
                    const score = exp.metrics?.score ?? 'N/A';
                    const isSelected = selectedId === exp.id;

                    return (
                        <TableRow
                            key={exp.id}
                            onClick={() => onSelect(exp)}
                            className={
                                isSelected ? 'bg-zinc-100 dark:bg-zinc-800' : 'cursor-pointer'
                            }
                        >
                            <TableCell className="font-mono font-medium">
                                {exp.variant_tag}
                            </TableCell>
                            <TableCell>
                                <Badge
                                    variant={exp.experiment_type === 'baseline' ? 'solid' : 'soft'}
                                >
                                    {exp.experiment_type}
                                </Badge>
                            </TableCell>
                            <TableCell
                                className={`font-bold ${Number(score) > 0 ? 'text-emerald-600' : 'text-rose-600'}`}
                            >
                                {score}
                            </TableCell>
                            <TableCell className="text-zinc-500 text-sm">
                                {new Date(exp.week_start).toLocaleDateString()} -{' '}
                                {new Date(exp.week_end).toLocaleDateString()}
                            </TableCell>
                            <TableCell>
                                <StatusBadge status={exp.status} />
                            </TableCell>
                        </TableRow>
                    );
                })}
            </TableBody>
        </Table>
    );
}

function StatusBadge({ status }: { status: string }) {
    switch (status) {
        case 'active':
            return (
                <Badge className="bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400 border-emerald-200">
                    Active
                </Badge>
            );
        case 'kept':
            return (
                <Badge className="bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400 border-blue-200">
                    Kept
                </Badge>
            );
        case 'discarded':
            return (
                <Badge className="bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400 border-zinc-200">
                    Discarded
                </Badge>
            );
        case 'crashed':
            return (
                <Badge className="bg-rose-100 text-rose-800 dark:bg-rose-900/30 dark:text-rose-400 border-rose-200">
                    Crashed
                </Badge>
            );
        default:
            return <Badge>{status}</Badge>;
    }
}
