import { Badge, Button } from '@llm-market-bench/ui-design-system';
import { useState } from 'react';
import type { ConditionRule, DAGNode, JSONObject, JSONValue } from '../types';

interface BlockConfigureModalProps {
    node: DAGNode | null;
    isOpen: boolean;
    onClose: () => void;
    onSave: (updatedNode: DAGNode) => void;
}

const NEWS_BUCKETS = [
    { id: 'semiconductors', label: 'Semiconductors (NVDA, AMD, TSM)' },
    { id: 'ai_cloud', label: 'AI & Cloud Hyperscalers' },
    { id: 'fed_rates', label: 'Federal Reserve & Rates' },
    { id: 'earnings', label: 'Quarterly Earnings & Guidance' },
    { id: 'macro_inflation', label: 'CPI, Inflation & Jobs' },
    { id: 'energy', label: 'Crude Oil & Energy' },
    { id: 'financials', label: 'Banking & Financials' },
    { id: 'tariffs_trade', label: 'Tariffs & Trade War' },
    { id: 'general_market', label: 'General Market Catalysts' },
];

const TECHNICAL_METRICS = [
    { id: 'price', label: 'Price (Close)' },
    { id: 'rsi_14', label: 'RSI (14 Period)' },
    { id: 'vwap', label: 'Session VWAP' },
    { id: 'sma_20', label: 'SMA 20' },
    { id: 'sma_50', label: 'SMA 50' },
    { id: 'rvol', label: 'Relative Volume (RVOL)' },
];

function NewsConfigForm({
    config,
    onUpdate,
}: {
    config: JSONObject;
    onUpdate: (k: string, v: JSONValue) => void;
}) {
    return (
        <div className="flex flex-col gap-3">
            <label className="flex flex-col gap-1 text-xs font-normal text-muted-foreground">
                <span>Thematic News Bucket</span>
                <select
                    value={String(config.bucket || 'general_market')}
                    onChange={(e) => onUpdate('bucket', e.target.value)}
                    className="border border-border bg-boxel-canvas p-2 text-sm font-bold text-foreground rounded-none"
                >
                    {NEWS_BUCKETS.map((b) => (
                        <option key={b.id} value={b.id}>
                            {b.label}
                        </option>
                    ))}
                </select>
            </label>
            <label className="flex flex-col gap-1 text-xs font-normal text-muted-foreground">
                <span>Catalyst Lookback Window (Hours)</span>
                <input
                    type="number"
                    value={Number(config.lookback_hours || 48)}
                    onChange={(e) => onUpdate('lookback_hours', Number(e.target.value))}
                    className="border border-border bg-boxel-canvas p-2 text-sm font-bold text-foreground rounded-none"
                />
            </label>
        </div>
    );
}

