import { Badge } from '@llm-market-bench/ui-design-system';
import type { ReactNode } from 'react';
import { QUIZ_TOTAL_QUESTION_LABEL, QUIZ_WORST_CASE } from './quiz-worst-case';

export const QUIZ_CARD_BASE_CLASS =
    'col-start-1 row-start-1 flex w-full max-w-2xl min-w-0 flex-col gap-4 rounded-none p-6';
export const QUIZ_HEADER_CLASS =
    'flex min-w-0 flex-wrap items-center justify-between gap-x-2 gap-y-1 border-b-2 border-voxel-bevel-hi pb-3';
export const QUIZ_CONTEXT_ROW_CLASS =
    'flex min-w-0 flex-wrap items-center justify-between gap-x-2 gap-y-1 text-xs font-normal text-voxel-muted';
export const QUIZ_PROMPT_CLASS =
    'font-display min-h-10 min-w-0 break-words text-sm font-bold leading-snug text-voxel-ink';
export const QUIZ_OPTION_BUTTON_CLASS =
    'h-auto w-full min-w-0 justify-start px-4 py-3 text-left whitespace-normal';
export const QUIZ_FOOTER_CLASS =
    'mt-auto flex min-w-0 flex-wrap items-center justify-between gap-x-2 gap-y-1 border-t-2 border-voxel-bevel-hi pt-3';

/**
 * Reserves one row of card copy. The hidden sizer and the live row share a
 * single grid cell, so the row is always as tall as the longest copy it can
 * ever show and every row below it starts at the same y on every question.
 */
export function QuizPinnedRow({
    testId,
    sizer,
    children,
}: {
    testId: string;
    sizer: ReactNode;
    children: ReactNode;
}) {
    return (
        <div className="grid min-w-0">
            <div
                data-testid={testId}
                aria-hidden="true"
                inert
                className="invisible col-start-1 row-start-1 min-w-0"
            >
                {sizer}
            </div>
            <div className="col-start-1 row-start-1 min-w-0">{children}</div>
        </div>
    );
}

/** Reserved header row: act badge, longest act title and longest live hint. */
export function QuizHeaderRowSizer({ totalActs }: { totalActs: number }) {
    return (
        <div className={QUIZ_HEADER_CLASS}>
            <div className="flex min-w-0 flex-wrap items-center gap-2">
                <Badge colorScheme="accent" variant="soft" size="sm">
                    {`Act ${String(totalActs)} of ${String(totalActs)}`}
                </Badge>
                <span className="min-w-0 break-words text-sm font-bold text-voxel-ink">
                    {QUIZ_WORST_CASE.actTitle}
                </span>
            </div>
            <span className="min-w-0 whitespace-nowrap text-xs font-normal text-voxel-muted">
                {QUIZ_WORST_CASE.liveHint}
            </span>
        </div>
    );
}

/** Reserved context row: act pips, longest context label and the final counter. */
export function QuizContextRowSizer({ totalActs }: { totalActs: number }) {
    return (
        <div className={QUIZ_CONTEXT_ROW_CLASS}>
            <div className="flex items-center gap-2">
                {Array.from({ length: totalActs }, (_, i) => (
                    <span
                        key={`ctx-sizer-pip-${String(i)}`}
                        className="h-2 w-4 border-2 border-transparent"
                    />
                ))}
            </div>
            <span className="flex min-w-0 flex-wrap items-baseline justify-end gap-x-2 gap-y-1">
                <span className="min-w-0 break-words">{QUIZ_WORST_CASE.context}</span>
                <span className="whitespace-nowrap">{QUIZ_TOTAL_QUESTION_LABEL}</span>
            </span>
        </div>
    );
}

/** Reserved prompt row: the longest prompt in the diagnostic. */
export function QuizPromptSizer() {
    return <div className={QUIZ_PROMPT_CLASS}>{QUIZ_WORST_CASE.prompt}</div>;
}
