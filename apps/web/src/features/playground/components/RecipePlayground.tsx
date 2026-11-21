import { Input } from '@llm-market-bench/ui-design-system';
import { useRouter } from '@tanstack/react-router';
import { useState } from 'react';
import type { PushStrategy, StrategyStage } from '~/features/recipes/types';
import type { AnalyticsEvent } from '~/lib/analytics';
import { createStage, deriveTools } from '../lib/blocks';
import { launchDraft } from '../lib/launch';
import type { LaunchResult } from '../lib/launch-result';
import { SCENARIOS } from '../lib/scenarios';
import { BlockStack } from './BlockStack';
import { DescribeLine } from './DescribeLine';
import { RunRequestForm } from './RunRequestForm';
import { RunStrip } from './RunStrip';
import { ScenarioRow } from './ScenarioRow';

export interface RecipePlaygroundProps {
    isAuthenticated: boolean;
    runsLeft: number | null;
    email?: string;
    onEvent?: (event: AnalyticsEvent, props?: Record<string, unknown>) => void;
}

export function RecipePlayground({
    isAuthenticated,
    runsLeft,
    email,
    onEvent,
}: RecipePlaygroundProps) {
    const router = useRouter();
    const [stage, setStage] = useState<StrategyStage>(() => createStage());
    const [name, setName] = useState('My first bot');
    const [scenarioId, setScenarioId] = useState<string | null>(null);
    const [live, setLive] = useState(false);
    const [busy, setBusy] = useState(false);
    const [result, setResult] = useState<LaunchResult | null>(null);

    const adopt = (strategy: PushStrategy, scenario: string | null) => {
        const next = strategy.stages[0];
        setStage({ id: next.id, blocks: next.blocks, selected_tools: next.selected_tools });
        setName(strategy.name.slice(0, 40));
        setScenarioId(scenario);
        setResult(null);
    };

    const run = async () => {
        if (busy) return;
        if (!isAuthenticated) {
            await router.navigate({ to: '/login', search: { redirect: '/' } });
            return;
        }
        setBusy(true);
        setResult(null);
        const launched = await launchDraft(stage, name, live);
        setResult(launched);
        if (launched.kind !== 'error' && launched.kind !== 'invalid') {
            onEvent?.(launched.kind === 'blocked' ? 'playground_run_blocked' : 'playground_run', {
                kind: launched.kind,
                live,
                ...(launched.kind === 'blocked' ? { reason: launched.reason } : {}),
            });
        }
        if (launched.kind === 'error' && launched.needsAuth) {
            await router.navigate({ to: '/login', search: { redirect: '/' } });
        }
        if (launched.kind === 'backtest' || launched.kind === 'live-only') {
            await router.invalidate();
        }
        setBusy(false);
    };

    const outOfRuns =
        runsLeft === 0 || (result?.kind === 'blocked' && result.reason === 'daily-cap');

    return (
        <div className="flex flex-col gap-4 min-w-0">
            <div className="flex flex-wrap items-end gap-3">
                <div className="flex-1 basis-64 min-w-0 flex flex-col gap-1">
                    <span className="text-xs font-normal text-voxel-muted">Name this bot</span>
                    <Input
                        aria-label="Bot name"
                        value={name}
                        maxLength={40}
                        onChange={(event) => setName(event.target.value)}
                    />
                </div>
                <DescribeLine
                    isAuthenticated={isAuthenticated}
                    disabled={busy}
                    onCompiled={(strategy, summary, fallback) => {
                        adopt(strategy, null);
                        onEvent?.('playground_describe_used', {
                            fallback,
                            summaryLength: summary.length,
                        });
                        if (fallback) onEvent?.('playground_describe_failed', {});
                    }}
                    onFailed={(reason) => onEvent?.('describe_it_failed', { reason })}
                />
            </div>

            <BlockStack
                stage={stage}
                onChange={(next) => {
                    setStage(next);
                    setScenarioId(null);
                    setResult(null);
                }}
            />
            <ScenarioRow
                scenarios={SCENARIOS}
                activeId={scenarioId}
                onPick={(scenario) => {
                    adopt(scenario.strategy, scenario.id);
                    onEvent?.('playground_preset_applied', { scenario: scenario.id });
                }}
            />

            <RunStrip
                tools={
                    stage.selected_tools.length ? stage.selected_tools : deriveTools(stage.blocks)
                }
                live={live}
                onLiveChange={setLive}
                busy={busy}
                result={result}
                onRun={run}
                isAuthenticated={isAuthenticated}
                runsLeft={runsLeft}
            />

            {outOfRuns ? (
                <RunRequestForm isAuthenticated={isAuthenticated} defaultEmail={email} />
            ) : null}
        </div>
    );
}
