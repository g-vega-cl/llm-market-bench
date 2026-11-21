import { Button } from '@llm-market-bench/ui-design-system';
import { Link } from '@tanstack/react-router';
import { type LaunchResult, launchMessage } from '../lib/launch-result';

export interface RunStripProps {
    tools: string[];
    live: boolean;
    onLiveChange: (live: boolean) => void;
    busy: boolean;
    result: LaunchResult | null;
    onRun: () => void;
    isAuthenticated: boolean;
    runsLeft: number | null;
}

function ResultLine({ result }: { result: LaunchResult }) {
    const tone =
        result.kind === 'blocked' || result.kind === 'invalid' || result.kind === 'error'
            ? 'text-danger'
            : 'text-voxel-ink';
    return (
        <div className="flex flex-col gap-1" role="status" aria-live="polite">
            <p className={`text-xs font-normal ${tone}`}>{launchMessage(result)}</p>
            {'recipeId' in result && result.recipeId ? (
                <Link
                    to="/recipes"
                    search={{ recipeId: result.recipeId }}
                    className="text-xs font-normal text-accent hover:underline"
                >
                    Open the bot and its receipts →
                </Link>
            ) : null}
        </div>
    );
}

/**
 * The one action. Disclosure sits above the button, not behind a tooltip:
 * the bot is public the moment it runs, prompt included.
 */
export function RunStrip({
    tools,
    live,
    onLiveChange,
    busy,
    result,
    onRun,
    isAuthenticated,
    runsLeft,
}: RunStripProps) {
    const label = busy ? 'Running…' : isAuthenticated ? 'Run backtest' : 'Sign in to run';

    return (
        <section aria-label="Run the bot" className="voxel-trough flex flex-col gap-3 p-3 min-w-0">
            <p className="text-xs font-normal text-voxel-muted">
                Running saves this bot and starts a backtest. Tick below to put it on the public
                desk — live bots, prompts and all, are public. Paper cash only.
            </p>

            <div className="flex flex-wrap items-center gap-3">
                <Button variant="solid" size="md" disabled={busy} onClick={onRun}>
                    {label}
                </Button>

                <label className="flex items-center gap-2 text-xs font-normal text-voxel-muted">
                    <input
                        type="checkbox"
                        checked={live}
                        onChange={(event) => onLiveChange(event.target.checked)}
                    />
                    Also go live at the next slot
                </label>

                {runsLeft !== null ? (
                    <span className="font-mono text-xs font-normal text-voxel-muted">
                        {runsLeft} {runsLeft === 1 ? 'run' : 'runs'} left today
                    </span>
                ) : null}
            </div>

            <p className="font-mono text-xs font-normal text-voxel-muted break-words">
                Tools it may call: {tools.length > 0 ? tools.join(', ') : 'none yet'}
            </p>

            {result ? <ResultLine result={result} /> : null}
        </section>
    );
}
