import { QUIZ_ACTS } from './personality-questions';
import {
    QUIZ_CARD_BASE_CLASS,
    QUIZ_FOOTER_CLASS,
    QUIZ_OPTION_BUTTON_CLASS,
    QuizContextRowSizer,
    QuizHeaderRowSizer,
    QuizPromptSizer,
} from './quiz-card-rows';
import { QUIZ_WORST_CASE } from './quiz-worst-case';

/**
 * Single non-interactive upper-bound sizer sharing layout constants with
 * `PersonalityQuizStep` so every question and `ActCheckpointPlaque` hold
 * identical card height at every container width with zero CLS.
 *
 * Its header, context and prompt rows are the same reserved rows the live card
 * renders, so the sizer and the pinned card agree pixel for pixel.
 */
export function QuizStepHeightSizer() {
    return (
        <div
            data-testid="quiz-height-sizer"
            aria-hidden="true"
            inert
            className={`pointer-events-none invisible border-2 border-transparent select-none ${QUIZ_CARD_BASE_CLASS}`}
        >
            <QuizHeaderRowSizer totalActs={QUIZ_ACTS.length} />

            <div className="voxel-trough h-2 w-full overflow-hidden rounded-none" />

            <QuizContextRowSizer totalActs={QUIZ_ACTS.length} />

            <QuizPromptSizer />

            <div className="grid grid-cols-1 gap-4">
                {QUIZ_WORST_CASE.options.map((option, optionIdx) => (
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
