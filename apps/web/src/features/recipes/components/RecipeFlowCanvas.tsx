import { Badge, Button } from '@llm-market-bench/ui-design-system';
import { useState } from 'react';
import type { DAGNode, JSONObject, NodeType, RecipeGraph } from '../types';
import { BlockConfigureModal } from './BlockConfigureModal';

interface RecipeFlowCanvasProps {
    recipe: RecipeGraph;
    onChange: (updated: RecipeGraph) => void;
}

const NODE_TYPE_COLORS: Record<NodeType, { badge: string; border: string }> = {
    news_source: { badge: 'bg-blue-900/60 text-blue-200', border: 'border-blue-700/50' },
    price_tape: { badge: 'bg-emerald-900/60 text-emerald-200', border: 'border-emerald-700/50' },
    technical_gate: { badge: 'bg-amber-900/60 text-amber-200', border: 'border-amber-700/50' },
    classification: { badge: 'bg-purple-900/60 text-purple-200', border: 'border-purple-700/50' },
    generative_analyst: { badge: 'bg-cyan-900/60 text-cyan-200', border: 'border-cyan-700/50' },
    risk_output: { badge: 'bg-red-900/60 text-red-200', border: 'border-red-700/50' },
};

function NewsNodeDetails({ config }: { config: Record<string, unknown> }) {
    return (
        <span>
            Bucket: <b className="text-foreground">{String(config.bucket || 'any')}</b> | Lookback:{' '}
            {String(config.lookback_hours || 48)}h
        </span>
    );
}

function TechNodeDetails({ config }: { config: Record<string, unknown> }) {
    return (
        <span>
            Conditions: {((config.conditions as unknown[]) || []).length} rule(s) (All must pass)
        </span>
    );
}

function LLMNodeDetails({ config }: { config: Record<string, unknown> }) {
    return (
        <span>
            Model:{' '}
            <b className="text-foreground">{String(config.model || '~typesafe/jev-latest')}</b> |
            Target: {String(config.target_choice || 'BULLISH')} (≥
            {String(config.min_confidence || 70)}%)
        </span>
    );
}

function RiskNodeDetails({ config }: { config: Record<string, unknown> }) {
    return (
        <span>
            Action: <b className="text-foreground">{String(config.action || 'BUY')}</b> | SL:{' '}
            {String(config.stop_loss_pct || 1.5)}% | TP: {String(config.target_profit_pct || 3.0)}%
            | Hold: {String(config.max_hold_bars || 12)} bars
        </span>
    );
}

function FlowNodeSummary({ node }: { node: DAGNode }) {
    switch (node.type) {
        case 'news_source':
            return <NewsNodeDetails config={node.config} />;
        case 'technical_gate':
            return <TechNodeDetails config={node.config} />;
        case 'classification':
            return <LLMNodeDetails config={node.config} />;
        case 'generative_analyst':
            return (
                <span>Model: {String(node.config.model || 'auto-strata')} | Analyst reasoning</span>
            );
        case 'risk_output':
            return <RiskNodeDetails config={node.config} />;
        default:
            return <span>Type: {node.type}</span>;
    }
}

function FlowNodeItem({
    node,
    index,
    onConfigure,
    onRemove,
}: {
    node: DAGNode;
    index: number;
    onConfigure: () => void;
    onRemove: () => void;
}) {
    const styling = NODE_TYPE_COLORS[node.type] || {
        badge: 'bg-muted text-muted-foreground',
        border: 'border-border',
    };

    return (
        <div
            className={`flex flex-col gap-2 border ${styling.border} bg-boxel-surface p-4 rounded-none voxel-card`}
        >
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-bold text-muted-foreground">
                        #{index + 1}
                    </span>
                    <span className="text-sm font-bold text-foreground">{node.title}</span>
                    <span
                        className={`rounded-none px-1.5 py-0.5 text-xs font-normal uppercase tracking-wider ${styling.badge}`}
                    >
                        {node.type.replace('_', ' ')}
                    </span>
                </div>
                <div className="flex items-center gap-2">
                    <Button size="sm" variant="ghost" onClick={onConfigure}>
                        Configure
                    </Button>
                    <button
                        type="button"
                        onClick={onRemove}
                        className="px-2 text-xs font-bold text-red-400 hover:text-red-300"
                        title="Delete step"
                    >
                        ✕
                    </button>
                </div>
            </div>

            <div className="voxel-trough p-2 font-mono text-xs font-normal text-muted-foreground">
                <FlowNodeSummary node={node} />
            </div>
        </div>
    );
}

