import { Badge } from '@llm-market-bench/ui-design-system';
import { LIVE_ONLY_TOOL_NAMES, type RecipeJobRecord } from '../types';
import type { StatusTone } from './builder-phases';

export interface RunView {
    label: string;
    text: string;
    tone: StatusTone;
}

export function isInFlightRun(run: RecipeJobRecord | null): boolean {
    return run?.status === 'pending' || run?.status === 'processing';
}

export function describeRun(run: RecipeJobRecord | null): RunView | null {
    if (!run) return null;
    const progress =
        typeof run.progress_pct === 'number' ? `${Math.round(run.progress_pct)}%` : null;
    switch (run.status) {
        case 'pending':
            return {
                label: 'BACKTEST QUEUED',
                text: `Queued${progress ? ` · ${progress}` : ''} — a worker picks it up shortly. You can keep editing.`,
                tone: 'accent',
            };
        case 'processing':
            return {
                label: 'BACKTEST RUNNING',
                text: `Running${progress ? ` · ${progress}` : ''} — you can keep editing while it works.`,
                tone: 'accent',
            };
        case 'completed':
            return {
                label: 'LAST BACKTEST',
                text: 'Last backtest finished.',
                tone: 'success',
            };
        case 'failed':
            return {
                label: 'LAST BACKTEST',
                text: run.error_message
                    ? `Failed: ${run.error_message}`
                    : 'Failed — re-run it from My Bots.',
                tone: 'danger',
            };
        case 'cancelled':
            return { label: 'LAST BACKTEST', text: 'Cancelled.', tone: 'neutral' };
        default:
            return null;
    }
}

export type WorkspaceStatus =
    | {
          kind: 'prompt_needed';
          label: 'PROMPT NEEDED';
          tone: 'warning';
          detail: string;
          showLiveWarning: false;
          preferLive: false;
      }
    | {
          kind: 'run_in_flight';
          label: string | undefined;
          tone: StatusTone;
          detail: string;
          showLiveWarning: boolean;
          preferLive: boolean;
      }
    | {
          kind: 'live_active';
          label: 'LIVE ACTIVE';
          tone: 'success';
          detail: string;
          showLiveWarning: false;
          preferLive: false;
      }
    | {
          kind: 'fallback_template';
          label: 'CLOSEST WORKING TEMPLATE';
          tone: 'warning';
          detail: string;
          showLiveWarning: boolean;
          preferLive: boolean;
      }
    | {
          kind: 'live_recommended';
          label: 'LIVE RECOMMENDED';
          tone: 'warning';
          detail: string;
          showLiveWarning: true;
          preferLive: true;
      }
    | {
          kind: 'saved';
          label: 'SAVED BOT';
          tone: StatusTone;
          detail: string;
          showLiveWarning: false;
          preferLive: false;
      }
    | {
          kind: 'ready';
          label: undefined;
          tone: StatusTone;
          detail: string;
          showLiveWarning: false;
          preferLive: false;
      };

export function resolveLiveWarningMessage(
    warning: string | undefined,
    selectedTools: string[],
): string | null {
    const liveOnlyTools = selectedTools.filter((tool) => LIVE_ONLY_TOOL_NAMES.has(tool));
    const toolNote =
        liveOnlyTools.length > 0
            ? `Selected live-only tools (${liveOnlyTools.join(', ')}) are skipped in offline point-in-time backtests.`
            : null;
    const parts = [
        warning?.trim() || null,
        toolNote && !(warning && liveOnlyTools.every((t) => warning.includes(t))) ? toolNote : null,
    ].filter(Boolean);
    return parts.length > 0 ? parts.join(' ') : null;
}

export function deriveWorkspaceStatus(args: {
    hasEmptyPrompt: boolean;
    runInFlight: boolean;
    runView: RunView | null;
    isCurrentlyScheduledLive: boolean;
    fallback: boolean;
    hasLiveWarning: boolean;
    strategyId?: string;
    isDirty: boolean;
    statusDetail: string;
}): WorkspaceStatus {
    if (args.hasEmptyPrompt) {
        return {
            kind: 'prompt_needed',
            label: 'PROMPT NEEDED',
            tone: 'warning',
            detail: 'Prompt block cannot be empty — add strategy instructions in Blocks & Tools.',
            showLiveWarning: false,
            preferLive: false,
        };
    }
    if (args.runInFlight && args.runView) {
        const adviseLive = args.hasLiveWarning && !args.isCurrentlyScheduledLive;
        return {
            kind: 'run_in_flight',
            label: args.runView.label,
            tone: args.runView.tone,
            detail: args.statusDetail,
            showLiveWarning: adviseLive,
            preferLive: adviseLive,
        };
    }
    if (args.isCurrentlyScheduledLive) {
        return {
            kind: 'live_active',
            label: 'LIVE ACTIVE',
            tone: 'success',
            detail: args.statusDetail,
            showLiveWarning: false,
            preferLive: false,
        };
    }
    if (args.fallback) {
        return {
            kind: 'fallback_template',
            label: 'CLOSEST WORKING TEMPLATE',
            tone: 'warning',
            detail: args.statusDetail,
            showLiveWarning: args.hasLiveWarning,
            preferLive: args.hasLiveWarning,
        };
    }
    if (args.hasLiveWarning) {
        return {
            kind: 'live_recommended',
            label: 'LIVE RECOMMENDED',
            tone: 'warning',
            detail: args.statusDetail,
            showLiveWarning: true,
            preferLive: true,
        };
    }
    if (args.strategyId) {
        return {
            kind: 'saved',
            label: 'SAVED BOT',
            tone: args.isDirty ? 'neutral' : 'success',
            detail: args.statusDetail,
            showLiveWarning: false,
            preferLive: false,
        };
    }
    return {
        kind: 'ready',
        label: undefined,
        tone: args.isDirty ? 'neutral' : 'success',
        detail: args.statusDetail,
        showLiveWarning: false,
        preferLive: false,
    };
}

export function LiveWarningBanner({ show, message }: { show: boolean; message: string | null }) {
    if (!show || !message) return null;
    return (
        <div
            role="status"
            data-testid="compiled-bot-live-warning"
            className="voxel-trough bg-voxel-trough border border-warning/60 rounded-none p-3 flex flex-col gap-2 min-w-0"
        >
            <div className="flex flex-wrap items-center gap-2 min-w-0">
                <Badge colorScheme="warning" variant="soft" size="sm">
                    WARNING — RUN LIVE
                </Badge>
                <span className="text-xs font-normal text-voxel-muted">
                    Offline backtests only use point-in-time historical data.
                </span>
            </div>
            <p className="text-xs font-normal text-voxel-ink leading-relaxed break-words">
                {message}
            </p>
            <p className="text-xs font-normal text-voxel-muted break-words">
                Enable Live (30m) below to run this bot on live market data, or adjust its blocks
                and tools.
            </p>
        </div>
    );
}
