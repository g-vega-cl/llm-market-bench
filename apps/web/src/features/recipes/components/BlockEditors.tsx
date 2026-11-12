import { Button } from '@llm-market-bench/ui-design-system';
import { useState } from 'react';
import type {
    MemoriesBlock,
    NewsBlock,
    PromptBlock,
    TechnicalsBlock,
    TechnicalsRule,
} from '../types';

const MEMORY_CATEGORIES = [
    'ALL',
    'MARKET_EVENT',
    'GOVERNMENT_INCENTIVE',
    'LESSON_LEARNED',
    'THEMATIC_FLOW',
    'AUTORESEARCH_INSIGHT',
];

const TECHNICAL_METRICS = [
    'P/E',
    'FCF',
    'VWAP',
    'Price vs VWAP',
    'RSI',
    'MACD',
    'price_52w_pct',
    'SMA 20',
    'SMA 50',
    'RVOL',
];

function parseKeywordsInput(raw: string): string[] {
    return raw
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean);
}

function KeywordsInput({
    label,
    className,
    keywords,
    placeholder,
    onChange,
}: {
    label: string;
    className: string;
    keywords: string[];
    placeholder: string;
    onChange: (next: string[]) => void;
}) {
    const [raw, setRaw] = useState(keywords.join(', '));

    return (
        <label className={className}>
            <span>{label}</span>
            <input
                type="text"
                value={raw}
                onChange={(e) => {
                    const nextRaw = e.target.value;
                    setRaw(nextRaw);
                    onChange(parseKeywordsInput(nextRaw));
                }}
                placeholder={placeholder}
                className="border border-border bg-boxel-surface p-2 text-sm font-bold text-foreground rounded-none"
            />
        </label>
    );
}

export function PromptBlockEditor({
    block,
    onUpdate,
}: {
    block: PromptBlock;
    onUpdate: (text: string) => void;
}) {
    return (
        <textarea
            rows={3}
            aria-label="Prompt text"
            value={block.text}
            onChange={(e) => onUpdate(e.target.value)}
            placeholder="Write instructions for the LLM (use {{prev_output}} in Stage 2+ to reference prior stage output)..."
            className="w-full border border-border bg-boxel-surface p-2 text-xs font-normal text-foreground rounded-none"
        />
    );
}

export function NewsBlockEditor({
    block,
    onUpdate,
}: {
    block: NewsBlock;
    onUpdate: (patch: Partial<NewsBlock>) => void;
}) {
    return (
        <div className="flex flex-wrap gap-3">
            <KeywordsInput
                key={block.id}
                label="Contains Keywords (comma-separated)"
                className="flex flex-1 basis-64 min-w-0 flex-col gap-1 text-xs font-normal text-muted-foreground"
                keywords={block.contains}
                placeholder="Trump, chips, tariff"
                onChange={(contains) => onUpdate({ contains })}
            />
            <label className="flex flex-col gap-1 text-xs font-normal text-muted-foreground">
                <span>Recency (Hours)</span>
                <input
                    type="number"
                    min={1}
                    value={block.recency_hours}
                    onChange={(e) =>
                        onUpdate({ recency_hours: Math.max(1, Number(e.target.value) || 48) })
                    }
                    className="border border-border bg-boxel-surface p-2 text-sm font-bold text-foreground rounded-none"
                />
            </label>
        </div>
    );
}