export function RecipeFlowCanvas({ recipe, onChange }: RecipeFlowCanvasProps) {
    const [activeEditNode, setActiveEditNode] = useState<DAGNode | null>(null);

    const handleNodeSave = (updatedNode: DAGNode) => {
        const newNodes = recipe.nodes.map((n) => (n.id === updatedNode.id ? updatedNode : n));
        onChange({ ...recipe, nodes: newNodes });
    };

    const handleRemoveNode = (nodeId: string) => {
        const newNodes = recipe.nodes.filter((n) => n.id !== nodeId);
        const newEdges = [];
        for (let i = 0; i < newNodes.length - 1; i++) {
            newEdges.push({ from: newNodes[i].id, to: newNodes[i + 1].id });
        }
        onChange({ ...recipe, nodes: newNodes, edges: newEdges });
    };

    const handleAddNode = (type: NodeType) => {
        const newId = `${type}-${Date.now().toString().slice(-4)}`;
        const titleMap: Record<NodeType, string> = {
            news_source: 'News Catalyst Filter',
            price_tape: 'Price Tape Stream',
            technical_gate: 'Technical Indicator Gate',
            classification: 'Jev Catalyst Classifier',
            generative_analyst: 'Reasoning Analyst',
            risk_output: 'Risk & Trade Execution',
        };

        const defaultConfigs: Record<NodeType, JSONObject> = {
            news_source: { bucket: 'general_market', lookback_hours: 48 },
            price_tape: { ticker: 'SPY', cadence: recipe.cadence },
            technical_gate: { conditions: [{ metric: 'price', operator: '>', target: 'vwap' }] },
            classification: {
                model: '~typesafe/jev-latest',
                target_choice: 'BULLISH',
                min_confidence: 70,
            },
            generative_analyst: {
                model: 'auto-strata',
                system_prompt: 'Quantitative market analysis.',
            },
            risk_output: {
                action: 'BUY',
                stop_loss_pct: 1.5,
                target_profit_pct: 3.0,
                max_hold_bars: 12,
            },
        };

        const newNode: DAGNode = {
            id: newId,
            type,
            title: titleMap[type],
            config: defaultConfigs[type],
        };

        const newNodes = [...recipe.nodes, newNode];
        const newEdges = [];
        for (let i = 0; i < newNodes.length - 1; i++) {
            newEdges.push({ from: newNodes[i].id, to: newNodes[i + 1].id });
        }

        onChange({ ...recipe, nodes: newNodes, edges: newEdges });
    };

    return (
        <div className="flex flex-col gap-4 border border-border bg-boxel-canvas p-4 rounded-none">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border pb-3">
                <div className="flex items-center gap-2">
                    <span className="font-display text-lg font-bold text-foreground">
                        Pipeline Recipe Canvas
                    </span>
                    <Badge variant="outline" size="sm">
                        {recipe.nodes.length} Blocks
                    </Badge>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                    <span className="text-xs font-normal text-muted-foreground">Add Step:</span>
                    <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleAddNode('news_source')}
                    >
                        + News
                    </Button>
                    <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleAddNode('technical_gate')}
                    >
                        + Technical Gate
                    </Button>
                    <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleAddNode('classification')}
                    >
                        + LLM Gate
                    </Button>
                    <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleAddNode('risk_output')}
                    >
                        + Risk Exit
                    </Button>
                </div>
            </div>

            <div className="flex flex-col gap-3">
                {recipe.nodes.map((node, index) => (
                    <div key={node.id} className="flex flex-col gap-2">
                        <FlowNodeItem
                            node={node}
                            index={index}
                            onConfigure={() => setActiveEditNode(node)}
                            onRemove={() => handleRemoveNode(node.id)}
                        />
                        {index < recipe.nodes.length - 1 && (
                            <div className="flex items-center justify-center py-1">
                                <span className="text-xs font-bold text-muted-foreground">
                                    ↓ THEN
                                </span>
                            </div>
                        )}
                    </div>
                ))}
            </div>

            <BlockConfigureModal
                node={activeEditNode}
                isOpen={activeEditNode !== null}
                onClose={() => setActiveEditNode(null)}
                onSave={handleNodeSave}
            />
        </div>
    );
}
