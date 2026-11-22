import { Badge } from '@llm-market-bench/ui-design-system';
import type { ReactNode } from 'react';
import type { BuilderPhase, StatusTone } from './builder-phases';

interface StatusView {
    label: string;
    text: string;
    tone: StatusTone;
}

/** Past this mark the copy admits the provider is slow (one announcement, not a tick). */
const SLOW_AFTER_MS = 12_000;

function describe(phase: BuilderPhase, elapsedMs: number, detail?: string): StatusView {
    switch (phase) {
        case 'compiling':
            return {
                label: 'COMPILING',
                text:
                    detail ??
                    (elapsedMs >= SLOW_AFTER_MS
                        ? 'the free model is slow right now — still trying, and it falls back to a working template if it misses the deadline'
                        : 'asking the model, then validating the recipe'),
                tone: 'accent',
            };
        case 'signed-out':
            return {
                label: 'SIGN IN TO BUILD',
                text: 'Your idea is parked in this browser until you sign in.',
                tone: 'info',
            };
        case 'question':
            return {
                label: 'YOUR ANSWER NEEDED',
                text: 'One quick question — pick an option or reply in the box below.',
                tone: 'warning',
            };
        case 'declined':
            return {
                label: 'CANNOT RUN AS DESCRIBED',
                text: 'The nearest buildable version is shown above.',
                tone: 'warning',
            };
        case 'ready':
            return {
                label: 'BOT READY',
                text: detail ?? 'Compiled and editable — backtest it with paper cash.',
                tone: 'success',
            };
        case 'error':
            return {
                label: 'FAILED',
                text: detail ?? 'Nothing was queued. Try again, or rephrase the idea.',
                tone: 'danger',
            };
        default:
            return {
                label: 'READY',
                text: 'Describe the bot you want — one sentence is enough.',
                tone: 'neutral',
            };
    }
}

export interface BuilderStatusStripProps {
    phase: BuilderPhase;
    /** Ticking compile timer. Kept out of the live region so it is not announced. */
    elapsedMs?: number;
    /** Overrides the default line for the phase (draft state, run state, errors). */
    detail?: string;
    /** Overrides for non-builder background work, e.g. a queued backtest run. */
    label?: string;
    tone?: StatusTone;
    /** In-flow action for the row, e.g. a link to the run this line describes. */
    action?: ReactNode;
}

/**
 * Always-mounted status line for the builder. It is the single place that says
 * what the builder is doing — idle, compiling, waiting on the user, finished or
 * failed — so a long request never looks like a dead button.
 *
 * Only the label+text pair is a live region: the elapsed counter changes every
 * second, and a polite region would queue one announcement per tick.
 */
export function BuilderStatusStrip({
    phase,
    elapsedMs = 0,
    detail,
    label,
    tone,
    action,
}: BuilderStatusStripProps) {
    const defaults = describe(phase, elapsedMs, detail);
    const view: StatusView = {
        label: label ?? defaults.label,
        text: detail ?? defaults.text,
        tone: tone ?? defaults.tone,
    };
    const counter = phase === 'compiling' ? `${Math.max(1, Math.round(elapsedMs / 1000))}s` : null;

    return (
        <div
            data-testid="builder-status"
            className="voxel-trough bg-voxel-trough flex flex-wrap items-baseline gap-x-2 gap-y-1 p-3 min-w-0"
        >
            <Badge variant="soft" size="sm" colorScheme={view.tone} showDot>
                {view.label}
            </Badge>
            <span
                role="status"
                aria-live="polite"
                data-testid="builder-status-text"
                className="text-xs font-normal text-voxel-muted min-w-0 break-words"
            >
                {view.text}
            </span>
            {counter ? (
                <span
                    aria-hidden="true"
                    data-testid="builder-status-clock"
                    className="text-xs font-normal text-voxel-muted whitespace-nowrap"
                >
                    {counter}
                </span>
            ) : null}
            {action ? <span className="whitespace-nowrap">{action}</span> : null}
        </div>
    );
}
