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

function formatStableDate(dateStr: string): string {
    if (!dateStr) return 'N/A';
    const parts = dateStr.split('T')[0].split('-');
    if (parts.length === 3) {
        const year = parts[0];
        const monthStr = parts[1];
        const dayStr = parts[2];
        const months = [
            'Jan',
            'Feb',
            'Mar',
            'Apr',
            'May',
            'Jun',
            'Jul',
            'Aug',
            'Sep',
            'Oct',
            'Nov',
            'Dec',
        ];
        const monthIndex = parseInt(monthStr, 10) - 1;
        if (monthIndex >= 0 && monthIndex < 12) {
            const day = parseInt(dayStr, 10);
            return `${months[monthIndex]} ${day}, ${year}`;
        }
    }
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
        timeZone: 'America/New_York',
        month: 'short',
        day: 'numeric',
        year: 'numeric',
    });
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
                                <div className="flex items-center gap-2">
                                    <span>{exp.variant_tag}</span>
                                    {(exp.research_output as { selected_tools?: string[] })
                                        ?.selected_tools && (
                                        <Badge
                                            colorScheme="accent"
                                            variant="outline"
                                            className="text-[9px] px-1.5 py-0 font-sans tracking-wide"
                                        >
                                            🛠️ Pull
                                        </Badge>
                                    )}
                                </div>
                            </TableCell>
                            <TableCell>
                                <Badge
                                    variant={exp.experiment_type === 'baseline' ? 'solid' : 'soft'}
                                >
                                    {exp.experiment_type}
                                </Badge>
                            </TableCell>
                            <TableCell
                                className={`font-bold ${
                                    score === 'N/A'
                                        ? 'text-zinc-400 dark:text-zinc-500 font-medium'
                                        : Number(score) > 0
                                          ? 'text-emerald-600'
                                          : 'text-rose-600'
                                }`}
                            >
                                {score}
                            </TableCell>
                            <TableCell className="text-zinc-500 text-sm">
                                {formatStableDate(exp.week_start)} -{' '}
                                {formatStableDate(exp.week_end)}
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
        case 'baseline':
            return (
                <Badge colorScheme="accent" variant="soft">
                    Baseline
                </Badge>
            );
        case 'saved':
        case 'kept':
            return (
                <Badge colorScheme="neutral" variant="soft">
                    Saved
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