function TechnicalGateConfigForm({
    config,
    onUpdate,
}: {
    config: JSONObject;
    onUpdate: (k: string, v: JSONValue) => void;
}) {
    const conditions = (config.conditions as unknown as ConditionRule[]) || [];

    const handleUpdateRule = (idx: number, patch: Partial<ConditionRule>) => {
        const next = [...conditions];
        next[idx] = { ...next[idx], ...patch };
        onUpdate('conditions', next as unknown as JSONValue);
    };

    const handleRemoveRule = (idx: number) => {
        const next = [...conditions];
        next.splice(idx, 1);
        onUpdate('conditions', next as unknown as JSONValue);
    };

    const handleAddRule = () => {
        onUpdate('conditions', [
            ...conditions,
            { metric: 'price', operator: '>', target: 'vwap' },
        ] as unknown as JSONValue);
    };

    return (
        <div className="flex flex-col gap-3">
            <span className="text-xs font-normal text-muted-foreground">
                Technical Conditions (All Must Pass)
            </span>
            <div className="flex flex-col gap-2">
                {conditions.map((cond, idx) => (
                    <div
                        key={`${cond.metric}-${cond.operator}-${cond.target}`}
                        className="flex items-center gap-2 border border-border bg-boxel-canvas p-2 rounded-none"
                    >
                        <select
                            value={cond.metric}
                            onChange={(e) => handleUpdateRule(idx, { metric: e.target.value })}
                            className="border border-border bg-boxel-surface p-1 text-xs font-bold text-foreground"
                        >
                            {TECHNICAL_METRICS.map((m) => (
                                <option key={m.id} value={m.id}>
                                    {m.label}
                                </option>
                            ))}
                        </select>
                        <select
                            value={cond.operator}
                            onChange={(e) =>
                                handleUpdateRule(idx, {
                                    operator: e.target.value as ConditionRule['operator'],
                                })
                            }
                            className="border border-border bg-boxel-surface p-1 text-xs font-bold text-foreground"
                        >
                            <option value=">">&gt;</option>
                            <option value="<">&lt;</option>
                            <option value=">=">&gt;=</option>
                            <option value="<=">&lt;=</option>
                            <option value="==">==</option>
                        </select>
                        <input
                            type="text"
                            value={String(cond.target)}
                            onChange={(e) => handleUpdateRule(idx, { target: e.target.value })}
                            placeholder="Target"
                            className="flex-1 border border-border bg-boxel-surface p-1 text-xs font-bold text-foreground"
                        />
                        <button
                            type="button"
                            onClick={() => handleRemoveRule(idx)}
                            className="px-2 text-xs font-bold text-red-400 hover:text-red-300"
                        >
                            ✕
                        </button>
                    </div>
                ))}
            </div>
            <Button size="sm" variant="outline" onClick={handleAddRule}>
                + Add Condition Rule
            </Button>
        </div>
    );
}

function ClassificationConfigForm({
    config,
    onUpdate,
}: {
    config: JSONObject;
    onUpdate: (k: string, v: JSONValue) => void;
}) {
    return (
        <div className="flex flex-col gap-3">
            <label className="flex flex-col gap-1 text-xs font-normal text-muted-foreground">
                <span>Inference Model</span>
                <select
                    value={String(config.model || '~typesafe/jev-latest')}
                    onChange={(e) => onUpdate('model', e.target.value)}
                    className="border border-border bg-boxel-canvas p-2 text-sm font-bold text-foreground rounded-none"
                >
                    <option value="~typesafe/jev-latest">
                        Jev (Alpha Decisions API via OpenRouter)
                    </option>
                    <option value="auto-strata">Local Auto-Strata (Free Tier Queue)</option>
                </select>
            </label>
            <label className="flex flex-col gap-1 text-xs font-normal text-muted-foreground">
                <span>Target Decision Choice</span>
                <select
                    value={String(config.target_choice || 'BULLISH')}
                    onChange={(e) => onUpdate('target_choice', e.target.value)}
                    className="border border-border bg-boxel-canvas p-2 text-sm font-bold text-foreground rounded-none"
                >
                    <option value="BULLISH">BULLISH</option>
                    <option value="BEARISH">BEARISH</option>
                    <option value="NEUTRAL">NEUTRAL</option>
                </select>
            </label>
            <label className="flex flex-col gap-1 text-xs font-normal text-muted-foreground">
                <span>Minimum Confidence (%)</span>
                <input
                    type="number"
                    min="50"
                    max="100"
                    value={Number(config.min_confidence || 70)}
                    onChange={(e) => onUpdate('min_confidence', Number(e.target.value))}
                    className="border border-border bg-boxel-canvas p-2 text-sm font-bold text-foreground rounded-none"
                />
            </label>
        </div>
    );
}

