import { Badge, Button } from '@llm-market-bench/ui-design-system';
import { useState } from 'react';

export interface MarketContextViewerProps {
    context?: string | null;
}

export function MarketContextViewer({ context }: MarketContextViewerProps) {
    const [copied, setCopied] = useState(false);
    const [isOpen, setIsOpen] = useState(false);

    if (!context?.trim()) {
        return (
            <div className="space-y-1">
                <div className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                    Market Context (Model Input)
                </div>
                <div className="p-3 bg-slate-900/50 border border-slate-800 rounded-lg text-xs text-slate-500 italic">
                    Market context was not captured for predictions recorded prior to September 23,
                    2026.
                </div>
            </div>
        );
    }

    const handleCopy = async () => {
        try {
            await navigator.clipboard.writeText(context);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        } catch {
            // Fallback for environments where clipboard API is restricted
        }
    };

    const charCount = context.length;
    const estTokens = Math.round(charCount / 4);

    return (
        <div className="space-y-2">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                        Market Context (Model Input)
                    </span>
                    <Badge variant="soft" colorScheme="neutral" size="sm">
                        ~{estTokens.toLocaleString()} tokens
                    </Badge>
                </div>
                <div className="flex items-center gap-2">
                    <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => setIsOpen((prev) => !prev)}
                        className="text-xs text-slate-400 hover:text-slate-200"
                    >
                        {isOpen ? 'Collapse Context' : 'Expand Context'}
                    </Button>
                    <Button
                        size="sm"
                        variant="soft"
                        onClick={handleCopy}
                        className="text-xs font-mono"
                    >
                        {copied ? 'Copied!' : 'Copy Context'}
                    </Button>
                </div>
            </div>

            {isOpen ? (
                <pre className="whitespace-pre-wrap font-mono text-xs max-h-96 overflow-y-auto bg-slate-950 border border-slate-800 text-slate-300 p-4 rounded-lg select-text leading-relaxed">
                    {context}
                </pre>
            ) : (
                <button
                    type="button"
                    onClick={() => setIsOpen(true)}
                    className="w-full text-left p-3 bg-slate-950/60 border border-slate-800/80 hover:border-slate-700 rounded-lg text-xs font-mono text-slate-400 cursor-pointer transition-colors line-clamp-3 select-none"
                    title="Click to expand full market context"
                >
                    {context.slice(0, 300)}...
                    <span className="block mt-1 text-slate-500 font-sans italic">
                        Click to view complete pre-market briefing and options data.
                    </span>
                </button>
            )}
        </div>
    );
}
