import {
    QUIZ_CARD_BASE_CLASS,
    QUIZ_CONTEXT_ROW_CLASS,
    QUIZ_FOOTER_CLASS,
    QUIZ_HEADER_CLASS,
    QUIZ_OPTION_BUTTON_CLASS,
    QUIZ_PROMPT_CLASS,
} from './PersonalityQuizStep';
import { PERSONALITY_QUESTIONS, QUIZ_ACTS } from './personality-questions';

function longestBy(values: string[]): string {
    return values.reduce((best, value) => (value.length > best.length ? value : best), '');
}

const WORST_CASE_SIZER = {
    actTitle: longestBy(QUIZ_ACTS.map((act) => act.title)),
    context: longestBy(PERSONALITY_QUESTIONS.map((q) => q.context)),
    prompt: longestBy(PERSONALITY_QUESTIONS.map((q) => q.prompt)),
    options: [0, 1, 2, 3].map((slot) => ({
        label: longestBy(PERSONALITY_QUESTIONS.map((q) => q.options[slot]?.label ?? '')),
        detail: longestBy(PERSONALITY_QUESTIONS.map((q) => q.options[slot]?.detail ?? '')),
    })),
};

/**
 * Single non-interactive upper-bound sizer sharing layout constants with
 * `PersonalityQuizStep` so every question and `ActCheckpointPlaque` hold
 * identical card height at every container width with zero CLS.
 */
export function QuizStepHeightSizer() {
    return (
        <div
            data-testid="quiz-height-sizer"
            aria-hidden="true"
            inert
            className={`pointer-events-none invisible border-2 border-transparent select-none ${QUIZ_CARD_BASE_CLASS}`}
        >
            <div className={QUIZ_HEADER_CLASS}>
                <div className="flex min-w-0 flex-wrap items-center gap-2">
                    <span className="voxel-badge inline-flex items-center gap-1.5 rounded-none px-2 py-0.5 text-sm font-bold uppercase tracking-wider">
                        {`Act ${String(QUIZ_ACTS.length)} of ${String(QUIZ_ACTS.length)}`}
                    </span>
                    <span className="min-w-0 break-words text-sm font-bold">
                        {WORST_CASE_SIZER.actTitle}
                    </span>
                </div>
                <span className="min-w-0 whitespace-nowrap text-xs font-normal">
                    Scoring 4 trading axes
                </span>
            </div>

            <div className="voxel-trough h-2 w-full overflow-hidden rounded-none" />

            <div className={QUIZ_CONTEXT_ROW_CLASS}>
                <div className="flex items-center gap-2">
                    {QUIZ_ACTS.map((act) => (
                        <span key={act.axis} className="h-2 w-4 border-2 border-transparent" />
                    ))}
                </div>
                <span className="flex min-w-0 flex-wrap items-baseline justify-end gap-x-2 gap-y-1">
                    <span className="min-w-0 break-words">{WORST_CASE_SIZER.context}</span>
                    <span className="whitespace-nowrap">
                        {`Question ${String(PERSONALITY_QUESTIONS.length).padStart(2, '0')} / ${String(PERSONALITY_QUESTIONS.length)}`}
                    </span>
                </span>
            </div>

            <div className={QUIZ_PROMPT_CLASS}>{WORST_CASE_SIZER.prompt}</div>

            <div className="grid grid-cols-1 gap-4">
                {WORST_CASE_SIZER.options.map((option, optionIdx) => (
                    <div
                        key={`sizer-opt-${String(optionIdx)}`}
                        className={`voxel-btn inline-flex items-center gap-2 text-sm font-bold ${QUIZ_OPTION_BUTTON_CLASS}`}
                    >
                        <span className="flex min-w-0 flex-col items-start gap-2">
                            <span className="text-sm font-bold">
                                {`${String.fromCharCode(65 + optionIdx)}. ${option.label}`}
                            </span>
                            <span className="text-xs font-normal">{option.detail}</span>
                        </span>
                    </div>
                ))}
            </div>

            <div className={QUIZ_FOOTER_CLASS}>
                <span className="voxel-btn inline-flex items-center justify-center gap-2 px-3 py-1.5 text-sm font-bold">
                    Previous question
                </span>
                <span className="voxel-btn inline-flex items-center justify-center gap-2 px-3 py-1.5 text-sm font-bold">
                    Browse all 16 types
                </span>
            </div>
        </div>
    );
}
