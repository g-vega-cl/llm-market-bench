import { QUIZ_ACTS } from './personality-questions';
import {
    QUIZ_CARD_BASE_CLASS,
    QUIZ_FOOTER_CLASS,
    QUIZ_OPTIONS_GRID_CLASS,
    QuizContextRowSizer,
    QuizHeaderRowSizer,
    QuizOptionRowSizers,
    QuizPromptSizer,
} from './quiz-card-rows';

/**
 * Single non-interactive upper-bound sizer sharing layout constants with
 * `PersonalityQuizStep` so every question and `ActCheckpointPlaque` hold
 * identical card height at every container width with zero CLS.
 *
 * Its header, context, prompt and four answer rows are the same reserved rows
 * the live card renders, so the sizer and the pinned card agree pixel for
 * pixel — including the shared worst-case answer every option row reserves.
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

            <div className={QUIZ_OPTIONS_GRID_CLASS}>
                <QuizOptionRowSizers />
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
