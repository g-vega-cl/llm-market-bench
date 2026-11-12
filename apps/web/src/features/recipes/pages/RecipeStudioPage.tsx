import { Badge, Button, PageLayout } from '@llm-market-bench/ui-design-system';
import { useState } from 'react';
import {
    enqueueRecipeJobFn,
    fetchRecipeAlertsFn,
    getRecipeJobStatusFn,
    markAlertReadFn,
    saveRecipeFn,
    submitWaitlistPledgeFn,
} from '../api/recipes-api';
import { RecipeAlertsInbox } from '../components/RecipeAlertsInbox';
import { RecipeBacktestResults } from '../components/RecipeBacktestResults';
import { RecipeFlowCanvas } from '../components/RecipeFlowCanvas';
import { WaitlistPledgeModal } from '../components/WaitlistPledgeModal';
import { STARTER_RECIPES } from '../starter-templates';
import type {
    BacktestResultData,
    RecipeAlert,
    RecipeCadence,
    RecipeGraph,
    StrategyRecipeRecord,
} from '../types';

async function pollJobResults(
    jobId: string,
    onComplete: (data: BacktestResultData) => void,
): Promise<void> {
    for (let attempts = 0; attempts < 6; attempts++) {
        await new Promise((r) => setTimeout(r, 1000));
        try {
            const res = await getRecipeJobStatusFn({ data: { jobId } });
            if (res?.status === 'completed' && res.result_json) {
                onComplete(res.result_json as BacktestResultData);
                return;
            }
            if (res?.status === 'failed') return;
        } catch {
            // Ignore transient network errors
        }
    }
}