export function MemoriesBlockEditor({
    block,
    onUpdate,
}: {
    block: MemoriesBlock;
    onUpdate: (patch: Partial<MemoriesBlock>) => void;
}) {
    return (
        <div className="flex flex-wrap gap-3">
            <KeywordsInput
                key={block.id}
                label="Contains Keywords"
                className="flex flex-1 basis-56 min-w-0 flex-col gap-1 text-xs font-normal text-muted-foreground"
                keywords={block.contains}
                placeholder="FOMC, tariff"
                onChange={(contains) => onUpdate({ contains })}
            />
            <label className="flex flex-col gap-1 text-xs font-normal text-muted-foreground">
                <span>Recency (Hours)</span>
                <input
                    type="number"
                    min={1}
                    value={block.recency_hours}
                    onChange={(e) =>
                        onUpdate({ recency_hours: Math.max(1, Number(e.target.value) || 168) })
                    }
                    className="border border-border bg-boxel-surface p-2 text-sm font-bold text-foreground rounded-none"
                />
            </label>
            <label className="flex flex-col gap-1 text-xs font-normal text-muted-foreground">
                <span>Category</span>
                <select
                    value={block.category}
                    onChange={(e) => onUpdate({ category: e.target.value })}
                    className="border border-border bg-boxel-surface p-2 text-sm font-bold text-foreground rounded-none"
                >
                    {MEMORY_CATEGORIES.map((c) => (
                        <option key={c} value={c}>
                            {c}
                        </option>
                    ))}
                </select>
            </label>
            <label className="flex flex-col gap-1 text-xs font-normal text-muted-foreground">
                <span>Min Importance (1-10)</span>
                <input
                    type="number"
                    min={1}
                    max={10}
                    value={block.min_importance}
                    onChange={(e) =>
                        onUpdate({
                            min_importance: Math.min(10, Math.max(1, Number(e.target.value) || 1)),
                        })
                    }
                    className="border border-border bg-boxel-surface p-2 text-sm font-bold text-foreground rounded-none"
                />
            </label>
        </div>
    );
}

export function TechnicalsBlockEditor({
    block,
    onUpdate,
}: {
    block: TechnicalsBlock;
    onUpdate: (rules: TechnicalsRule[]) => void;
}) {
    const updateRule = (ruleId: string, patch: Partial<TechnicalsRule>) => {
        onUpdate(block.rules.map((r) => (r.id === ruleId ? { ...r, ...patch } : r)));
    };

    const addRule = () => {
        onUpdate([
            ...block.rules,
            {
                id: `rule-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
                metric: 'RSI',
                operator: '<',
                target: '70',
            },
        ]);
    };

    const removeRule = (ruleId: string) => {
        onUpdate(block.rules.filter((r) => r.id !== ruleId));
    };

    return (
        <div className="flex flex-col gap-2">
            <span className="text-xs font-normal text-muted-foreground">
                Company Technical & Fundamental Criteria (injected as prompt instructions)
            </span>
            {block.rules.map((rule) => (
                <div
                    key={rule.id}
                    className="flex flex-wrap items-center gap-2 border border-border bg-boxel-surface p-2 rounded-none"
                >
                    <select
                        aria-label="Technical Metric"
                        value={rule.metric}
                        onChange={(e) => updateRule(rule.id, { metric: e.target.value })}
                        className="border border-border bg-boxel-canvas p-1 text-sm font-bold text-foreground rounded-none"
                    >
                        {TECHNICAL_METRICS.map((m) => (
                            <option key={m} value={m}>
                                {m}
                            </option>
                        ))}
                    </select>
                    <select
                        aria-label="Operator"
                        value={rule.operator}
                        onChange={(e) =>
                            updateRule(rule.id, {
                                operator: e.target.value as TechnicalsRule['operator'],
                            })
                        }
                        className="border border-border bg-boxel-canvas p-1 text-sm font-bold text-foreground rounded-none"
                    >
                        <option value=">">&gt;</option>
                        <option value="<">&lt;</option>
                        <option value=">=">&gt;=</option>
                        <option value="<=">&lt;=</option>
                        <option value="==">==</option>
                    </select>
                    <input
                        type="text"
                        aria-label="Target Value"
                        value={rule.target}
                        onChange={(e) => updateRule(rule.id, { target: e.target.value })}
                        placeholder="Target"
                        className="flex-1 basis-32 min-w-0 border border-border bg-boxel-canvas p-1 text-sm font-bold text-foreground rounded-none"
                    />
                    <Button size="sm" variant="outline" onClick={() => removeRule(rule.id)}>
                        ✕
                    </Button>
                </div>
            ))}
            <div>
                <Button size="sm" variant="outline" onClick={addRule}>
                    + Add Rule
                </Button>
            </div>
        </div>
    );
}
