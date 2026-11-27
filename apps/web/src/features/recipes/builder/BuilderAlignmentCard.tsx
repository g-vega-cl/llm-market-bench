import { Badge, Button } from '@llm-market-bench/ui-design-system';
import { useState } from 'react';
import type { AlignmentQuestion } from './compiler';

export const MAX_CUSTOM_ALIGNMENT_CHARS = 120;

export interface AlignmentAnswerEntry {
    question: string;
    answer: string;
}

export interface BuilderAlignmentCardProps {
    intro?: string;
    questions: AlignmentQuestion[];
    isCompiling: boolean;
    onSubmit: (answers: AlignmentAnswerEntry[]) => void;
    onSkip: () => void;
}

interface AnswerSelection {
    value: string;
    source: 'option' | 'custom';
}

/** Badge fill that survives the card's own selected state. */
function badgeTone(isRecommended: boolean, isSelected: boolean): string {
    if (!isRecommended) return '';
    return isSelected ? 'bg-voxel-trough text-accent' : 'bg-accent text-voxel-trough';
}

interface AlignmentOptionCardProps {
    option: string;
    isSelected: boolean;
    isRecommended: boolean;
    isCompiling: boolean;
    onSelect: () => void;
}

/**
 * One option card. Every card reserves the same leading badge slot and pins the
 * same height, so a badged card cannot sit wider, taller or off-centre from its
 * siblings.
 */
function AlignmentOptionCard({
    option,
    isSelected,
    isRecommended,
    isCompiling,
    onSelect,
}: AlignmentOptionCardProps) {
    return (
        <Button
            type="button"
            size="sm"
            variant={isSelected ? 'solid' : 'outline'}
            colorScheme={isSelected ? 'accent' : 'neutral'}
            aria-pressed={isSelected}
            disabled={isCompiling}
            onClick={onSelect}
            className="relative h-14 w-full min-w-0 text-center"
        >
            <span
                aria-hidden="true"
                className={`flex size-4 shrink-0 items-center justify-center text-xs font-normal leading-none ${badgeTone(isRecommended, isSelected)}`}
            >
                {isRecommended ? 'R' : ''}
            </span>
            <span className="min-w-0 break-words text-xs font-normal leading-snug line-clamp-2">
                {option}
                {isRecommended ? <span className="sr-only">, recommended</span> : null}
            </span>
        </Button>
    );
}

/**
 * Step 2 of /build: presents one focused round of 3-5 tailored multiple-choice
 * questions so the user can align on strategy choices before compiling the final bot.
 */
export function BuilderAlignmentCard({
    intro,
    questions,
    isCompiling,
    onSubmit,
    onSkip,
}: BuilderAlignmentCardProps) {
    const [selections, setSelections] = useState<Record<string, AnswerSelection>>({});

    const answeredCount = questions.filter((q) => Boolean(selections[q.id]?.value.trim())).length;
    const allAnswered = questions.length > 0 && answeredCount === questions.length;

    const selectOption = (questionId: string, option: string) => {
        setSelections((prev) => ({ ...prev, [questionId]: { value: option, source: 'option' } }));
    };

    const setCustomAnswer = (questionId: string, text: string) => {
        setSelections((prev) => ({
            ...prev,
            [questionId]: {
                value: text.slice(0, MAX_CUSTOM_ALIGNMENT_CHARS),
                source: 'custom',
            },
        }));
    };

    const handleSubmit = () => {
        if (!allAnswered || isCompiling) return;
        const entries: AlignmentAnswerEntry[] = questions.map((q) => ({
            question: q.question,
            answer: (selections[q.id]?.value ?? '').trim(),
        }));
        onSubmit(entries);
    };

    return (
        <div data-testid="builder-alignment-card" className="flex flex-col gap-4 min-w-0">
            <div className="flex flex-wrap items-center justify-between gap-2 min-w-0">
                <p className="text-sm font-bold text-voxel-ink min-w-0 break-words">
                    {intro || 'Quick alignment before we compile your bot'}
                </p>
                <div className="flex items-center gap-2">
                    <span className="text-xs font-normal text-voxel-ink">R = our pick</span>
                    <Badge
                        variant="soft"
                        size="sm"
                        colorScheme={allAnswered ? 'success' : 'accent'}
                    >
                        {`${String(answeredCount)} / ${String(questions.length)} answered`}
                    </Badge>
                </div>
            </div>

            <div className="flex flex-col gap-3 min-w-0">
                {questions.map((q, idx) => {
                    const entry = selections[q.id];
                    const selectedOption = entry?.source === 'option' ? entry.value : null;
                    const customValue = entry?.source === 'custom' ? entry.value : '';
                    // The card trusts the parser, but a reply that reaches it without
                    // a usable index still marks exactly one option rather than none.
                    const recommendedIndex =
                        q.recommended >= 1 && q.recommended <= q.options.length ? q.recommended : 1;

                    return (
                        <fieldset
                            key={q.id}
                            data-testid={`alignment-question-${idx + 1}`}
                            className="voxel-trough bg-voxel-trough rounded-none border-0 p-4 m-0 min-w-0 flex flex-col gap-3"
                        >
                            <legend className="flex flex-wrap items-baseline gap-2 min-w-0 w-full p-0">
                                <Badge variant="soft" size="xs" colorScheme="neutral">
                                    {`Q${String(idx + 1)}`}
                                </Badge>
                                <span className="text-sm font-bold text-voxel-ink min-w-0 break-words">
                                    {q.question}
                                </span>
                            </legend>

                            {/* Fixed four-column grid (two on phones) with a fixed card
                                height: every card in a row is the same size, whatever the
                                option count or label length. */}
                            <div
                                data-testid={`alignment-options-${String(idx + 1)}`}
                                className="grid grid-cols-2 sm:grid-cols-4 gap-2 items-stretch min-w-0"
                            >
                                {q.options.map((option, optionIndex) => (
                                    <AlignmentOptionCard
                                        key={`${q.id}-${option}`}
                                        option={option}
                                        isSelected={selectedOption === option}
                                        isRecommended={recommendedIndex === optionIndex + 1}
                                        isCompiling={isCompiling}
                                        onSelect={() => selectOption(q.id, option)}
                                    />
                                ))}
                            </div>

                            <input
                                type="text"
                                maxLength={MAX_CUSTOM_ALIGNMENT_CHARS}
                                aria-label={`Custom answer for question ${String(idx + 1)}`}
                                value={customValue}
                                onChange={(event) => setCustomAnswer(q.id, event.target.value)}
                                disabled={isCompiling}
                                placeholder="Or type your own preference..."
                                className="w-full border border-voxel-bevel-hi bg-voxel-surface px-3 py-2 text-xs font-normal text-voxel-ink placeholder:text-voxel-muted rounded-none focus:outline-none focus:ring-2 focus:ring-accent/40"
                            />
                        </fieldset>
                    );
                })}
            </div>

            <div className="flex flex-wrap items-center justify-between gap-4 min-w-0">
                <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    colorScheme="neutral"
                    disabled={isCompiling}
                    onClick={onSkip}
                >
                    Skip &amp; build with defaults
                </Button>

                <Button
                    type="button"
                    size="md"
                    variant="solid"
                    colorScheme="accent"
                    className="voxel-btn--hero"
                    disabled={!allAnswered}
                    isLoading={isCompiling}
                    onClick={handleSubmit}
                >
                    Build Final Bot →
                </Button>
            </div>
        </div>
    );
}