export function RecipeStudioPage() {
    const [recipe, setRecipe] = useState<RecipeGraph>(STARTER_RECIPES[0]);
    const [activeTemplateIdx, setActiveTemplateIdx] = useState<number>(0);
    const [openRouterKey, setOpenRouterKey] = useState<string>('');
    const [openCodeKey, setOpenCodeKey] = useState<string>('');
    const [showKeyConfig, setShowKeyConfig] = useState<boolean>(false);

    const [isSimulating, setIsSimulating] = useState<boolean>(false);
    const [backtestResults, setBacktestResults] = useState<BacktestResultData | null>(null);

    const [alerts, setAlerts] = useState<RecipeAlert[]>([]);
    const [showAlertsInbox, setShowAlertsInbox] = useState<boolean>(false);
    const [showPledgeModal, setShowPledgeModal] = useState<boolean>(false);

    const handleSelectTemplate = (idx: number) => {
        setActiveTemplateIdx(idx);
        setRecipe(STARTER_RECIPES[idx]);
        setBacktestResults(null);
    };

    const handleCadenceChange = (cadence: RecipeCadence) => {
        setRecipe((prev) => ({ ...prev, cadence }));
    };

    const handleRunBacktest = async () => {
        setIsSimulating(true);
        try {
            const saved = (await saveRecipeFn({ data: { recipe } })) as StrategyRecipeRecord;
            const job = (await enqueueRecipeJobFn({
                data: {
                    recipeId: saved.id,
                    mode: 'backtest',
                    weeksRequested: ['2026-W09', '2026-W10'],
                    openRouterKey: openRouterKey || undefined,
                    openCodeKey: openCodeKey || undefined,
                },
            })) as { id: string; status: string; result_json?: BacktestResultData };

            if (job.result_json) {
                setBacktestResults(job.result_json);
            } else {
                await pollJobResults(job.id, setBacktestResults);
            }
        } finally {
            setIsSimulating(false);
        }
    };

    const handleLoadAlerts = async () => {
        try {
            const list = await fetchRecipeAlertsFn();
            setAlerts(list);
            setShowAlertsInbox(true);
        } catch {
            setShowAlertsInbox(true);
        }
    };

    const handleMarkAlertRead = async (alertId: string) => {
        try {
            await markAlertReadFn({ data: { alertId } });
            setAlerts((prev) => prev.map((a) => (a.id === alertId ? { ...a, is_read: true } : a)));
        } catch {
            // Handled
        }
    };

    const handlePledgeSubmit = async (email: string, tier: string, feedback: string) => {
        await submitWaitlistPledgeFn({
            data: { email, intendedTier: tier, feedback },
        });
    };

    return (
        <PageLayout>
            <div className="flex flex-col gap-6">
                {/* Header Section */}
                <div className="flex flex-wrap items-center justify-between gap-4 border-b border-border pb-4">
                    <div className="flex flex-col gap-1">
                        <div className="flex items-center gap-2">
                            <h1 className="font-display text-lg font-bold text-foreground">
                                Strategy Recipe Studio
                            </h1>
                            <Badge variant="outline" size="sm">
                                Voxel DAG v2.0
                            </Badge>
                        </div>
                        <p className="text-xs font-normal text-muted-foreground">
                            Compose visual trading recipes with news catalyst streams, technical
                            indicator gates, and LLM classifiers.
                        </p>
                    </div>

                    <div className="flex flex-wrap items-center gap-2">
                        <Button
                            size="sm"
                            variant="outline"
                            onClick={() => setShowPledgeModal(true)}
                        >
                            ★ Early Supporter Waitlist
                        </Button>
                        <Button size="sm" variant="outline" onClick={handleLoadAlerts}>
                            Alerts Inbox ({alerts.filter((a) => !a.is_read).length})
                        </Button>
                        <Button
                            size="sm"
                            variant="outline"
                            onClick={() => setShowKeyConfig((p) => !p)}
                        >
                            {openRouterKey ? 'BYO Key (Active)' : 'BYO API Key'}
                        </Button>
                        <Button size="sm" onClick={handleRunBacktest} disabled={isSimulating}>
                            {isSimulating ? 'Simulating...' : '▶ Run Simulation'}
                        </Button>
                    </div>
                </div>

                {/* BYO Key Box */}
                {showKeyConfig && (
                    <div className="flex flex-col gap-3 border border-border bg-boxel-surface p-4 rounded-none voxel-card">
                        <span className="font-display text-sm font-bold text-foreground">
                            BYO Model Inference Routing
                        </span>
                        <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,14rem),1fr))] gap-3">
                            <label className="flex flex-col gap-1 text-xs font-normal text-muted-foreground">
                                <span>OpenRouter API Key (Enables Jev)</span>
                                <input
                                    type="password"
                                    value={openRouterKey}
                                    onChange={(e) => setOpenRouterKey(e.target.value)}
                                    placeholder="sk-or-v1-..."
                                    className="border border-border bg-boxel-canvas p-2 text-xs font-mono text-foreground rounded-none"
                                />
                            </label>
                            <label className="flex flex-col gap-1 text-xs font-normal text-muted-foreground">
                                <span>OpenCode Key (Optional /free endpoint)</span>
                                <input
                                    type="password"
                                    value={openCodeKey}
                                    onChange={(e) => setOpenCodeKey(e.target.value)}
                                    placeholder="Free opencode token..."
                                    className="border border-border bg-boxel-canvas p-2 text-xs font-mono text-foreground rounded-none"
                                />
                            </label>
                        </div>
                        <div className="voxel-trough p-2 font-mono text-xs text-muted-foreground">
                            Free tier executes locally on our dedicated GPU queue (
                            <b className="text-foreground">auto-strata</b>). Adding an OpenRouter
                            key unlocks Jev Alpha Decisions classification.
                        </div>
                    </div>
                )}

                {/* Template Picker & Cadence Toggle */}
                <div className="flex flex-wrap items-center justify-between gap-3 border border-border bg-boxel-surface p-3 rounded-none voxel-card">
                    <div className="flex flex-wrap items-center gap-2">
                        <span className="text-xs font-bold text-muted-foreground">
                            Starter Recipes:
                        </span>
                        {STARTER_RECIPES.map((tmpl, idx) => (
                            <button
                                key={tmpl.name}
                                type="button"
                                onClick={() => handleSelectTemplate(idx)}
                                className={`px-2 py-1 text-xs font-bold rounded-none ${
                                    activeTemplateIdx === idx
                                        ? 'bg-primary text-primary-foreground'
                                        : 'bg-boxel-canvas text-muted-foreground hover:text-foreground'
                                }`}
                            >
                                {tmpl.name.split(' ')[0]}
                            </button>
                        ))}
                    </div>

                    <div className="flex items-center gap-2">
                        <span className="text-xs font-bold text-muted-foreground">Cadence:</span>
                        <button
                            type="button"
                            onClick={() => handleCadenceChange('5m')}
                            className={`px-2 py-1 text-xs font-bold rounded-none ${
                                recipe.cadence === '5m'
                                    ? 'bg-primary text-primary-foreground'
                                    : 'bg-boxel-canvas text-muted-foreground'
                            }`}
                        >
                            5-Minute Bars
                        </button>
                        <button
                            type="button"
                            onClick={() => handleCadenceChange('1d')}
                            className={`px-2 py-1 text-xs font-bold rounded-none ${
                                recipe.cadence === '1d'
                                    ? 'bg-primary text-primary-foreground'
                                    : 'bg-boxel-canvas text-muted-foreground'
                            }`}
                        >
                            1-Day Bars
                        </button>
                    </div>
                </div>

                {/* Recipe Canvas */}
                <RecipeFlowCanvas recipe={recipe} onChange={setRecipe} />

                {/* Backtest Results */}
                <RecipeBacktestResults results={backtestResults} isLoading={isSimulating} />

                {/* Alerts Inbox Drawer */}
                {showAlertsInbox && (
                    <RecipeAlertsInbox
                        alerts={alerts}
                        onMarkRead={handleMarkAlertRead}
                        onClose={() => setShowAlertsInbox(false)}
                    />
                )}

                {/* Waitlist Pledge Modal */}
                <WaitlistPledgeModal
                    isOpen={showPledgeModal}
                    onClose={() => setShowPledgeModal(false)}
                    onSubmit={handlePledgeSubmit}
                />
            </div>
        </PageLayout>
    );
}
