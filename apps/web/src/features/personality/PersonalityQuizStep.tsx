import { Badge, Button } from '@llm-market-bench/ui-design-system';
import type { QuizQuestion } from './personality-questions';

export interface PersonalityQuizStepProps {
    question: QuizQuestion;
    stepIndex: number;
    totalQuestions: number;
    chosenOptionId?: string;
    liveHint: string;
    onSelectOption: (questionId: string, optionId: string) => void;
    onPrevious: () => void;
    onBrowseAll: () => void;
}

/**
 * Interactive single-step diagnostic card inside `.scene-scrim .voxel-card`.
 * Uses at most two typography combos (`text-xs font-normal`, `text-sm font-bold`)
 * and one border style (`border-2`).
 */
export function PersonalityQuizStep({
    question,
    stepIndex,
    totalQuestions,
    chosenOptionId,
    liveHint,
    onSelectOption,
    onPrevious,
    onBrowseAll,
}: PersonalityQuizStepProps) {
    const progressPercent = Math.round(((stepIndex + 1) / totalQuestions) * 100);

    return (
        <div
            data-testid="personality-quiz-card"
            className="scene-scrim voxel-card flex w-full max-w-2xl flex-col gap-5 rounded-none p-6"
        >
            <div className="flex flex-wrap items-center justify-between gap-2 border-b-2 border-voxel-bevel-hi pb-3">
                <div className="flex items-center gap-2">
                    <Badge colorScheme="accent" variant="soft" size="sm">
                        {`Question ${String(stepIndex + 1).padStart(2, '0')} / ${totalQuestions}`}
                    </Badge>
                    <span className="text-xs font-normal text-voxel-muted">{question.context}</span>
                </div>
                <span
                    data-testid="quiz-live-world-hint"
                    className="text-xs font-normal text-voxel-muted"
                >
                    {liveHint || 'Scoring 4 trading axes'}
                </span>
            </div>

            <div
                role="progressbar"
                aria-valuenow={progressPercent}
                aria-valuemin={0}
                aria-valuemax={100}
                className="voxel-trough h-2 w-full overflow-hidden rounded-none"
            >
                <div
                    className="h-full bg-accent transition-all duration-200"
                    style={{ width: `${progressPercent}%` }}
                />
            </div>

            <h2 className="text-sm font-bold leading-snug text-voxel-ink">{question.prompt}</h2>

            <div className="grid grid-cols-1 gap-3">
                {question.options.map((option, optionIdx) => {
                    const selected = chosenOptionId === option.id;
                    return (
                        <Button
                            key={option.id}
                            type="button"
                            variant={selected ? 'solid' : 'outline'}
                            colorScheme={selected ? 'accent' : 'neutral'}
                            size="md"
                            data-testid={`quiz-option-${option.id}`}
                            onClick={() => onSelectOption(question.id, option.id)}
                            className="h-auto w-full justify-start px-4 py-3 text-left whitespace-normal"
                        >
                            <span className="flex flex-col items-start gap-1">
                                <span className="text-sm font-bold">
                                    {`${String.fromCharCode(65 + optionIdx)}. ${option.label}`}
                                </span>
                                <span className="text-xs font-normal text-voxel-muted">
                                    {option.detail}
                                </span>
                            </span>
                        </Button>
                    );
                })}
            </div>

            <div className="flex flex-wrap items-center justify-between gap-2 border-t-2 border-voxel-bevel-hi pt-3">
                <Button
                    type="button"
                    variant="outline"
                    colorScheme="neutral"
                    size="sm"
                    disabled={stepIndex === 0}
                    onClick={onPrevious}
                >
                    Previous question
                </Button>

                <Button
                    type="button"
                    variant="outline"
                    colorScheme="neutral"
                    size="sm"
                    data-testid="skip-to-all-archetypes"
                    onClick={onBrowseAll}
                >
                    Browse all 5 styles
                </Button>
            </div>
        </div>
    );
}
