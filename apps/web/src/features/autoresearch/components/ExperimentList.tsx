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
                <Badge colorScheme="success" variant="soft">
                    Active
                </Badge>
            );
        case 'kept':
            return (
                <Badge colorScheme="info" variant="soft">
                    Kept
                </Badge>
            );
        case 'discarded':
            return (
                <Badge colorScheme="neutral" variant="soft">
                    Discarded
                </Badge>
            );
        case 'crashed':
            return (
                <Badge colorScheme="danger" variant="soft">
                    Crashed
                </Badge>
            );
        default:
            return <Badge>{status}</Badge>;
    }
}
