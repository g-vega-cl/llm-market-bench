import { Badge, Button } from '@llm-market-bench/ui-design-system';
import type { QuizQuestion } from './personality-questions';

export interface PersonalityQuizStepProps {
    question: QuizQuestion;
    stepIndex: number;
    totalQuestions: number;
    /** Act this question belongs to (1-indexed display, 0-indexed `actIndex`). */
    actTitle: string;
    actIndex: number;
    totalActs: number;
    chosenOptionId?: string;
    liveHint: string;
    /** Act 4 carries the optional free-text field. */
    showSelfDescription: boolean;
    selfDescription: string;
    onSelfDescriptionChange: (value: string) => void;
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
    actTitle,
    actIndex,
    totalActs,
    chosenOptionId,
    liveHint,
    showSelfDescription,
    selfDescription,
    onSelfDescriptionChange,
    onSelectOption,
    onPrevious,
    onBrowseAll,
}: PersonalityQuizStepProps) {
    const progressPercent = Math.round(((stepIndex + 1) / totalQuestions) * 100);

    return (
        <div
            data-testid="personality-quiz-card"
            className="scene-scrim voxel-card flex w-full max-w-2xl flex-col gap-4 rounded-none p-6"
        >
            <div className="flex min-w-0 flex-wrap items-center justify-between gap-2 border-b-2 border-voxel-bevel-hi pb-3">
                <div className="flex min-w-0 flex-wrap items-center gap-2">
                    <Badge colorScheme="accent" variant="soft" size="sm">
                        {`Act ${actIndex + 1} of ${totalActs}`}
                    </Badge>
                    <span className="min-w-0 break-words text-sm font-bold text-voxel-ink">
                        {actTitle}
                    </span>
                </div>
                <span
                    data-testid="quiz-live-world-hint"
                    className="min-w-0 break-words text-xs font-normal text-voxel-muted"
                >
                    {liveHint || 'Scoring 4 trading axes'}
                </span>
            </div>

            <div
                role="progressbar"
                aria-label="Diagnostic quiz progress"
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

            <div className="flex min-w-0 flex-wrap items-center justify-between gap-2 text-xs font-normal text-voxel-muted">
                <div
                    data-testid="quiz-act-track"
                    aria-hidden="true"
                    className="flex items-center gap-2"
                >
                    {Array.from({ length: totalActs }, (_, i) => (
                        <span
                            key={`act-pip-${String(i)}`}
                            className={
                                i < actIndex
                                    ? 'h-2 w-4 border-2 border-voxel-bevel-lo bg-accent'
                                    : i === actIndex
                                      ? 'h-2 w-4 border-2 border-accent bg-voxel-elevated'
                                      : 'h-2 w-4 border-2 border-voxel-bevel-lo bg-voxel-trough'
                            }
                        />
                    ))}
                </div>
                <span className="flex min-w-0 flex-wrap items-baseline justify-end gap-2">
                    <span className="min-w-0 break-words">{question.context}</span>
                    <span className="whitespace-nowrap">
                        {`Question ${String(stepIndex + 1).padStart(2, '0')} / ${totalQuestions}`}
                    </span>
                </span>
            </div>

            <h2 className="text-sm font-bold leading-snug text-voxel-ink">{question.prompt}</h2>

            {showSelfDescription ? (
                <div className="voxel-trough flex min-w-0 flex-col gap-2 rounded-none p-3">
                    <div className="flex min-w-0 flex-wrap items-baseline justify-between gap-2">
                        <label
                            htmlFor="personality-self-description"
                            className="min-w-0 break-words text-xs font-normal text-voxel-muted"
                        >
                            In your own words — anything you want the bot to be like (optional):
                        </label>
                        <span className="min-w-0 whitespace-nowrap text-xs font-normal text-voxel-muted">
                            {`${String(selfDescription.length)} / 180`}
                        </span>
                    </div>
                    <textarea
                        id="personality-self-description"
                        data-testid="quiz-self-description"
                        rows={2}
                        maxLength={180}
                        value={selfDescription}
                        onChange={(event) => onSelfDescriptionChange(event.target.value)}
                        className="w-full min-w-0 resize-none border-2 border-voxel-bevel-lo bg-voxel-surface p-2 text-xs font-normal text-voxel-ink outline-none focus:border-accent"
                    />
                </div>
            ) : null}

            <div className="grid grid-cols-1 gap-4">
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
                            <span className="flex flex-col items-start gap-2">
                                <span className="text-sm font-bold">
                                    {`${String.fromCharCode(65 + optionIdx)}. ${option.label}`}
                                </span>
                                <span
                                    className={
                                        selected
                                            ? 'text-xs font-normal'
                                            : 'text-xs font-normal text-voxel-muted'
                                    }
                                >
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
                    Browse all 16 types
                </Button>
            </div>
        </div>
    );
}
