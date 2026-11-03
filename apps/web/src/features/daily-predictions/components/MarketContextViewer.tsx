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
            <div className="flex flex-col gap-1">
                <div className="text-sm font-bold uppercase tracking-wider text-slate-400">
                    Market Context (Model Input)
                </div>
                <div className="p-3 bg-slate-900/50 border border-slate-800 rounded-none text-xs font-normal text-slate-500 italic">
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
        <div className="flex flex-col gap-2">
            <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                    <span className="text-sm font-bold uppercase tracking-wider text-slate-400">
                        Market Context (Model Input)
                    </span>
                    <Badge variant="soft" colorScheme="neutral" size="sm" radius="none">
                        ~{estTokens.toLocaleString('en-US')} tokens
                    </Badge>
                </div>
                <div className="flex items-center gap-2">
                    <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => setIsOpen((prev) => !prev)}
                        className="text-sm font-bold text-slate-400 hover:text-slate-200 rounded-none"
                    >
                        {isOpen ? 'Collapse Context' : 'Expand Context'}
                    </Button>
                    <Button
                        size="sm"
                        variant="soft"
                        onClick={handleCopy}
                        className="text-sm font-bold font-mono rounded-none"
                    >
                        {copied ? 'Copied!' : 'Copy Context'}
                    </Button>
                </div>
            </div>

            {isOpen ? (
                <pre className="whitespace-pre-wrap break-words font-mono text-xs max-h-96 overflow-y-auto bg-slate-950 border border-slate-800 text-slate-300 p-4 rounded-none select-text leading-relaxed">
                    {context}
                </pre>
            ) : (
                <button
                    type="button"
                    onClick={() => setIsOpen(true)}
                    className="w-full text-left p-3 bg-slate-950/60 border border-slate-800/80 hover:border-slate-700 rounded-none text-xs font-mono text-slate-400 cursor-pointer transition-colors line-clamp-3 select-none flex flex-col gap-1"
                    title="Click to expand full market context"
                >
                    <span>{context.slice(0, 300)}...</span>
                    <span className="text-xs font-normal text-slate-500 font-sans italic">
                        Click to view complete pre-market briefing and options data.
                    </span>
                </button>
            )}
        </div>
    );
}
