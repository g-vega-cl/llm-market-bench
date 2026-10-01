import { Badge } from '@llm-market-bench/ui-design-system';
import { splitPromptSections } from '../../autoresearch/utils/promptSections';

export interface SegmentedPromptInspectorProps {
    promptContent: string;
}

export function SegmentedPromptInspector({ promptContent }: SegmentedPromptInspectorProps) {
    const { header, mutable, footer, isSplit } = splitPromptSections(promptContent);

    if (!isSplit) {
        return (
            <div className="p-6 bg-slate-900 text-slate-100 rounded-xl space-y-3 min-w-0">
                <div className="text-xs font-bold uppercase tracking-wider text-slate-400">
                    The Predictor Prompt
                </div>
                <pre className="whitespace-pre-wrap break-words font-mono text-xs max-h-96 overflow-y-auto">
                    {promptContent}
                </pre>
            </div>
        );
    }

    return (
        <div className="space-y-6 min-w-0">
            {header && (
                <div className="space-y-2 min-w-0">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <span className="text-xs font-bold text-zinc-900 dark:text-zinc-100">
                                🔒 1. Engine Constraints & Anti-Bias Mandate
                            </span>
                            <span className="text-[10px] text-zinc-500 dark:text-zinc-400 font-mono">
                                (Header)
                            </span>
                        </div>
                        <Badge
                            variant="solid"
                            className="bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20 text-[10px] uppercase"
                        >
                            Frozen / System Managed
                        </Badge>
                    </div>
                    <p className="text-[11px] text-zinc-500 dark:text-zinc-400">
                        Unchangeable system rules (price injection rules, tool requirements,
                        zero-mean base rate mandate). Autoresearch cannot edit this.
                    </p>
                    <pre className="p-4 bg-zinc-950/80 text-zinc-400 rounded-xl overflow-x-auto text-xs font-mono leading-relaxed border border-amber-500/20 max-h-[250px] overflow-y-auto whitespace-pre-wrap break-words">
                        {header}
                    </pre>
                </div>
            )}

            <div className="space-y-2 min-w-0">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <span className="text-xs font-bold text-zinc-900 dark:text-zinc-100">
                            ⚡ 2. Intraday Trading Strategy & Analysis Rules
                        </span>
                        <span className="text-[10px] text-emerald-500 font-mono font-semibold">
                            (Evolved Target)
                        </span>
                    </div>
                    <Badge
                        variant="solid"
                        className="bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 text-[10px] uppercase font-bold"
                    >
                        Mutable / Evolved by Autoresearch
                    </Badge>
                </div>
                <p className="text-[11px] text-zinc-500 dark:text-zinc-400">
                    Analytical heuristics, technical levels, and catalyst transmission rules. This
                    section is iteratively tested and optimized by daily autoresearch.
                </p>
                <pre className="p-4 bg-zinc-950 text-zinc-200 rounded-xl overflow-x-auto text-xs font-mono leading-relaxed border border-emerald-500/30 ring-1 ring-emerald-500/20 max-h-[400px] overflow-y-auto whitespace-pre-wrap break-words">
                    {mutable}
                </pre>
            </div>

            {footer && (
                <div className="space-y-2 min-w-0">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <span className="text-xs font-bold text-zinc-900 dark:text-zinc-100">
                                🔒 3. Risk Rules & Output JSON Schema
                            </span>
                            <span className="text-[10px] text-zinc-500 dark:text-zinc-400 font-mono">
                                (Footer)
                            </span>
                        </div>
                        <Badge
                            variant="solid"
                            className="bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20 text-[10px] uppercase"
                        >
                            Frozen / System Managed
                        </Badge>
                    </div>
                    <p className="text-[11px] text-zinc-500 dark:text-zinc-400">
                        Mandatory structured JSON output schema and format constraints. Autoresearch
                        cannot edit this.
                    </p>
                    <pre className="p-4 bg-zinc-950/80 text-zinc-400 rounded-xl overflow-x-auto text-xs font-mono leading-relaxed border border-amber-500/20 max-h-[250px] overflow-y-auto whitespace-pre-wrap break-words">
                        {footer}
                    </pre>
                </div>
            )}
        </div>
    );
}
