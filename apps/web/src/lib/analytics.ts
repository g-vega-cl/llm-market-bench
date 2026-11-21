/**
 * Named analytics events. Autocapture already gives pageviews and clicks; these
 * are the outcome events a funnel needs, because element text is not a funnel.
 */
export type AnalyticsEvent =
    | 'recipe_forked'
    | 'run_queued'
    | 'builder_opened'
    | 'builder_compiled'
    | 'builder_question_answered'
    | 'builder_declined'
    | 'gallery_signin_clicked'
    | 'playground_run'
    | 'playground_run_blocked'
    | 'playground_preset_applied'
    | 'playground_describe_used'
    | 'playground_describe_failed'
    | 'describe_it_failed';

type CaptureClient =
    | {
          capture?: (event: string, props?: Record<string, unknown>) => void;
      }
    | null
    | undefined;

/** No-op without a client, so server renders and tests never throw. */
export function track(
    client: CaptureClient,
    event: AnalyticsEvent,
    props?: Record<string, unknown>,
): void {
    client?.capture?.(event, props);
}
