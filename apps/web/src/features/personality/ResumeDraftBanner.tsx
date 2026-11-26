import { Button } from '@llm-market-bench/ui-design-system';
import { PERSONALITY_QUESTIONS } from './personality-questions';
import { QUESTIONS_PER_ACT, type QuizDraft } from './quiz-session-helpers';

/**
 * Deferred localStorage resume trough rendered below the active quiz card per
 * `.agents/rules/design-spec.md` §4b.2 so returning users never experience
 * post-hydration layout shifts above the active question.
 */
export function ResumeDraftBanner({
    draft,
    onResume,
    onDismiss,
}: {
    draft: QuizDraft;
    onResume: () => void;
    onDismiss: () => void;
}) {
    const draftActNumber = Math.floor(draft.stepIndex / QUESTIONS_PER_ACT) + 1;
    return (
        <div
            data-testid="resume-quiz"
            className="scene-scrim voxel-trough flex w-full max-w-2xl min-w-0 flex-col gap-2 rounded-none p-4"
        >
            <p className="text-sm font-bold text-voxel-ink">
                {`You left off in Act ${String(draftActNumber)}`}
            </p>
            <p className="text-xs font-normal text-voxel-muted">
                {`${String(Object.keys(draft.answers).length)} of ${String(
                    PERSONALITY_QUESTIONS.length,
                )} answers saved on this device.`}
            </p>
            <div className="flex flex-wrap gap-2">
                <Button
                    type="button"
                    size="sm"
                    variant="solid"
                    colorScheme="accent"
                    data-testid="resume-quiz-button"
                    onClick={onResume}
                >
                    {`Resume Act ${String(draftActNumber)}`}
                </Button>
                <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    colorScheme="neutral"
                    onClick={onDismiss}
                >
                    Start over
                </Button>
            </div>
        </div>
    );
}
