/**
 * Named analytics events. Autocapture already gives pageviews and clicks; these
 * are the outcome events a funnel needs, because element text is not a funnel.
 */
export type AnalyticsEvent =
    | 'recipe_forked'
    | 'run_queued'
    | 'builder_opened'
    | 'builder_alignment_shown'
    | 'builder_compiled'
    | 'builder_failed'
    | 'builder_question_answered'
    | 'builder_declined'
    | 'bot_activated'
    | 'gallery_signin_clicked'
    | 'quiz_started'
    | 'quiz_question_answered'
    | 'quiz_act_completed'
    | 'quiz_completed';

type CaptureClient =
    | {
          __loaded?: boolean;
          capture?: (event: string, props?: Record<string, unknown>) => void;
      }
    | null
    | undefined;

const ACTIVATION_SESSION_KEY = 'benchify:bot-activated';

/**
 * Activation is defined as "queued a backtest for a compiled bot". The first
 * `run_queued` in a browser session also emits `bot_activated`, which gives
 * PostHog a single stable event for the activation funnel.
 */
function captureActivationOnce(client: CaptureClient, props?: Record<string, unknown>): void {
    if (typeof window === 'undefined') return;
    try {
        if (window.sessionStorage.getItem(ACTIVATION_SESSION_KEY)) return;
        window.sessionStorage.setItem(ACTIVATION_SESSION_KEY, '1');
    } catch {
        return;
    }
    client?.capture?.('bot_activated', { ...props, source: 'backtest_queued' });
}

/** No-op without a client, so server renders and tests never throw. */
export function track(
    client: CaptureClient,
    event: AnalyticsEvent,
    props?: Record<string, unknown>,
): void {
    if (client?.__loaded === false) return;
    client?.capture?.(event, props);
    if (event === 'run_queued') captureActivationOnce(client, props);
}
