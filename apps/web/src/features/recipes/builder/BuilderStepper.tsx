import { Badge } from '@llm-market-bench/ui-design-system';

export type BuilderStepNumber = 1 | 2 | 3;

export interface BuilderStepperProps {
    activeStep: BuilderStepNumber;
}

type StepVisualState = 'done' | 'active' | 'upcoming';

interface StepDef {
    num: BuilderStepNumber;
    title: string;
    subtitle: string;
}

const STEPS: readonly StepDef[] = [
    { num: 1, title: '1. Describe', subtitle: 'Your strategy in plain English' },
    { num: 2, title: '2. Align', subtitle: '3–5 quick multiple-choice picks' },
    { num: 3, title: '3. Backtest & Go Live', subtitle: 'Test on paper cash, then switch Live' },
];

const STEP_VIEW: Record<
    StepVisualState,
    { borderClass: string; badgeColor: 'success' | 'accent' | 'neutral'; badgeLabel: string }
> = {
    done: { borderClass: 'border-success/60', badgeColor: 'success', badgeLabel: 'DONE' },
    active: { borderClass: 'border-accent', badgeColor: 'accent', badgeLabel: 'NOW' },
    upcoming: {
        borderClass: 'border-voxel-bevel-hi',
        badgeColor: 'neutral',
        badgeLabel: 'NEXT',
    },
};

function resolveStepState(
    stepNum: BuilderStepNumber,
    activeStep: BuilderStepNumber,
): StepVisualState {
    if (stepNum < activeStep) return 'done';
    if (stepNum === activeStep) return 'active';
    return 'upcoming';
}

/**
 * Unified 3-step progress bar across all /build phases so users always know
 * where they are and what happens next.
 */
export function BuilderStepper({ activeStep }: BuilderStepperProps) {
    return (
        <nav
            aria-label="Bot builder progress"
            data-testid="builder-stepper"
            className="build-stepper voxel-trough bg-voxel-trough rounded-none p-2 grid grid-cols-[repeat(3,minmax(0,1fr))] gap-1.5 items-stretch min-w-0"
        >
            {STEPS.map((step) => {
                const state = resolveStepState(step.num, activeStep);
                const view = STEP_VIEW[state];

                return (
                    <div
                        key={step.num}
                        data-step-number={step.num}
                        data-step-state={state}
                        aria-current={state === 'active' ? 'step' : undefined}
                        className={`border bg-voxel-surface rounded-none p-1.5 flex flex-col justify-between gap-1 min-w-0 ${view.borderClass}`}
                    >
                        <div className="flex flex-wrap items-center justify-between gap-2 min-w-0">
                            <span className="text-sm font-bold text-voxel-ink">{step.title}</span>
                            <Badge
                                variant="soft"
                                size="xs"
                                colorScheme={view.badgeColor}
                                showDot={state === 'active'}
                            >
                                {view.badgeLabel}
                            </Badge>
                        </div>
                        <span className="build-step-subtitle text-xs font-normal text-voxel-muted break-words">
                            {step.subtitle}
                        </span>
                    </div>
                );
            })}
        </nav>
    );
}