function RiskConfigForm({
    config,
    onUpdate,
}: {
    config: JSONObject;
    onUpdate: (k: string, v: JSONValue) => void;
}) {
    return (
        <div className="grid grid-cols-2 gap-3">
            <label className="flex flex-col gap-1 text-xs font-normal text-muted-foreground">
                <span>Order Action</span>
                <select
                    value={String(config.action || 'BUY')}
                    onChange={(e) => onUpdate('action', e.target.value)}
                    className="border border-border bg-boxel-canvas p-2 text-sm font-bold text-foreground rounded-none"
                >
                    <option value="BUY">BUY (Long)</option>
                    <option value="SELL">SELL (Short)</option>
                </select>
            </label>
            <label className="flex flex-col gap-1 text-xs font-normal text-muted-foreground">
                <span>Stop Loss (%)</span>
                <input
                    type="number"
                    step="0.1"
                    value={Number(config.stop_loss_pct || 1.5)}
                    onChange={(e) => onUpdate('stop_loss_pct', Number(e.target.value))}
                    className="border border-border bg-boxel-canvas p-2 text-sm font-bold text-foreground rounded-none"
                />
            </label>
            <label className="flex flex-col gap-1 text-xs font-normal text-muted-foreground">
                <span>Target Profit (%)</span>
                <input
                    type="number"
                    step="0.1"
                    value={Number(config.target_profit_pct || 3.0)}
                    onChange={(e) => onUpdate('target_profit_pct', Number(e.target.value))}
                    className="border border-border bg-boxel-canvas p-2 text-sm font-bold text-foreground rounded-none"
                />
            </label>
            <label className="flex flex-col gap-1 text-xs font-normal text-muted-foreground">
                <span>Max Holding Bars</span>
                <input
                    type="number"
                    value={Number(config.max_hold_bars || 12)}
                    onChange={(e) => onUpdate('max_hold_bars', Number(e.target.value))}
                    className="border border-border bg-boxel-canvas p-2 text-sm font-bold text-foreground rounded-none"
                />
            </label>
        </div>
    );
}

export function BlockConfigureModal({ node, isOpen, onClose, onSave }: BlockConfigureModalProps) {
    const [title, setTitle] = useState(node?.title || '');
    const [config, setConfig] = useState<JSONObject>({ ...(node?.config || {}) });

    if (!isOpen || !node) return null;

    const handleSave = () => {
        onSave({ ...node, title, config });
        onClose();
    };

    const updateConfig = (key: string, value: JSONValue) => {
        setConfig((prev) => ({ ...prev, [key]: value }));
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
            <div className="flex w-full max-w-xl flex-col gap-4 border border-border bg-boxel-surface p-6 rounded-none voxel-card">
                <div className="flex items-center justify-between border-b border-border pb-3">
                    <div className="flex items-center gap-2">
                        <span className="font-display text-lg font-bold text-foreground">
                            Configure Block
                        </span>
                        <Badge variant="outline" size="sm">
                            {node.type}
                        </Badge>
                    </div>
                    <button
                        type="button"
                        onClick={onClose}
                        className="text-xs font-bold text-muted-foreground hover:text-foreground"
                    >
                        ✕
                    </button>
                </div>

                <div className="flex flex-col gap-4">
                    <label className="flex flex-col gap-1 text-xs font-normal text-muted-foreground">
                        <span>Block Title</span>
                        <input
                            type="text"
                            value={title}
                            onChange={(e) => setTitle(e.target.value)}
                            className="border border-border bg-boxel-canvas p-2 text-sm font-bold text-foreground rounded-none focus:outline-none"
                        />
                    </label>

                    {node.type === 'news_source' && (
                        <NewsConfigForm config={config} onUpdate={updateConfig} />
                    )}
                    {node.type === 'technical_gate' && (
                        <TechnicalGateConfigForm config={config} onUpdate={updateConfig} />
                    )}
                    {node.type === 'classification' && (
                        <ClassificationConfigForm config={config} onUpdate={updateConfig} />
                    )}
                    {node.type === 'risk_output' && (
                        <RiskConfigForm config={config} onUpdate={updateConfig} />
                    )}
                </div>

                <div className="flex justify-end gap-2 border-t border-border pt-3">
                    <Button variant="ghost" size="sm" onClick={onClose}>
                        Cancel
                    </Button>
                    <Button size="sm" onClick={handleSave}>
                        Apply Changes
                    </Button>
                </div>
            </div>
        </div>
    );
}
