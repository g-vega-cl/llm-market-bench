/** Lifecycle phases of the /build conversation, one discrete value per state. */
export type BuilderPhase =
    | 'idle'
    | 'signed-out'
    | 'queued'
    | 'compiling'
    | 'align'
    | 'question'
    | 'declined'
    | 'ready'
    | 'error';

/** Tones the status strip may use; matches the DS Badge `colorScheme` set. */
export type StatusTone = 'accent' | 'success' | 'danger' | 'info' | 'warning' | 'neutral';
