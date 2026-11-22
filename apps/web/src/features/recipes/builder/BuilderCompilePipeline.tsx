import { Badge } from '@llm-market-bench/ui-design-system';
import type { BuilderPhase } from './builder-phases';

export interface BuilderCompilePipelineProps {
    phase: Extract<BuilderPhase, 'queued' | 'compiling'>;
}

type StepState = 'done' | 'active' | 'pending';

interface PipelineStep {
    id: string;
    label: string;
    detail: string;
    state: StepState;
}

function resolveSteps(phase: Extract<BuilderPhase, 'queued' | 'compiling'>): PipelineStep[] {
    if (phase === 'queued') {
        return [
            { id: 'queue', label: '1. Queue', detail: 'Waiting for worker', state: 'active' },
            { id: 'model', label: '2. Model', detail: 'Drafting strategy', state: 'pending' },
            {
                id: 'validate',
                label: '3. Validate',
                detail: 'Runs when reply arrives',
                state: 'pending',
            },
        ];
    }
    return [
        { id: 'queue', label: '1. Queue', detail: 'Claimed by worker', state: 'done' },
        { id: 'model', label: '2. Model', detail: 'Drafting strategy', state: 'active' },
        {
            id: 'validate',
            label: '3. Validate',
            detail: 'Runs when reply arrives',
            state: 'pending',
        },
    ];
}

function stepScheme(state: StepState): 'success' | 'accent' | 'neutral' {
    if (state === 'done') return 'success';
    if (state === 'active') return 'accent';
    return 'neutral';
}

function stepBorderClass(state: StepState): string {
    if (state === 'done') return 'border-success/60';
    if (state === 'active') return 'border-accent';
    return 'border-voxel-bevel-hi';
}

/**
 * Honest Voxel pipeline visualization driven strictly by real queue/compile
 * lifecycle state (`queued` -> `compiling`), with no client-timed milestone guessing.
 */
export function BuilderCompilePipeline({ phase }: BuilderCompilePipelineProps) {
    const steps = resolveSteps(phase);

    return (
        <div
            data-testid="builder-compile-pipeline"
            className="voxel-trough bg-voxel-trough rounded-none p-3 flex flex-col gap-2 min-w-0"
        >
            <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,10rem),1fr))] gap-2 items-stretch">
                {steps.map((step) => (
                    <div
                        key={step.id}
                        data-step-state={step.state}
                        className={`border bg-voxel-surface rounded-none p-2 flex flex-col justify-between gap-2 min-w-0 ${stepBorderClass(step.state)}`}
                    >
                        <div className="flex flex-wrap items-center justify-between gap-2">
                            <span className="text-sm font-bold text-voxel-ink">{step.label}</span>
                            <Badge
                                variant="soft"
                                size="xs"
                                colorScheme={stepScheme(step.state)}
                                showDot={step.state === 'active'}
                            >
                                {step.state === 'done'
                                    ? 'DONE'
                                    : step.state === 'active'
                                      ? 'ACTIVE'
                                      : 'NEXT'}
                            </Badge>
                        </div>
                        <span className="text-xs font-normal text-voxel-muted break-words">
                            {step.detail}
                        </span>
                    </div>
                ))}
            </div>
        </div>
    );
}
