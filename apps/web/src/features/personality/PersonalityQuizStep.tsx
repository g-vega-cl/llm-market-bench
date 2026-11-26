import { Badge, Button } from '@llm-market-bench/ui-design-system';
import type { QuizQuestion } from './personality-questions';
import {
    QUIZ_CARD_BASE_CLASS,
    QUIZ_CONTEXT_ROW_CLASS,
    QUIZ_FOOTER_CLASS,
    QUIZ_HEADER_CLASS,
    QUIZ_OPTION_BUTTON_CLASS,
    QUIZ_PROMPT_CLASS,
    QuizContextRowSizer,
    QuizHeaderRowSizer,
    QuizPinnedRow,
    QuizPromptSizer,
} from './quiz-card-rows';

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
    onSelectOption: (questionId: string, optionId: string) => void;
    onPrevious: () => void;
    onBrowseAll: () => void;
}

/**
 * Recessed Act-4 free-text trough rendered below the active quiz card so the
 * optional words never displace question options or pad Acts 1–3.
 */
export function QuizSelfDescriptionTrough({
    selfDescription,
    onChange,
}: {
    selfDescription: string;
    onChange: (value: string) => void;
}) {
    return (
        <div className="scene-scrim voxel-trough flex w-full max-w-2xl min-w-0 flex-col gap-2 rounded-none p-4">
            <div className="flex min-w-0 flex-wrap items-baseline justify-between gap-x-2 gap-y-1">
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
                onChange={(event) => onChange(event.target.value)}
                className="h-14 w-full min-w-0 resize-none border-2 border-voxel-bevel-lo bg-voxel-surface p-2 text-xs font-normal text-voxel-ink outline-none focus:border-accent"
            />
        </div>
    );
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
    onSelectOption,
    onPrevious,
    onBrowseAll,
}: PersonalityQuizStepProps) {
    const progressPercent = Math.round(((stepIndex + 1) / totalQuestions) * 100);

    return (
        <div
            data-testid="personality-quiz-card"
            className={`scene-scrim voxel-card h-full ${QUIZ_CARD_BASE_CLASS}`}
        >
            <QuizPinnedRow
                testId="quiz-row-sizer-header"
                sizer={<QuizHeaderRowSizer totalActs={totalActs} />}
            >
                <div className={QUIZ_HEADER_CLASS}>
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
                        className="min-w-0 whitespace-nowrap text-xs font-normal text-voxel-muted"
                    >
                        {liveHint || 'Scoring 4 trading axes'}
                    </span>
                </div>
            </QuizPinnedRow>

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

            <QuizPinnedRow
                testId="quiz-row-sizer-context"
                sizer={<QuizContextRowSizer totalActs={totalActs} />}
            >
                <div className={QUIZ_CONTEXT_ROW_CLASS}>
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
                    <span className="flex min-w-0 flex-wrap items-baseline justify-end gap-x-2 gap-y-1">
                        <span className="min-w-0 break-words">{question.context}</span>
                        <span className="whitespace-nowrap">
                            {`Question ${String(stepIndex + 1).padStart(2, '0')} / ${totalQuestions}`}
                        </span>
                    </span>
                </div>
            </QuizPinnedRow>

            <QuizPinnedRow testId="quiz-row-sizer-prompt" sizer={<QuizPromptSizer />}>
                <h2 className={QUIZ_PROMPT_CLASS}>{question.prompt}</h2>
            </QuizPinnedRow>

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
                            className={QUIZ_OPTION_BUTTON_CLASS}
                        >
                            <span className="flex min-w-0 flex-col items-start gap-2">
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

            <div className={QUIZ_FOOTER_CLASS}>
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
